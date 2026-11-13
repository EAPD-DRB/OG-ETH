"""
Tests of the rebased-GDP basis, the revenue mapping, the dashboard targets
and the other inputs added with the FY2024/25 recalibration. No model solve
is involved.
"""

import json
import os
import pickle
from importlib.resources import files

import numpy as np
import pytest
from ogcore.parameters import Specifications

from ogeth import calibrate, targets, warm_start
from ogeth import macro_params as mp


@pytest.fixture(scope="module")
def packaged():
    return json.loads(
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .read_text(encoding="utf-8")
    )


def test_rebase_factors_are_old_over_new_gdp():
    """FY2024/25: 15,094 (IMF CR 26/174, old base) over 24,030 billion birr
    (Ministry of National Strategy, rebased); FY2025/26: 19,268 over 31,860;
    later years hold the FY2025/26 factor."""
    f = mp.rebase_factors(7)
    assert f[0] == pytest.approx(15094 / 24030)
    assert f[1] == pytest.approx(19268 / 31860)
    assert np.allclose(f[2:], f[1])
    # a published series keeps its numerator: debt in birr is unchanged
    assert mp.rebased([50.0])[0] == pytest.approx(50.0 * 15094 / 24030, 1e-4)


def test_debt_is_general_government_on_the_rebased_basis():
    """General-government gross debt, 43.3 percent of old-base GDP in
    FY2024/25 (IMF WEO October 2026), is 27.2 percent of rebased GDP; the
    program report's 50.5 adds debt the budget does not service."""
    assert mp.IMF_PUBLIC_DEBT[0] == pytest.approx(27.198, abs=1e-3)
    assert mp.IMF_PUBLIC_DEBT_WIDE_PUBLISHED[0] == 50.5
    assert 0.5 < mp.GG_FOREIGN_DEBT_SHARE < 0.6


def test_revenue_mapping_adds_up_to_the_outturn():
    """Every FY2024/25 revenue line is mapped once (NBE Annual Report
    2024/25, Table 6.3): the mapped lines plus the unmapped ones equal total
    domestic revenue of 1,386.5 billion birr."""
    r = mp.REVENUE_FY2425_BIRR_BN
    domestic = sum(v for k, v in r.items() if k != "grants")
    assert domestic == pytest.approx(1386.5, abs=0.5)
    mapped = (
        mp.PIT_REVENUE_SHARE
        + mp.CIT_REVENUE_SHARE
        + mp.CONS_TAX_SHARE
        + mp.WEALTH_TAX_SHARE
    ) * 24030
    unmapped = (
        r["reimbursements and property sales"]
        + r["other non-tax incl. pension contributions"]
    )
    assert mapped + unmapped == pytest.approx(domestic, abs=0.5)
    assert mp.PIT_REVENUE_SHARE == pytest.approx(194.3 / 24030, abs=1e-5)


def test_price_basis_conversion():
    """OG-Core's Y excludes the consumption tax: model shares are the data
    share over (1 - consumption-tax share)."""
    assert mp.MODEL_PER_MARKET_GDP == pytest.approx(
        1 / (1 - mp.CONS_TAX_SHARE)
    )
    assert 1.02 < mp.MODEL_PER_MARKET_GDP < 1.04
    assert mp.to_model(0.1) == pytest.approx(0.1 * mp.MODEL_PER_MARKET_GDP)


def test_formal_share_sits_at_the_top_of_lifetime_income():
    """77.65 percent informal (ILOSTAT, LFMS 2021): the top 20 percent of
    households are formal and group 4 is 23.5 percent formal."""
    formal = mp.formal_share_by_group(mp.INFORMAL_EMPLOYMENT_SHARE)
    assert formal == pytest.approx([0, 0, 0, 0.235, 1, 1, 1], abs=1e-3)
    assert np.dot(formal, mp.LAMBDAS) == pytest.approx(
        1 - mp.INFORMAL_EMPLOYMENT_SHARE
    )


def test_payroll_tax_falls_only_on_covered_groups(packaged):
    """The 18 percent statutory contribution applies to the pension-covered
    groups only, scaled to contributions."""
    tau = np.array(packaged["tau_payroll"])
    assert tau.shape == (1, 7)
    assert (tau[0, :5] == 0).all()
    assert tau[0, 6] == pytest.approx(
        mp.PAYROLL_STATUTORY_RATE * mp.PAYROLL_COVERAGE_SCALE, abs=1e-6
    )


def test_targets_carry_sources_and_dials():
    for k, (target, dial, source) in targets.TRANSITION_TARGETS.items():
        assert np.isfinite(target) and dial and source, k
    assert targets.TRANSITION_TARGETS["(I+I_g)/Y"][0] == pytest.approx(0.353)
    assert targets.TRANSITION_TARGETS["K_f/K"][0] == pytest.approx(
        mp.FDI_STOCK_TO_GDP / mp.PRIVATE_CAPITAL_OUTPUT_RATIO, abs=1e-4
    )


def test_capital_stocks_are_rebased():
    """Total K/Y by perpetual inventory on PWT 11.0 with the rebasing's
    investment gap phased in from FY2015/16; public capital (IMF ICSD 0.667
    of old-base GDP) converted like other fiscal stocks."""
    assert mp.TOTAL_CAPITAL_OUTPUT_RATIO == pytest.approx(2.514, abs=1e-3)
    assert mp.PUBLIC_CAPITAL_OUTPUT_RATIO == pytest.approx(
        0.667 * 15094 / 24030, abs=1e-3
    )
    # no revision rolls the old-base stock forward; the full-history gap is
    # the upper bound; the central case sits between
    low = mp.rebased_capital_output_ratio(None)
    high = mp.rebased_capital_output_ratio(1970)
    assert 1.9 < low < mp.TOTAL_CAPITAL_OUTPUT_RATIO < high < 3.1


def test_capital_and_depreciation_are_sourced(packaged):
    """delta for private capital from PWT 11.0's 0.0414 on total capital,
    with public capital at delta_g 0.02."""
    kg = mp.PUBLIC_CAPITAL_OUTPUT_RATIO / mp.TOTAL_CAPITAL_OUTPUT_RATIO
    assert mp.DELTA_ANNUAL * (1 - kg) + 0.02 * kg == pytest.approx(
        0.0414, abs=1e-4
    )
    assert packaged["delta_annual"] == pytest.approx(mp.DELTA_ANNUAL)
    assert packaged["initial_Kg_ratio"] == pytest.approx(mp.INITIAL_KG_RATIO)
    assert packaged["initial_wealth_ratio"] == pytest.approx(
        mp.INITIAL_WEALTH_RATIO
    )


def test_solver_settings_and_floor_are_in_the_json(packaged):
    """Anderson acceleration with nu <= 0.2 and the negative-rate floor
    travel with the packaged parameters, not the example script."""
    assert packaged["TPI_outer_method"] == "anderson"
    assert packaged["nu"] <= 0.2
    assert packaged["r_gov_floor"] == pytest.approx(mp.R_GOV_FLOOR)


def test_demographics_read_the_un_projection_to_its_end():
    """The data window sets long-run population growth; it runs to 2098,
    the last year the Population-Data archive supports."""
    assert calibrate.DEMOG_FINAL_DATA_YEAR == 2098


def test_packaged_population_growth_falls_with_the_projection(packaged):
    g_n = np.array(packaged["g_n"])
    assert g_n[0] > 0.03
    assert abs(packaged["g_n_ss"]) < 0.005


def test_packaged_json_loads():
    p = Specifications(baseline=True)
    p.update_specifications(
        json.loads(
            files("ogeth")
            .joinpath("ogeth_default_parameters.json")
            .read_text(encoding="utf-8")
        )
    )
    assert np.asarray(p.alpha_db).ndim == 3


def test_warm_start_seed_is_shipped_and_shaped():
    assert os.path.exists(warm_start.SEED_PATH)
    with open(warm_start.SEED_PATH, "rb") as fh:
        seed = pickle.load(fh)
    assert seed["b"].shape == (80, 7) and seed["n"].shape == (80, 7)
    assert seed["factor"] > 0

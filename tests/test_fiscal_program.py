"""
Tests of the two baseline scenarios' fiscal paths.

The packaged JSON is the history-anchored baseline: every fiscal input takes
its FY2024/25 outturn or enacted FY2025/26 budget value and is held there,
and debt stabilizes at its measured ratio. The IMF fifth-ECF-review program
(Country Report 26/174) is a scenario built by ``fiscal_program_params``:
spending ratios mapped onto the model's instruments, revenue gains spread
over the consumption and corporate taxes, and a real effective interest
rates on market and concessional debt from the program's debt
sustainability analysis. These tests pin the
packaged paths to the history derivation and check the program mapping
reproduces the IMF accounts. No model solve is involved.
"""

import json
from importlib.resources import files

import numpy as np
import pytest
from ogcore.parameters import Specifications

from ogeth import macro_params as mp

N = len(mp.PROGRAM_YEARS)


@pytest.fixture(scope="module")
def packaged():
    return json.loads(
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def params(packaged):
    p = Specifications()
    p.update_specifications(packaged)
    return p


def test_spending_paths_reproduce_imf_primary_expenditure():
    """G + TR + I_g equals IMF expenditure net of interest, within 0.1 pp."""
    sp = mp.program_spending_paths()
    primary = (
        np.array(sp["alpha_G"][:N])
        + np.array(sp["alpha_T"][:N])
        + np.array(sp["alpha_I"][:N])
    )
    # the paths are shares of the model's Y; the IMF's of market-price GDP
    primary = primary / mp.MODEL_PER_MARKET_GDP
    if mp.PENSIONS_ON:
        # pension benefits are paid by the pension system, not as transfers
        primary = primary + mp.PENSIONS_SHARE_OF_GDP / 100
    imf = (np.array(mp.IMF_EXPENDITURE) - np.array(mp.IMF_INTEREST)) / 100
    assert np.allclose(primary, imf, atol=1e-3)


def test_program_paths_start_at_fy2024_25_values(packaged):
    """Period 0 is FY2024/25: general-government debt 43.3, capital spending
    5.0, grants 1.7 and recurrent spending net of interest and transfers 4.3
    percent of old-base GDP (IMF WEO Oct 2026; CR 26/174 Tables 1 and 2b),
    times old over rebased GDP (15,094 / 24,030), in model units."""
    f = 15094.0 / 24030.0
    assert mp.rebase_factors()[0] == pytest.approx(f)
    # general-government debt, split into concessional (alpha_ODA) and
    # market debt (initial_debt_ratio)
    total = packaged["initial_debt_ratio"] + packaged["alpha_ODA"][0]
    assert total == pytest.approx(mp.to_model(0.433 * f), abs=1e-4)
    external = mp.to_model(0.433 * f) * (31.8 - 7.2) / 43.3
    assert packaged["alpha_ODA"][0] == pytest.approx(0.9 * external, abs=1e-4)
    assert packaged["initial_foreign_debt_ratio"] * packaged[
        "initial_debt_ratio"
    ] == pytest.approx(0.1 * external, abs=1e-4)
    assert packaged["alpha_I"][0] == pytest.approx(
        mp.to_model(0.050 * f), abs=1e-5
    )
    assert packaged["alpha_FA"][0] == pytest.approx(
        mp.to_model(0.017 * f), abs=1e-5
    )
    assert packaged["alpha_G"][0] == pytest.approx(
        mp.to_model((0.071 - 0.008 - 0.020) * f), abs=1e-5
    )
    cash = 0.020 * f - (
        mp.PENSIONS_SHARE_OF_GDP / 100 if mp.PENSIONS_ON else 0
    )
    assert packaged["alpha_T"][0] == pytest.approx(mp.to_model(cash), abs=1e-5)


def test_closure_starts_after_the_program_horizon(packaged):
    """Spending follows the program for its seven fiscal years; OG-Core's
    debt-closure rule takes over from FY2031/32."""
    assert packaged["tG1"] == N


def test_revenue_paths_add_the_imf_revenue_gain(params):
    """Consumption-tax and CIT paths of the program scenario carry the
    program's revenue increase (9.2 -> 12.3 percent of GDP) in the stated
    two-thirds / one-third split, evaluated at the FY2024/25 collections
    they scale."""
    prog = mp.fiscal_program_params(params)
    tau_c = np.asarray(prog["tau_c"])[:N, 0]
    cit = np.asarray(prog["adjustment_factor_for_cit_receipts"])[:N]
    gain_cons = (tau_c / tau_c[0] - 1) * mp.BASE_CONS_TAX_REVENUE
    gain_cit = (cit / cit[0] - 1) * mp.BASE_CIT_REVENUE
    imf_gain = (np.array(mp.IMF_REVENUE) - mp.IMF_REVENUE[0]) / 100
    # the formalization path phases in PIT_FORMALIZATION_GAIN over the program
    formal = mp.PIT_FORMALIZATION_GAIN * np.arange(N) / (N - 1)
    assert np.allclose(gain_cons + gain_cit + formal, imf_gain, atol=1e-12)
    assert np.allclose(
        gain_cons, mp.INDIRECT_SHARE_OF_REVENUE_GAIN * (imf_gain - formal)
    )


def test_history_baseline_holds_fy2024_25_inputs(packaged, params):
    """The packaged baseline: FY2024/25 outturn and FY2025/26 budget, then
    held; effective revenue rates, compliance and the foreign borrowing
    share flat; debt stabilizes at its measured ratio; remittances flat."""
    expected = mp.history_anchored_params(params)
    for key in ("alpha_G", "alpha_T", "alpha_I", "alpha_FA"):
        path = np.array(packaged[key])
        assert np.allclose(path[: len(expected[key])], expected[key])
        # nothing moves after the enacted budget year
        assert np.allclose(path[mp.HISTORY_KNOWN_YEARS - 1 :], path[-1])
    prog = mp.program_spending_paths()
    assert packaged["alpha_I"][1] == pytest.approx(prog["alpha_I"][1])
    tau_c = np.asarray(packaged["tau_c"])
    assert np.allclose(tau_c, tau_c[0])
    cit = np.asarray(packaged["adjustment_factor_for_cit_receipts"])
    assert np.allclose(cit, cit[0])
    lab = np.array(packaged["labor_income_tax_noncompliance_rate"])
    assert np.allclose(lab, lab[0])
    assert np.allclose(packaged["zeta_D"], mp.MARKET_FOREIGN_DEBT_SHARE)
    assert packaged["debt_ratio_ss"] == pytest.approx(mp.HISTORY_DEBT_RATIO_SS)
    # the long-run anchor is the FY2024/25 ratio of all debt, which is all
    # market debt once concessional debt has been repaid
    assert packaged["debt_ratio_ss"] == pytest.approx(
        packaged["initial_debt_ratio"] + packaged["alpha_ODA"][0], abs=1e-4
    )
    assert packaged["alpha_ODA"][-1] == 0.0
    assert packaged["alpha_RM_T"] == packaged["alpha_RM_1"]
    assert packaged["r_gov_DY"] == pytest.approx(
        -2 * packaged["r_gov_DY2"] * mp.HISTORY_DEBT_RATIO_SS
    )


def test_formalization_path_broadens_the_base_over_the_program():
    """Program scenario: group 6 goes from half to full compliance and group
    5 from none to a fifth, linearly over the seven program years, then
    holds; labor and capital rates move together (the SS diagnostic tiles
    one from the other)."""
    prog = mp.program_compliance_paths()
    lab = np.array(prog["labor_income_tax_noncompliance_rate"])
    cap = np.array(prog["capital_income_tax_noncompliance_rate"])
    assert lab.shape[0] == N + 1 and np.allclose(lab, cap)
    # the shape vectors give compliance relative to the top group; the
    # calibrated scale sets the level (see taxes.md)
    start = 1 - mp.COMPLIANCE_SCALE * (1 - np.array(mp.NONCOMPLIANCE_START))
    end = 1 - mp.COMPLIANCE_SCALE * (1 - np.array(mp.NONCOMPLIANCE_END))
    assert lab[0].tolist() == pytest.approx(start.tolist())
    assert lab[N - 1].tolist() == pytest.approx(end.tolist())
    assert lab[N].tolist() == pytest.approx(end.tolist())
    assert 0 < mp.COMPLIANCE_SCALE < 1
    assert (np.diff(lab, axis=0) <= 1e-6).all()  # compliance only improves


def test_pensions_go_to_the_formal_groups_only(packaged):
    """replacement_rate_adjust mirrors the compliance structure: no public
    pension for the five informal groups, half for group 6, full for group
    7."""
    adj = np.array(packaged["replacement_rate_adjust"])
    assert adj.shape[-1] == 7
    expected = np.array(mp.PENSION_COVERAGE) * mp.PENSION_COVERAGE_SCALE
    assert adj[-1].tolist() == pytest.approx(expected.tolist())
    assert adj[-1][:5].tolist() == pytest.approx([0.0] * 5)
    assert adj[-1][5] == pytest.approx(0.5 * adj[-1][6])
    assert 0 < mp.PENSION_COVERAGE_SCALE < 1


def test_domestic_market_debt_matches_the_imf_domestic_debt():
    """Market debt less its foreign-held part is domestically held debt, which
    the IMF reports separately (18.7 percent of old-base GDP in FY2024/25):
    the concessional split reproduces it to within 0.2 points of GDP."""
    domestic = mp.INITIAL_MARKET_DEBT_RATIO * (
        1 - mp.MARKET_FOREIGN_DEBT_SHARE
    )
    assert domestic == pytest.approx(
        mp.to_model(mp.IMF_DOMESTIC_DEBT[0] / 100), abs=2e-3
    )


def test_program_r_gov_targets_the_dsa_market_rate(params):
    """Program scenario: along the program's market-debt path (all debt less
    concessional debt) the shift path puts r_gov (before OG-Core's floor)
    on the DSA's real rate on domestic debt, -11.0 percent in FY2024/25
    rising to 3.3 by FY2030/31, above the floor."""
    prog = mp.fiscal_program_params(params)
    shift = np.asarray(prog["r_gov_shift"])[:N]
    scale = float(np.asarray(params.r_gov_scale).flatten()[0])
    d = mp.program_market_debt_path()
    r_gov = (
        scale * mp.R_SS_FOR_R_GOV
        - shift
        + prog["r_gov_DY"] * d
        + params.r_gov_DY2 * d**2
    )
    assert prog["debt_ratio_ss"] == pytest.approx(mp.PROGRAM_DEBT_RATIO_SS)
    assert prog["alpha_RM_T"] == pytest.approx(
        mp.to_model(mp.IMF_PRIVATE_TRANSFERS[-1] / 100), abs=1e-6
    )
    dsa = np.array(mp.DSA_DOMESTIC_REAL_RATE[:N]) / 100
    assert np.allclose(r_gov, dsa, atol=1e-9)
    assert (dsa > mp.R_GOV_FLOOR).all()


def test_history_r_gov_targets_the_dsa_market_rate(params):
    """History baseline: at the debt anchor (premium zero) r_gov follows the
    DSA's real rate on domestic debt year by year to 2036 (the legacy
    stock rolling over at market rates), then the long-run rate."""
    targets = mp.market_rate_targets()
    # OG-Core extends the path by holding its last value
    shift = np.asarray(params.r_gov_shift)[: len(targets)]
    scale = float(np.asarray(params.r_gov_scale).flatten()[0])
    D = params.debt_ratio_ss
    r_gov = (
        scale * mp.R_SS_FOR_R_GOV
        - shift
        + params.r_gov_DY * D
        + params.r_gov_DY2 * D**2
    )
    assert np.allclose(r_gov, targets, atol=1e-9)
    assert r_gov[0] == pytest.approx(-0.110)
    assert r_gov[N - 1] == pytest.approx(0.033)
    assert r_gov[11] == pytest.approx(0.046)  # 2036
    assert (np.diff(r_gov) > 0).all()


def test_long_run_r_gov_is_the_dsa_rate_on_new_domestic_debt(params):
    """The long-run real rate on market debt is the mean of the DSA's terms
    for new domestic borrowing (4.9 percent medium and long term, 4.5 short
    term); OG-Core holds the last shift value."""
    assert mp.LONG_RUN_R_GOV == pytest.approx(0.047)
    shift = np.asarray(params.r_gov_shift)
    scale = float(np.asarray(params.r_gov_scale).flatten()[0])
    D = params.debt_ratio_ss
    long_run = (
        scale * mp.R_SS_FOR_R_GOV
        - shift[-1]
        + params.r_gov_DY * D
        + params.r_gov_DY2 * D**2
    )
    assert long_run == pytest.approx(mp.LONG_RUN_R_GOV, abs=1e-9)


def test_packaged_fiscal_paths_match_the_derivation(packaged, params):
    """A regeneration must rewrite the fiscal paths from the same tables."""
    expected = mp.scenario_params(params)
    assert np.allclose(packaged["g_RM"], expected["g_RM"])
    for key in ("alpha_G", "alpha_T", "alpha_I", "alpha_FA"):
        assert np.allclose(
            np.array(packaged[key])[: len(expected[key])], expected[key]
        )
    assert np.allclose(
        np.array(packaged["adjustment_factor_for_cit_receipts"])[
            : len(expected["adjustment_factor_for_cit_receipts"])
        ],
        expected["adjustment_factor_for_cit_receipts"],
    )
    assert np.allclose(
        np.array(packaged["tau_c"])[: len(expected["tau_c"])],
        expected["tau_c"],
    )
    assert np.allclose(
        np.array(packaged["r_gov_shift"])[: len(expected["r_gov_shift"])],
        expected["r_gov_shift"],
    )


def test_initial_wealth_ratio_is_built_from_its_components():
    """B/Y = private K/Y (rebased total less rebased IMF ICSD public
    capital) - foreign-owned capital (UNCTAD FDI stock, mid-FY2024/25, over
    rebased USD GDP) + domestically held general-government debt, in model
    units."""
    assert mp.PRIVATE_CAPITAL_OUTPUT_RATIO == pytest.approx(
        mp.TOTAL_CAPITAL_OUTPUT_RATIO - mp.PUBLIC_CAPITAL_OUTPUT_RATIO
    )
    assert mp.FDI_STOCK_TO_GDP == pytest.approx(
        (42.528 + 46.324) / 2 / 201.42, abs=1e-4
    )
    assert mp.INITIAL_WEALTH_RATIO == pytest.approx(
        mp.to_model(
            mp.PRIVATE_CAPITAL_OUTPUT_RATIO
            - mp.FDI_STOCK_TO_GDP
            + mp.DOMESTIC_DEBT_TO_GDP
        ),
        abs=1e-3,
    )
    # OG-Core's valid range for initial_wealth_ratio
    assert 0.8 < mp.INITIAL_WEALTH_RATIO < 7.0


def test_concessional_debt_follows_the_dsa_then_ends():
    """Concessional debt moves with the DSA's public external debt ratio
    (31.8 percent of old-base GDP in FY2024/25, 16.8 in FY2030/31, 9.2 in
    2036, 4.1 in 2046), then falls to zero at the 2036-2046 pace: no
    concessional subsidy in the long run."""
    a = np.array(mp.concessional_debt_path())
    assert a[0] == pytest.approx(mp.CONCESSIONAL_DEBT_RATIO)
    assert a[6] / a[0] == pytest.approx(16.8 / 31.8, abs=1e-4)
    assert a[11] / a[0] == pytest.approx(9.2 / 31.8, abs=1e-4)
    assert a[21] / a[0] == pytest.approx(4.1 / 31.8, abs=1e-4)
    assert (np.diff(a) <= 0).all()
    assert a[-1] == 0.0 and a[-2] > 0.0


def test_concessional_rate_is_the_dsa_external_rate_in_real_terms():
    """r_ODA is the DSA's average nominal rate on external debt (USD) less
    US inflation: -1.3 percent real in FY2024/25, 0.6 at the FY2026/27 peak,
    held after 2046."""
    r = np.array(mp.concessional_rate_path())
    assert r[0] == pytest.approx(0.007 - mp.US_INFLATION)
    assert r[2] == pytest.approx(0.026 - mp.US_INFLATION)
    assert r[-1] == pytest.approx(0.009 - mp.US_INFLATION)
    assert len(r) == 2046 - 2025 + 1


def test_zeta_d_keeps_the_foreign_share_of_market_debt():
    """New market debt keeps the FY2024/25 foreign share of market debt
    (the non-official external debt over market debt): the program allows
    no new non-concessional external borrowing beyond the Koysha loan, and
    new concessional loans enter through alpha_ODA."""
    z = np.asarray(mp.zeta_D_path())
    assert np.allclose(z, mp.MARKET_FOREIGN_DEBT_SHARE)
    assert 0.05 < mp.MARKET_FOREIGN_DEBT_SHARE < 0.2


def test_transfers_are_targeted_by_programme(packaged, params):
    """eta gives the safety net to the poorest quarter, the fertilizer
    subsidy to the bottom 70 percent, and pensions to the retired in the
    formal groups; it is rebuilt from the packaged demographics."""
    eta = np.array(packaged["eta"])
    assert eta.shape == (80, 7) and eta.sum() == pytest.approx(1.0)
    retire_idx = int(params.retirement_age[0]) - int(params.E)
    expected = mp.transfer_eta(
        packaged["omega_SS"], packaged["lambdas"], retire_idx
    )
    assert np.allclose(eta, expected, atol=1e-12)
    pensions = 0.0 if mp.PENSIONS_ON else mp.PENSIONS_SHARE_OF_GDP
    total = (
        mp.PSNP_SHARE_OF_GDP + mp.FERTILIZER_SUBSIDY_SHARE_OF_GDP + pensions
    )
    share = eta.sum(axis=0)
    assert share[3:5].sum() == pytest.approx(0.0)  # groups 4-5 get nothing
    # with the pension system on, the retired formal groups are paid
    # benefits instead of transfers
    assert share[5:].sum() == pytest.approx(pensions / total)
    assert eta[:retire_idx, 5:].sum() == pytest.approx(
        0.0
    )  # pensions: retired
    assert share[0] > share[1] > share[2]

"""
Tests of the statutory income-tax functions, the defined-benefit pension
parameters and the wealth-share targets.
"""

import numpy as np
import pytest

from ogeth import income
from ogeth import macro_params as mp

LAMBDAS = np.array([0.25, 0.25, 0.2, 0.1, 0.1, 0.09, 0.01])


def test_schedule_rates_follow_the_brackets():
    # 2025 schedule: 2,000 birr a month exempt, then 15/20/25/30/35 percent
    etr, mtr = mp.schedule_tax_rates(
        np.array([12 * 2000, 12 * 3000, 12 * 14000, 12 * 100000]),
        mp.PIT_SCHEDULE_2025,
    )
    assert etr[0] == pytest.approx(0.0)
    assert mtr[0] == pytest.approx(0.0)
    assert etr[1] == pytest.approx(0.15 * 1000 / 3000)
    assert mtr[1] == pytest.approx(0.15)
    tax_14000 = 0.15 * 2000 + 0.20 * 3000 + 0.25 * 3000 + 0.30 * 4000
    assert etr[2] == pytest.approx(tax_14000 / 14000)
    assert mtr[3] == pytest.approx(0.35)
    assert etr[3] < 0.35
    # scaling the thresholds shifts where the brackets bite
    etr_s, _ = mp.schedule_tax_rates(
        np.array([12 * 2400]), mp.PIT_SCHEDULE_2025, scale=1.2
    )
    assert etr_s[0] == pytest.approx(0.0)


def test_gouveia_strauss_fit_tracks_the_schedules():
    incomes = np.array([48_000.0, 168_000.0, 663_000.0, 2_000_000.0])
    for schedule in (mp.PIT_SCHEDULE_2016, mp.PIT_SCHEDULE_2025):
        phi = mp.fit_gs_parameters(schedule)
        etr, mtr = mp.schedule_tax_rates(incomes, schedule)
        assert np.allclose(mp.gs_rates(incomes, phi, "etr"), etr, atol=0.012)
        assert np.allclose(mp.gs_rates(incomes, phi, "mtr"), mtr, atol=0.06)
        assert 0.34 < phi[0] < 0.36  # the 35 percent top rate
    flat = mp.flat_gs_parameters(0.10)
    assert np.allclose(mp.gs_rates(incomes, flat, "etr"), 0.10, atol=1e-6)
    assert np.allclose(mp.gs_rates(incomes, flat, "mtr"), 0.10, atol=1e-6)


def test_statutory_tax_params_shape_and_anchor():
    t = mp.statutory_tax_params()
    assert t["tax_func_type"] == "GS"
    assert len(t["etr_params"]) == 2 and len(t["etr_params"][0][0]) == 3
    assert t["mtrx_params"] == t["etr_params"]
    assert t["mtry_params"][0][0][0] == pytest.approx(0.10)
    # GDP per adult in FY2025/26 birr: 23,851 billion over about 67.7
    # million adults
    assert t["mean_income_data"] == pytest.approx(353_000, rel=0.01)
    # the FY2024/25 schedule is expressed in FY2025/26 birr, so its
    # thresholds sit above the 2016 proclamation's 600 birr a month
    phi16 = t["etr_params"][0][0]
    etr_low = mp.gs_rates(12 * 700, phi16, "etr")
    assert etr_low < mp.gs_rates(12 * 3000, phi16, "etr")
    assert etr_low < 0.10


def test_defined_benefit_parameters():
    d = mp.defined_benefit_params()
    assert d["pension_system"] == "Defined Benefits"
    assert d["retirement_age"] == [60]
    assert d["yr_contrib"] == 40 and d["avg_earn_num_years"] == 3
    # 30 percent after ten years plus 1.25 percent for each of the other 30
    assert d["yr_contrib"] * d["alpha_db"] == pytest.approx(0.675)


def test_compliance_paths_scale_compliance_not_noncompliance():
    paths = mp.program_compliance_paths(compliance_scale=0.5)
    start = np.array(paths["labor_income_tax_noncompliance_rate"][0])
    end = np.array(paths["labor_income_tax_noncompliance_rate"][-1])
    assert start.tolist() == pytest.approx([1, 1, 1, 1, 1, 0.75, 0.5])
    assert end.tolist() == pytest.approx([1, 1, 1, 1, 0.9, 0.5, 0.5])
    cov = np.array(paths["replacement_rate_adjust"][0])
    assert cov.tolist() == pytest.approx(
        (np.array(mp.PENSION_COVERAGE) * mp.PENSION_COVERAGE_SCALE).tolist()
    )
    scaled = mp.program_compliance_paths(pension_coverage_scale=0.2)
    assert np.array(scaled["replacement_rate_adjust"][0])[-1] == pytest.approx(
        0.2
    )


def test_wealth_share_targets_floor_the_bottom_and_sum_to_one():
    target = income.wealth_share_targets(LAMBDAS)
    assert target.shape == (7,)
    assert target.sum() == pytest.approx(1.0)
    assert target[0] == pytest.approx(income.WEALTH_SHARE_FLOOR)
    raw = income.wid_group_shares(
        "ETH", LAMBDAS, variable=income.WID_WEALTH_VARIABLE
    )
    assert raw[0] < 0  # the poorest quarter has negative net wealth in WID
    assert raw[-1] == pytest.approx(0.236, abs=1e-3)
    assert target[-1] > 0.23 and target[5] > 0.33
    b = np.ones((80, 7)) * np.arange(1, 8)
    omega = np.full((80, 7), 1 / 80) * LAMBDAS.reshape(1, 7)
    shares = income.implied_wealth_shares(b, omega)
    assert shares.sum() == pytest.approx(1.0)
    assert shares[0] == pytest.approx(
        0.25 * 1 / (LAMBDAS * np.arange(1, 8)).sum()
    )


def test_steady_state_moments_from_a_synthetic_solution():
    from unittest.mock import MagicMock

    from ogeth import calibrate

    S, J = 80, 7
    p = MagicMock()
    p.omega_SS = np.full((S, J), 1 / S) * LAMBDAS.reshape(1, J)
    ss = {
        "Y": np.array(1.0),
        "n": np.full((S, J), 0.3),
        "b_s": np.ones((S, J)) * np.arange(1, J + 1),
        "before_tax_income": np.ones((S, J)) * np.arange(1, J + 1),
        "iit_revenue": np.array(0.05),
        "agg_pension_outlays": np.array(0.005),
        "B": np.array(2.1),
        "r": 0.08,
        "TR": 0.01,
        "factor": 900000.0,
    }
    c_start = np.array([0, 0, 0, 0, 0, 0.1, 0.2])
    c_end = np.array([0, 0, 0, 0, 0.04, 0.2, 0.2])
    m = calibrate.steady_state_moments(ss, p, c_start, c_end)
    np.testing.assert_allclose(m["n_model"], 0.3)
    assert m["wealth_shares"].sum() == pytest.approx(1.0)
    assert m["pension_outlays"] == pytest.approx(0.005)
    assert m["wealth_ratio"] == pytest.approx(2.1)
    # first-period PIT scales the steady-state take by the compliance-
    # weighted income of the groups at the two dates
    inc = LAMBDAS * np.arange(1, J + 1)
    expected = 0.05 * (c_start * inc).sum() / (c_end * inc).sum()
    assert m["pit_start"] == pytest.approx(expected)
    assert m["r"] == 0.08 and m["factor"] == 900000.0

"""
Tests of the income gradients in fertility and mortality that Calibration
passes to OG-Core's demographics.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from ogeth import calibrate


def test_gradients_are_the_library_tilts_per_percentile_point():
    g = calibrate.demographic_gradients(20, 80)
    # DHS 2024 tilts: fertility -0.736, infant mortality -0.657 per unit of
    # wealth rank, divided by 100 for OG-Core's percentile-point scale
    assert g["fert_gradient"] == pytest.approx(-0.00736, abs=1e-5)
    assert g["infmort_gradient"] == pytest.approx(-0.00657, abs=1e-5)
    mort = g["mort_gradient"]
    assert mort.shape == (100,)
    assert mort[0] == 0.0  # age 0 is carried by infmort_gradient
    assert np.allclose(mort[1:5], -0.00703, atol=1e-5)  # under-five tilt
    assert np.all(mort[5:15] == 0.0)  # no measurement for ages 5-14
    assert np.allclose(mort[15:30], -0.00874, atol=1e-5)  # census 15-29
    assert np.allclose(mort[30:45], 0.00081, atol=1e-5)  # census 30-44
    assert np.all(mort[45:] == 0.0)  # older bands not used


def test_mortality_gradient_steepens_with_income():
    g = calibrate.demographic_gradients(
        20, 80, T=320, start_year=2025, g_y_annual=0.047
    )
    path = g["mort_gradient"]
    assert path.shape == (400, 100)
    base = calibrate.demographic_gradients(20, 80)["mort_gradient"]
    # the rule's change since the 2007 census: -0.2443 ln(1100/210) at
    # the 2024 income, plus one year of growth by the 2025 start
    shift_2025 = -0.2443 * np.log(1100 * 1.047 / 210) / 100
    assert path[0, 20] == pytest.approx(base[20] + shift_2025, abs=1e-6)
    assert path[0, 50] == pytest.approx(shift_2025, abs=1e-6)  # 0 measured
    assert path[0, 3] == pytest.approx(base[3])  # children untouched
    assert path[0, 70] == pytest.approx(0.0)  # rule not applied past 60
    # steeper over time, and flat once income passes the rule's range
    assert path[40, 30] < path[0, 30]
    years_to_cap = np.log(10000 / (1100 * 1.047)) / np.log(1.047)
    assert path[int(years_to_cap) + 5, 30] == pytest.approx(path[-1, 30])
    assert path[-1, 30] == pytest.approx(
        base[30] - 0.2443 * np.log(10000 / 210) / 100, abs=1e-6
    )


def test_gradients_missing_indicator_raises(tmp_path):
    path = tmp_path / "g.csv"
    path.write_text(
        "indicator,year,sex,age_lo,age_hi,measure,slope,ratio,q1,q2,q3,q4,q5,source\n"
        "TFR,2024,all,,,,-0.7,1.9,5,4,4,4,3,x\n"
    )
    with pytest.raises(ValueError):
        calibrate.demographic_gradients(20, 80, path=str(path))


def test_calibration_passes_gradients_to_demographics():
    p = MagicMock()
    p.I, p.M, p.E, p.S, p.T, p.J = 1, 1, 20, 80, 320, 7
    p.start_year = 2025
    p.lambdas = np.array([0.25, 0.25, 0.2, 0.1, 0.1, 0.09, 0.01])
    p.g_y = 0.04
    p.retirement_age = np.array([65])
    omega = np.full((80, 7), 1 / 80) * p.lambdas.reshape(1, 7)
    demog = {"omega_SS": omega, "g_n": np.full(400, 0.02)}
    with patch("ogeth.calibrate.macro_params") as mock_macro:
        mock_macro.get_macro_params.return_value = {}
        mock_macro.derive_remittance_params.return_value = {}
        mock_macro.transfer_eta.return_value = np.zeros((80, 7))
        with patch("ogcore.demographics.get_pop_objs") as mock_demog:
            mock_demog.return_value = demog
            with patch("ogeth.calibrate.income.get_e_interp") as mock_e:
                mock_e.return_value = np.ones((80, 7))
                c = calibrate.Calibration(p, update_from_api=True)
    kwargs = mock_demog.call_args.kwargs
    assert kwargs["country_id"] == calibrate.UN_COUNTRY_CODE
    np.testing.assert_array_equal(kwargs["income_percentiles"], p.lambdas)
    assert kwargs["fert_gradient"] == pytest.approx(-0.00736, abs=1e-5)
    assert kwargs["infmort_gradient"] == pytest.approx(-0.00657, abs=1e-5)
    assert kwargs["mort_gradient"].shape == (400, 100)
    assert "e" in c.get_dict()

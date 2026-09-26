"""
Tests of income.py: the WID x NTA reshaping of the OG-USA ability matrix.

The OG-USA download is replaced by a synthetic matrix so the tests run
offline; the Ethiopian and US inputs are the packaged data files.
"""

import json
from importlib.resources import files

import numpy as np
import pytest

from ogeth import income

LAMBDAS = np.array([0.25, 0.25, 0.2, 0.1, 0.1, 0.09, 0.01])
LAMBDAS_USA = np.array(
    [0.25, 0.25, 0.2, 0.1, 0.1, 0.09, 0.005, 0.004, 0.0009, 0.0001]
)


@pytest.fixture
def synthetic_usa_e(monkeypatch):
    """A smooth (80, 10) matrix standing in for the OG-USA download."""
    ages = income.model_ages(income.OGUSA_E, income.OGUSA_S)
    hump = 1 + 0.02 * (ages - 20) - 0.0003 * (ages - 20) ** 2
    groups = np.array([0.4, 0.55, 0.8, 1.05, 1.35, 2.5, 5.0, 7.0, 15.0, 40.0])
    e_usa = hump.reshape(-1, 1) * groups.reshape(1, -1)
    monkeypatch.setattr(
        income, "load_ogusa_e", lambda: (e_usa.copy(), LAMBDAS_USA.copy())
    )
    return e_usa


@pytest.fixture(scope="module")
def packaged():
    content = (
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(content)


def test_wid_group_shares_sum_to_one():
    for country in ("ETH", "US"):
        shares = income.wid_group_shares(country, LAMBDAS)
        assert shares.shape == (7,)
        assert shares.sum() == pytest.approx(1.0, abs=1e-3)
        assert (shares > 0).all()


def test_wid_group_shares_match_source():
    """The Ethiopian bottom quarter and top percent are read off WID."""
    shares = income.wid_group_shares("ETH", LAMBDAS)
    assert shares[0] == pytest.approx(0.0439, abs=1e-4)
    assert shares[-1] == pytest.approx(0.1046, abs=2e-4)
    assert shares[:2].sum() == pytest.approx(0.1734, abs=1e-4)


def test_wid_group_shares_reject_unsupported_groups():
    with pytest.raises(ValueError):
        income.wid_group_shares("ETH", np.array([0.3, 0.3, 0.4]))


def test_wid_gini_values():
    assert income.wid_gini("ETH") == pytest.approx(0.5157)
    assert income.wid_gini("US") == pytest.approx(0.5831)


def test_scale_groups_to_shares_hits_the_target():
    rng = np.random.default_rng(1)
    e = rng.uniform(0.5, 2.0, size=(80, 7)) * np.arange(1, 8)
    omega = rng.uniform(0.5, 1.5, size=(80, 7)) * LAMBDAS.reshape(1, 7)
    omega /= omega.sum()
    target = income.wid_group_shares("ETH", LAMBDAS)
    scaled = income.scale_groups_to_shares(e, omega, target)
    np.testing.assert_allclose(
        income.implied_group_shares(scaled, omega), target / target.sum()
    )
    # only the level of each group's profile moves, not its shape
    np.testing.assert_allclose(
        scaled / e, np.broadcast_to((scaled / e)[0:1, :], e.shape)
    )
    with pytest.raises(ValueError):
        income.scale_groups_to_shares(e, omega, np.array([0.5, 0.5]))
    with pytest.raises(ValueError):
        income.scale_groups_to_shares(e, omega, -target)


def test_tilt_to_gini_hits_the_target():
    rng = np.random.default_rng(2)
    e = rng.uniform(0.5, 2.0, size=(80, 7)) * np.arange(1, 8)
    omega = rng.uniform(0.5, 1.5, size=(80, 7)) * LAMBDAS.reshape(1, 7)
    omega /= omega.sum()
    for target in (0.35, 0.516, 51.6):
        tilted = income.tilt_to_gini(e, omega, LAMBDAS, target)
        want = target / 100 if target > 1 else target
        assert income.implied_gini(tilted, omega, LAMBDAS) == pytest.approx(
            want, abs=1e-6
        )
    with pytest.raises(ValueError):
        income.tilt_to_gini(e, omega, LAMBDAS, 0.0)


def test_age_factor_peaks_early_and_falls():
    """Ethiopian per-worker earnings peak earlier and fall faster after 50
    than US earnings, and the factor is flat at the oldest ages."""
    ages = income.model_ages(20, 80)
    factor = income.earnings_age_factor(ages)
    assert factor.shape == (80,)
    assert np.isfinite(factor).all() and (factor > 0).all()
    assert factor[0] > factor[20] > factor[40]
    assert factor[45] < 0.7
    old = ages >= income.OLDEST_MEASURED_AGE
    assert np.allclose(factor[old], factor[old][0])


def test_employment_ratio_and_nta_profiles():
    ages = np.array([22.0, 42.0, 70.0, 95.0])
    eth = income.employment_ratio("ETH", 2005, ages)
    usa = income.employment_ratio("US", 2006, ages)
    assert eth[0] == pytest.approx(0.7941, abs=1e-4)
    assert usa[2] == pytest.approx(0.1495, abs=1e-4)
    assert eth[3] == eth[2]  # held constant beyond the last band
    profile = income.nta_labor_income("ETH", ages)
    assert profile[1] > profile[0] > profile[2] > profile[3] > 0
    with pytest.raises(ValueError):
        income.employment_ratio("ETH", 1900, ages)


def test_interpolate_usa_e_identity_and_grid(synthetic_usa_e):
    same = income.interpolate_usa_e(
        synthetic_usa_e, LAMBDAS_USA, 20, 80, LAMBDAS_USA
    )
    np.testing.assert_allclose(same, synthetic_usa_e)
    e7 = income.interpolate_usa_e(
        synthetic_usa_e, LAMBDAS_USA, 20, 80, LAMBDAS
    )
    assert e7.shape == (80, 7)
    # the first six groups share the US midpoints, so they are copied
    np.testing.assert_allclose(e7[:, :6], synthetic_usa_e[:, :6])
    e40 = income.interpolate_usa_e(
        synthetic_usa_e, LAMBDAS_USA, 20, 40, LAMBDAS
    )
    assert e40.shape == (40, 7)
    with pytest.raises(RuntimeError):
        income.interpolate_usa_e(
            synthetic_usa_e, LAMBDAS_USA, 20, 80, np.array([0.5, 0.4999, 1e-4])
        )


@pytest.mark.parametrize("S", [80, 40])
def test_get_e_interp_shape_and_normalization(synthetic_usa_e, S):
    rng = np.random.default_rng(0)
    omega = rng.uniform(0.5, 1.5, size=(S, 7)) * LAMBDAS.reshape(1, 7)
    omega /= omega.sum()
    e = income.get_e_interp(20, S, 7, LAMBDAS, omega)
    assert e.shape == (S, 7)
    assert (e * omega).sum() == pytest.approx(1.0)
    assert (e > 0).all()
    # a one-dimensional age distribution is spread with lambdas
    e1 = income.get_e_interp(20, S, 7, LAMBDAS, omega.sum(axis=1))
    assert (e1 * omega.sum(axis=1).reshape(S, 1) * LAMBDAS).sum() == (
        pytest.approx(1.0)
    )


def test_get_e_interp_applies_both_factors(synthetic_usa_e):
    """Relative to the interpolated US matrix, the age pattern of every
    group follows the age factor and the group pattern at every age
    follows the group factor."""
    omega = np.full((80, 7), 1 / 80) * LAMBDAS.reshape(1, 7)
    e = income.get_e_interp(20, 80, 7, LAMBDAS, omega)
    base = income.interpolate_usa_e(
        synthetic_usa_e, LAMBDAS_USA, 20, 80, LAMBDAS
    )
    ratio = e / base
    age_factor = income.earnings_age_factor(income.model_ages(20, 80))
    for j in range(7):
        np.testing.assert_allclose(
            ratio[:, j] / ratio[0, j], age_factor / age_factor[0]
        )
    np.testing.assert_allclose(
        income.implied_group_shares(e, omega),
        income.wid_group_shares("ETH", LAMBDAS),
        atol=1e-4,
    )


def test_get_e_interp_alternative_targets(synthetic_usa_e):
    omega = np.full((80, 7), 1 / 80) * LAMBDAS.reshape(1, 7)
    own = np.array([0.06, 0.14, 0.17, 0.11, 0.15, 0.27, 0.10])
    e_own = income.get_e_interp(20, 80, 7, LAMBDAS, omega, group_shares=own)
    np.testing.assert_allclose(
        income.implied_group_shares(e_own, omega), own, atol=1e-6
    )
    e_gini = income.get_e_interp(20, 80, 7, LAMBDAS, omega, gini_to_match=0.45)
    assert income.implied_gini(e_gini, omega, LAMBDAS) == pytest.approx(
        0.45, abs=1e-6
    )
    assert (e_gini * omega).sum() == pytest.approx(1.0)
    with pytest.raises(ValueError):
        income.get_e_interp(
            20, 80, 7, LAMBDAS, omega, group_shares=own, gini_to_match=0.45
        )


def test_packaged_e_is_the_reshaped_matrix(packaged):
    """The shipped e carries the WID group pattern and the NTA age pattern
    and averages to one over the shipped population."""
    e = np.asarray(packaged["e"])
    omega = np.asarray(packaged["omega_SS"])
    lambdas = np.asarray(packaged["lambdas"])
    assert e.shape == (80, 7)
    assert (e * omega).sum() == pytest.approx(1.0, abs=1e-6)
    shares = income.implied_group_shares(e, omega)
    np.testing.assert_allclose(
        shares, income.wid_group_shares("ETH", lambdas), atol=1e-4
    )
    means = shares / lambdas
    assert means[0] == pytest.approx(0.176, abs=0.005)
    assert means[-1] == pytest.approx(10.47, abs=0.05)
    gini = income.implied_gini(e, omega, lambdas)
    assert gini == pytest.approx(0.511, abs=0.005)
    profile = (e * omega).sum(axis=1) / omega.sum(axis=1)
    thirties, fifties, sixties = (
        profile[10:20].mean(),
        profile[30:40].mean(),
        profile[40:50].mean(),
    )
    assert fifties / thirties < 1.2
    assert sixties / thirties < 0.8


def test_write_json_parameters_only_touches_requested_keys(tmp_path):
    path = tmp_path / "params.json"
    path.write_text(json.dumps({"a": 1, "e": [[1.0]], "z": "keep"}))
    income.write_json_parameters(str(path), {"e": [[2.0, 3.0]]})
    saved = json.loads(path.read_text())
    assert saved == {"a": 1, "e": [[2.0, 3.0]], "z": "keep"}

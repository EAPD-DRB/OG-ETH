"""
Tests of labor.py: the LFMS labor supply targets and the chi_n update.

The steady-state solves behind estimate_chi_n are not run here; the
update rule and the targets are tested on their own.
"""

import json
from importlib.resources import files

import numpy as np
import pytest
from ogcore.parameters import Specifications

from ogeth import income, labor


@pytest.fixture(scope="module")
def p():
    content = (
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .read_text(encoding="utf-8")
    )
    spec = Specifications(baseline=True)
    spec.update_specifications(json.loads(content))
    return spec


def test_hours_per_person_is_a_hump():
    df = labor.hours_per_person()
    hpp = df.set_index("age_band").hours_per_person
    assert hpp["30-34"] == pytest.approx(0.781 * 32.0)
    assert hpp["20-24"] < hpp["30-34"] > hpp["50-54"] > hpp["65+"]


def test_labor_supply_target_level_shape_and_floor():
    target = labor.labor_supply_target(20, 80)
    ages = income.model_ages(20, 80)
    assert target.shape == (80,)
    # prime-age Ethiopians work about 25 hours a week per person, which is
    # a bit over a fifth of a 16-hour day, seven days a week
    prime = target[(ages >= 30) & (ages < 40)].mean()
    assert prime == pytest.approx(25 / labor.WEEKLY_TIME_ENDOWMENT, rel=0.03)
    assert target[0] < prime
    # beyond the survey the target falls with the NTA profile, never
    # below the floor
    old = ages > labor.OLDEST_SURVEY_AGE
    assert np.all(np.diff(target[old]) <= 1e-12)
    assert target[-1] < 0.03
    assert target.min() >= labor.MIN_LABOR_SUPPLY
    scaled = labor.labor_supply_target(20, 80, ltilde=2.0)
    np.testing.assert_allclose(scaled, 2.0 * target)


def test_average_labor_supply_weights_by_population():
    n = np.array([[0.2, 0.4], [0.5, 0.5]])
    omega = np.array([[0.1, 0.3], [0.3, 0.3]])
    np.testing.assert_allclose(
        labor.average_labor_supply(n, omega), [0.35, 0.5]
    )


def test_chi_n_step_is_exact_on_target_and_monotone(p):
    chi_n = labor.steady_state_chi_n(p)
    assert chi_n.shape == (p.S,)
    target = labor.labor_supply_target(p.E, p.S, p.ltilde)
    same = labor.chi_n_step(chi_n, target, target, p)
    np.testing.assert_allclose(same, chi_n)
    # working more than the target in the model calls for a heavier
    # disutility weight
    heavier = labor.chi_n_step(chi_n, 1.5 * target, target, p)
    lighter = labor.chi_n_step(chi_n, 0.5 * target, target, p)
    free = chi_n < labor.MAX_CHI_N
    assert free.any()
    assert (heavier[free] > chi_n[free]).all()
    assert (heavier <= labor.MAX_CHI_N).all()
    assert (lighter < chi_n).all()


def test_fit_table_bands(p):
    target = labor.labor_supply_target(p.E, p.S, p.ltilde)
    table = labor.fit_table(target, target, p.E, p.S)
    assert list(table.age_band[:2]) == ["20-24", "25-29"]
    assert len(table) == 12
    np.testing.assert_allclose(table.model, table.target)
    assert table.target_hours.iloc[2] == pytest.approx(
        table.target.iloc[2] * labor.WEEKLY_TIME_ENDOWMENT
    )


def test_packaged_chi_n_is_not_the_ogusa_profile(p):
    """The shipped chi_n has been recalibrated to Ethiopian hours: it no
    longer starts at OG-USA's 38.12 for age 20."""
    chi_n = labor.steady_state_chi_n(p)
    assert chi_n.shape == (80,)
    assert (chi_n > 0).all()
    assert chi_n[0] != pytest.approx(38.12000874)

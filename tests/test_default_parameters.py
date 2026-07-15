"""
Tests that the packaged default parameters carry the informality calibration.

Informality is modeled as graded income-tax NON-compliance by lifetime-income
group (OG-Core by-(t, j) noncompliance parameters, PR #816): the bottom five of
seven groups (90% of households by population weight, close to ILO's 85%
informal-employment figure) pay none of the income tax owed, group 6 pays half,
and the top group complies fully. The compliant-group effective rate
(etr 0.1313) is solved from a revenue identity to hit the PIT anchor; the
marginal rate (0.35) is Ethiopia's statutory top PIT rate; the CIT collections
factor (0.327) is re-anchored so corporate-tax revenue matches actual
collections. income_tax_filer stays all-ones on purpose: informality is carried
by non-compliance, not by non-filing.

Anchors: IMF SIP 2025/108 (= Country Report 25/189) para 9 (PIT 1.4%, CIT 1.7%
of GDP); IMF Country Report 26/20 Table 2b (direct taxes 3.1% of GDP); ILO 2021
(informal employment 85% of total).

These are fast, structural pins on the shipped JSON. The revenue split this
calibration produces (PIT 1.39%, CIT 1.71%, direct 3.10% of GDP) requires a
steady-state solve and is therefore intentionally NOT asserted here.
"""

import json
from importlib.resources import files

import numpy as np
import pytest
from ogcore.parameters import Specifications

# Expected income-tax non-compliance by lifetime-income group (low -> high),
# shared by the labor and capital rows.
NONCOMPLIANCE_BY_GROUP = [1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.0]


@pytest.fixture(scope="module")
def defaults():
    """Raw packaged default-parameters JSON as a dict."""
    content = (
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(content)


@pytest.fixture(scope="module")
def p(defaults):
    """Packaged defaults loaded into ogcore Specifications.

    update_specifications validates and broadcasts to the full T dimension, so
    tests index the steady-state row (-1) to stay robust to that broadcast.
    """
    spec = Specifications(baseline=True)
    spec.update_specifications(defaults)
    return spec


def test_packaged_defaults_validate(p):
    """Shipped defaults load into Specifications with no validation errors."""
    assert not p.errors


def test_informality_tax_rates(p):
    """Compliant-group effective and marginal tax rates carry the anchors."""
    # linear tax funcs => one param per (t, age); index SS row, first age.
    assert p.tax_func_type == "linear"
    assert np.asarray(p.etr_params)[-1, 0].tolist() == pytest.approx([0.1313])
    assert np.asarray(p.mtrx_params)[-1, 0].tolist() == pytest.approx([0.35])
    assert np.asarray(p.mtry_params)[-1, 0].tolist() == pytest.approx([0.2])


def test_informality_noncompliance_by_group(p):
    """Bottom 5 groups fully non-compliant, group 6 half, top compliant."""
    labor = np.asarray(p.labor_income_tax_noncompliance_rate)[-1]
    capital = np.asarray(p.capital_income_tax_noncompliance_rate)[-1]
    assert labor.tolist() == pytest.approx(NONCOMPLIANCE_BY_GROUP)
    assert capital.tolist() == pytest.approx(NONCOMPLIANCE_BY_GROUP)


def test_cit_collections_factor(p):
    """CIT collections factor re-anchored to hit corporate-tax revenue."""
    factor = float(np.asarray(p.adjustment_factor_for_cit_receipts)[-1])
    assert factor == pytest.approx(0.327)


def test_all_households_are_filers(p):
    """income_tax_filer stays all-ones: non-compliance, not non-filing."""
    assert np.asarray(p.income_tax_filer)[-1].tolist() == pytest.approx(
        [1.0] * 7
    )


def test_informality_dimensions_consistent(defaults, p):
    """Group vectors match the 7 income groups; ~90% weight in the tail."""
    lambdas = np.asarray(p.lambdas).flatten()
    assert lambdas.shape[0] == 7
    assert len(defaults["labor_income_tax_noncompliance_rate"][0]) == 7
    assert len(defaults["capital_income_tax_noncompliance_rate"][0]) == 7
    # Bottom 5 groups (fully non-compliant) carry ~90% of households.
    assert lambdas[:5].sum() == pytest.approx(0.90)

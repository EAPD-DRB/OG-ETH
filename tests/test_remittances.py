"""
Tests of the remittance calibration in the packaged single-industry JSON.

Remittances are calibrated as a share of GDP that follows the IMF program's
private-transfers projection over the program years (5.6 to 4.1 percent of
GDP) and then stays where the program leaves it. That takes two things:
``alpha_RM_1`` at the measured level and ``alpha_RM_T`` at the program
endpoint, and a ``g_RM`` path built on ``g_n`` so ``aggregates.get_RM`` moves
detrended remittances along the program instead of eroding them (along the
actual path RM/Y then also moves with output's deviation from trend). These
tests pin the level against its source and assert the share follows the
program exactly -- the second is the one that catches a stale ``g_RM`` after
a demographics regeneration.

No model solve is involved.
"""

import copy
import json
from importlib.resources import files

import numpy as np
import pytest
from ogcore import aggregates as aggr
from ogcore.parameters import Specifications

from ogeth import macro_params as remittances

# IMF Country Report 26/174 (fifth ECF review, June 2026), Table 4a,
# FY2024/25 actual: private transfers (net) US$7,037 million, 5.6 percent of
# GDP. The World Bank WDI personal-remittances series (BX.TRF.PWKR.CD.DT)
# puts the same inflow at US$7.14 billion for calendar 2024.
IMF_PRIVATE_TRANSFERS_USD_MN = 7037
IMF_PRIVATE_TRANSFERS_SHARE_OF_GDP = 0.056
EXPECTED_ALPHA_RM = 0.056


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


def test_alpha_rm_matches_imf_private_transfers(packaged):
    """The level is the observed FY2024/25 private-transfers share of GDP."""
    assert packaged["alpha_RM_1"] == EXPECTED_ALPHA_RM
    assert packaged["alpha_RM_1"] == IMF_PRIVATE_TRANSFERS_SHARE_OF_GDP


def test_packaged_long_run_share_is_the_measured_level(packaged):
    """History baseline: no level shift between the first period and the
    steady state."""
    expected = remittances.remittance_level_params()
    assert packaged["alpha_RM_1"] == expected["alpha_RM_1"]
    assert packaged["alpha_RM_T"] == expected["alpha_RM_T"]
    assert packaged["alpha_RM_T"] == packaged["alpha_RM_1"]


def test_program_long_run_share_is_the_program_endpoint():
    """Program scenario: the long-run share is the last program-year
    projection, held like the other program series (4.1 percent of GDP)."""
    expected = remittances.remittance_level_params(scenario="program")
    assert expected["alpha_RM_1"] == pytest.approx(EXPECTED_ALPHA_RM)
    assert expected["alpha_RM_T"] == pytest.approx(
        remittances.IMF_PRIVATE_TRANSFERS[-1] / 100
    )


def test_packaged_g_rm_keeps_remittances_on_trend(params):
    """The property the packaged calibration rests on.

    ``get_RM`` compounds ``(1 + g_RM[t]) / (exp(g_y) * (1 + g_n[t-1]))``
    independently of output, so with trend output (Y = 1 in detrended
    units) the share must come out exactly at alpha_RM in every period; a
    ``g_RM`` that does not track ``g_n`` makes it drift for the first tG1
    periods. With Ethiopia's growth rates a scalar ``g_RM = 0`` eroded
    remittances relative to trend by about 7 percent a year.
    """
    Y = np.ones(params.T + params.S)
    ratio = aggr.get_RM(Y, params, "TPI")[: params.T] / Y[: params.T]
    assert np.allclose(ratio, params.alpha_RM_T, atol=1e-12)


def test_program_g_rm_moves_remittances_along_the_program_then_holds(
    params,
):
    """Program scenario: on trend the share comes out exactly at the glide
    in each program year and stays at the endpoint afterwards."""
    p = copy.deepcopy(params)
    p.update_specifications(
        remittances.scenario_params(params, scenario="program")
    )
    Y = np.ones(params.T + params.S)
    ratio = aggr.get_RM(Y, p, "TPI")[: params.T] / Y[: params.T]
    program = remittances.program_remittance_shares() / 100
    assert np.allclose(ratio[: program.size], program, atol=1e-12)
    assert np.allclose(ratio[program.size :], p.alpha_RM_T, atol=1e-12)


def test_program_shares_glide_between_the_anchors():
    """The model follows the program's start and end values with an even
    decline in between: the year-by-year projection has jumps that OG-Core's
    bounds on g_RM do not admit."""
    shares = remittances.program_remittance_shares()
    imf = np.array(remittances.IMF_PRIVATE_TRANSFERS)
    assert shares[0] == imf[0] and shares[-1] == pytest.approx(imf[-1])
    assert np.all(np.diff(shares) < 0)
    assert np.allclose(np.diff(np.log(shares)), np.diff(np.log(shares))[0])
    p = Specifications()
    lo, hi = -0.02, 0.15
    g_RM = remittances.program_share_g_RM(p.g_y, np.full(p.T + p.S, 0.03))
    assert g_RM.min() > lo and g_RM.max() < hi


def test_packaged_g_rm_is_consistent_with_packaged_g_n(params, packaged):
    """g_RM is derived from g_n, so a demographics regeneration that forgets
    to rewrite it leaves the two inconsistent."""
    expected = remittances.flat_share_g_RM(params.g_y, params.g_n)
    assert np.allclose(np.array(packaged["g_RM"]), expected, atol=1e-12)


def test_flat_share_g_rm_is_not_representable_as_a_scalar(params):
    """Documents why g_RM is a path: g_n moves enough over the transition that
    no single constant holds the share flat."""
    g_RM = remittances.flat_share_g_RM(params.g_y, params.g_n)
    assert g_RM.max() - g_RM.min() > 0.01


def test_steady_state_remittances_equal_alpha_rm_times_output(params):
    """SS mode ignores g_RM entirely -- the share there is alpha_RM_T alone."""
    assert aggr.get_RM(np.ones(1), params, "SS") == pytest.approx(
        params.alpha_RM_T
    )


def test_eta_rm_is_a_distribution(packaged):
    """eta_RM allocates all of aggregate remittances: (S, J), sums to 1."""
    eta = np.array(packaged["eta_RM"])
    assert eta.shape == (80, 7)
    assert eta.min() >= 0
    assert eta.sum() == pytest.approx(1.0)


def test_eta_rm_is_per_capita_within_each_group(packaged):
    """Within a lifetime-income group, every household receives the same
    amount: the age profile of eta_RM is the group's population profile."""
    eta = np.array(packaged["eta_RM"])
    omega_SS = np.array(packaged["omega_SS"])
    within = omega_SS / omega_SS.sum(axis=0, keepdims=True)
    group_share = eta.sum(axis=0)
    assert np.allclose(eta, within * group_share, atol=1e-12)


def test_packaged_eta_rm_is_consistent_with_packaged_demographics(packaged):
    """eta_RM is rebuilt from omega_SS and the quintile value shares, so a
    regeneration that forgets it leaves the matrix stale."""
    expected = remittances.remittance_eta(
        packaged["omega_SS"], packaged["lambdas"]
    )
    assert np.allclose(np.array(packaged["eta_RM"]), expected, atol=1e-12)


def test_quintile_value_shares_follow_the_2010_survey():
    """World Bank / Bendixen & Amandi (2010) recipient income brackets:
    9% below ETB 1,000, 47% at ETB 1,000-3,500, 37% above ETB 3,500, with
    7% not answering. Renormalized over respondents and mapped to quintile
    pairs: 9.7% to the bottom two, 50.5% to the middle two, 39.8% to the
    top quintile."""
    q = np.array(remittances.RM_QUINTILE_VALUE_SHARES)
    assert q.shape == (5,)
    assert q.sum() == pytest.approx(1.0)
    assert q[:2].sum() == pytest.approx(9 / 93, abs=1e-12)
    assert q[2:4].sum() == pytest.approx(47 / 93, abs=1e-12)
    assert q[4] == pytest.approx(37 / 93, abs=1e-12)
    assert q[0] == q[1] and q[2] == q[3]


def test_eta_rm_tilts_remittances_toward_higher_income_groups(packaged):
    """The survey rejects the population-proportional default: the bottom
    half of households receives well under its population share and the top
    fifth well over."""
    group_share = np.array(packaged["eta_RM"]).sum(axis=0)
    lambdas = np.array(packaged["lambdas"])
    assert group_share[:2].sum() < 0.5 * lambdas[:2].sum()
    assert group_share[4:].sum() > 1.5 * lambdas[4:].sum()


def test_remittance_eta_maps_uniform_quintiles_to_population_shares():
    """With remittance value spread evenly across quintiles, every group
    receives exactly its population share -- OG-Core's default allocation."""
    lambdas = [0.25, 0.25, 0.2, 0.1, 0.1, 0.09, 0.01]
    omega_SS = np.tile(np.array(lambdas) / 80, (80, 1))
    eta = remittances.remittance_eta(omega_SS, lambdas, [0.2] * 5)
    assert np.allclose(eta.sum(axis=0), lambdas)

"""
Ethiopia Youth Dividend — Full Analysis
========================================
7 Thematic Dimensions | 25 Policy Scenarios | 2025–2050
Concept Note: "Ethiopia's Youth Dividend: A Comprehensive Macroeconomic
Assessment" (Full Version)

All 25 scenarios run against the D1 common baseline (UN WPP 2024 medium-
fertility, current fiscal policy). Results saved to
examples/OG-ETH-YouthDividend-Full/.

SCENARIO REGISTER
-----------------
D1  Baseline — UN WPP 2024 medium-fertility, current policies  (= BASE)
D2  Accelerated fertility decline (TFR → 2.5 by 2035 not 2045)
D3  High youth mortality shock (+15% mortality, ages 20–35)
D4  Upper bound — high-fertility UN variant

E2  Moderate TVET expansion (+10% age-efficiency young workers)
E3  Strong university quality improvement (+20%)
E4  Combined TVET + university reform (+25%)

L2  Moderate formalisation — formal share 13% → 25% by 2035
L3  Strong formalisation — formal share 13% → 40% by 2035
L4  Full formalisation — formal share 13% → 55% (middle-income avg)

G2  Partial FLFP convergence by 2040 (female LFP halfway toward male)
G3  Full FLFP convergence by 2040
G4  Accelerated FLFP convergence by 2030

M2  Moderate brain drain (graduate emigration doubles by 2030)
M3  Severe brain drain (20% of graduates leave per decade)
M4  Brain gain — skilled diaspora return raises capital & productivity

F2  Education investment surge (+2 % of GDP govt education spending)
F3  Youth employment subsidy (wage subsidy for formal youth hiring)
F4  Gender inclusion investment (targeted transfers + participation)
F5  IMF fiscal consolidation constraint (−1.5 % of GDP youth spending)

I1  Moderate integrated package (E2 + L2 + G2 + F2)
I2  Ambitious integrated package (E3 + L3 + G3 + F2)
I3  Maximum dividend (E4 + L4 + G4 + M4)
I4  Delayed action — same as I2 but reforms begin 2035, not 2025

PARAMETER MAPPING
-----------------
Scenario  | Primary parameters changed
----------|---------------------------------------------
D2        | g_n (faster decline), g_n_ss (lower long-run)
D3        | rho (mortality +15% ages 20–35 = model periods 0–15)
D4        | g_n (higher path), g_n_ss (higher long-run)
E2-E4     | e (age-efficiency +10/20/25% for ages 20–50)
L2-L4     | e (+15/34/53% working-age via formalisation productivity premium)
          | frisch (+0.05/0.10/0.15 for reduced labour-market frictions)
G2        | e (uniform +15% — halfway female LFP convergence)
G3        | e (uniform +30% — full female LFP convergence by 2040)
G4        | e (uniform +30% by 2030, implemented as full target)
M2        | e (top-2 ability groups −20% for working-age — brain drain)
M3        | e (top-2 ability groups −35% — severe brain drain)
M4        | e (top-2 ability groups +25% — brain gain) + zeta_K +0.10
F2        | alpha_G +0.020 (govt education expenditure surge)
F3        | e (+10% ages 20–35) + frisch +0.10 (subsidy → formalisation)
F4        | alpha_T +0.010 + e (uniform +10% — gender investment channel)
F5        | alpha_G −0.015 (IMF fiscal consolidation)
I1-I3     | Multiplicative combination of constituent shocks
I4        | I2 shocks, but p.e for periods t=0..9 reverts to baseline
          | (10-year implementation delay — directly assigned post-update)

FORMALISATION PRODUCTIVITY PREMIUM (L2-L4 derivation)
------------------------------------------------------
Formal workers earn ≈2.5× informal workers in Ethiopia (ILO 2023).
Normalised baseline avg productivity = 0.13×2.5 + 0.87×1.0 = 1.195
L2 (formal 25%): 0.25×2.5 + 0.75×1.0 = 1.375 → boost = +15.1%
L3 (formal 40%): 0.40×2.5 + 0.60×1.0 = 1.600 → boost = +33.9%
L4 (formal 55%): 0.55×2.5 + 0.45×1.0 = 1.825 → boost = +52.7%

GENDER FLFP BOOST DERIVATION (G2-G4)
--------------------------------------
Ethiopia female LFP ≈ 39%, male ≈ 77% (ILO 2023)
50/50 gender split assumed; aggregate effective labour/worker:
  Current  = 0.5×77% + 0.5×39% = 58% of male-equivalent
  Full conv = 0.5×77% + 0.5×77% = 77% of male-equivalent
  Gain = (77−58)/58 ≈ 33%; rounded to 30% net of frictions
  G2 half convergence ≈ +15%; G3/G4 full convergence ≈ +30%
"""

import multiprocessing
import os
import json
import time
import copy
from importlib.resources import files

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless — no display needed
import matplotlib.pyplot as plt
from distributed import Client

from ogeth.calibrate import Calibration
from ogcore.parameters import Specifications
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle
from ogeth.utils import is_connected

import dask
dask.config.set(scheduler="synchronous")
plt.style.use("ogcore.OGcorePlots")


# ===========================================================================
# Core helpers
# ===========================================================================

def _e0(p):
    """Return base-period e as (S, J) regardless of stored shape."""
    e = np.array(p.e, dtype=float)
    return e[0] if e.ndim == 3 else e


def _age_ramp(S, starting_age, peak_age, taper_age, magnitude):
    """
    (S,) array: full `magnitude` from starting_age to peak_age,
    then linear taper to 0 at taper_age, then 0.
    """
    ages = np.linspace(starting_age, starting_age + S, S, endpoint=False)
    f = np.zeros(S)
    for i, a in enumerate(ages):
        if a <= peak_age:
            f[i] = magnitude
        elif a < taper_age:
            f[i] = magnitude * (taper_age - a) / (taper_age - peak_age)
    return f


def _working_age_ramp(S, starting_age, core_start=20, core_end=55,
                      taper_end=65, magnitude=1.0):
    """(S,) array with full `magnitude` from core_start to core_end,
    tapering to 0 by taper_end."""
    ages = np.linspace(starting_age, starting_age + S, S, endpoint=False)
    f = np.zeros(S)
    for i, a in enumerate(ages):
        if core_start <= a <= core_end:
            f[i] = magnitude
        elif core_end < a < taper_end:
            f[i] = magnitude * (taper_end - a) / (taper_end - core_end)
    return f


def _apply_age_boost(e0, age_factor):
    """e0: (S,J); age_factor: (S,) → new (S,J)."""
    return e0 * (1.0 + age_factor)[:, np.newaxis]


def build_baseline(baseline_dir, num_workers):
    """Construct a fully-calibrated Specifications baseline object."""
    p = Specifications(
        baseline=True,
        num_workers=num_workers,
        baseline_dir=baseline_dir,
        output_base=baseline_dir,
    )
    with files("ogeth").joinpath("ogeth_default_parameters.json").open("r") as f:
        defaults = json.load(f)
    p.update_specifications(defaults)
    if is_connected():
        c = Calibration(p, update_from_api=False)
        p.update_specifications(c.get_dict())
    return p


def run_scenario(p_base, scenario_dir, param_updates,
                 direct_overrides=None):
    """
    Create a reform Specifications derived from p_base.

    Args:
        p_base: calibrated baseline Specifications
        scenario_dir: where to write output
        param_updates: dict passed to update_specifications (accepts (S,J) e)
        direct_overrides: dict of {attr: np.ndarray} assigned directly to p
            after update_specifications, bypassing paramtools validation.
            Use for time-varying e [(T,S,J)] or rho [(T,S)] arrays.

    Returns:
        Specifications ready for runner()
    """
    p = copy.deepcopy(p_base)
    p.baseline = False
    p.output_base = scenario_dir
    if param_updates:
        p.update_specifications(param_updates)
    if direct_overrides:
        for attr, val in direct_overrides.items():
            setattr(p, attr, val)
    return p


def already_done(scenario_dir):
    return os.path.exists(os.path.join(scenario_dir, "TPI", "TPI_vars.pkl"))


def safe_run(p, client, label):
    if already_done(p.output_base):
        print(f"  {label}: already complete — skipping")
        return
    t0 = time.time()
    runner(p, time_path=True, client=client)
    print(f"  {label}: done in {time.time()-t0:.0f}s")


def pct_table(base_dir, reform_dir, num_years, start_year):
    """Return macro_table % change DataFrame, or None if output missing."""
    try:
        bt = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
        bp = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
        rt = safe_read_pickle(os.path.join(reform_dir, "TPI", "TPI_vars.pkl"))
        rp = safe_read_pickle(os.path.join(reform_dir, "model_params.pkl"))
        return ot.macro_table(
            bt, bp, reform_tpi=rt, reform_params=rp,
            var_list=["Y", "C", "K", "L", "r", "w"],
            output_type="pct_diff",
            num_years=num_years,
            start_year=start_year,
        )
    except FileNotFoundError as exc:
        print(f"  [WARNING] {exc}")
        return None


# ===========================================================================
# DIMENSION 1 — Demographic Foundation
# ===========================================================================

def d2_accelerated_fertility(p):
    """
    D2: Fertility rate reaches 2.5 by 2035 rather than 2045.
    Modelled as a 30% faster decline in population growth over 2025-2035,
    converging to a lower long-run steady state growth rate (−25%).
    """
    g_n = np.array(p.g_n, dtype=float)
    # Accelerate the first 10 periods (2025-2034) and converge to lower SS
    g_n[:10] *= np.linspace(1.0, 0.75, 10)   # phase down
    g_n[10:] *= 0.75                           # maintain lower path
    g_n_ss = float(p.g_n_ss) * 0.75
    return {"g_n": g_n.tolist(), "g_n_ss": g_n_ss}


def d3_youth_mortality_shock(p):
    """
    D3: Conflict or health crisis raises youth mortality by 15%.
    Affects model age periods 0-15 (ages 20-35) for the first 20 periods.
    Implemented via direct override of p.rho after update_specifications.
    """
    rho = np.array(p.rho, dtype=float)   # shape (T, S) after loading
    # Boost youth mortality for first 20 time periods
    rho[:20, :15] *= 1.15
    # Cap at maximum realistic mortality rate
    rho = np.clip(rho, 0.0, 0.999)
    return {}, {"rho": rho}   # no paramtools update; direct override only


def d4_high_fertility(p):
    """
    D4: High-fertility UN variant — population exceeds 200M by 2050.
    Modelled as a 30% higher population growth rate path through 2035,
    with slower subsequent decline.
    """
    g_n = np.array(p.g_n, dtype=float)
    g_n[:26] *= 1.30
    g_n[26:] *= 1.15
    g_n_ss = float(p.g_n_ss) * 1.20
    return {"g_n": g_n.tolist(), "g_n_ss": g_n_ss}


# ===========================================================================
# DIMENSION 2 — Education and Human Capital
# ===========================================================================

def e2_tvet_moderate(p):
    """E2: Efficiency units of young workers +10% by 2035."""
    factor = _age_ramp(p.S, p.starting_age, 35, 55, 0.10)
    return {"e": _apply_age_boost(_e0(p), factor).tolist()}


def e3_university_strong(p):
    """E3: Efficiency units +20% by 2035."""
    factor = _age_ramp(p.S, p.starting_age, 35, 55, 0.20)
    return {"e": _apply_age_boost(_e0(p), factor).tolist()}


def e4_combined_max(p):
    """E4: Combined TVET + university reform +25% by 2035."""
    factor = _age_ramp(p.S, p.starting_age, 35, 55, 0.25)
    return {"e": _apply_age_boost(_e0(p), factor).tolist()}


# ===========================================================================
# DIMENSION 3 — Labour Market and Formalisation
# ===========================================================================
# Productivity premium: formal workers earn ≈2.5× informal (ILO 2023 ETH)
# Baseline formal share: 13%. See module docstring for derivation.

def l2_moderate_formalisation(p):
    """L2: Formal employment share 13% → 25% by 2035. e +15.1%."""
    factor = _working_age_ramp(p.S, p.starting_age, magnitude=0.151)
    return {
        "e": _apply_age_boost(_e0(p), factor).tolist(),
        "frisch": float(p.frisch) + 0.05,
    }


def l3_strong_formalisation(p):
    """L3: Formal share 13% → 40% by 2035. e +33.9%."""
    factor = _working_age_ramp(p.S, p.starting_age, magnitude=0.339)
    return {
        "e": _apply_age_boost(_e0(p), factor).tolist(),
        "frisch": float(p.frisch) + 0.10,
    }


def l4_full_formalisation(p):
    """L4: Formal share 13% → 55% (middle-income avg). e +52.7%."""
    factor = _working_age_ramp(p.S, p.starting_age, magnitude=0.527)
    return {
        "e": _apply_age_boost(_e0(p), factor).tolist(),
        "frisch": float(p.frisch) + 0.15,
    }


# ===========================================================================
# DIMENSION 4 — Gender Inclusion
# ===========================================================================

def g2_partial_flfp(p):
    """G2: Female LFP halfway toward male levels by 2040. e +15%."""
    e_new = _e0(p) * 1.15
    return {"e": e_new.tolist()}


def g3_full_flfp_2040(p):
    """G3: Full female LFP convergence by 2040. e +30%."""
    e_new = _e0(p) * 1.30
    return {"e": e_new.tolist()}


def g4_full_flfp_2030(p):
    """
    G4: Full convergence by 2030 (10 years earlier than G3).
    Same long-run magnitude (+30%); timing advantage captured via direct
    override of the first 5 periods (2025-2029) at the full target value,
    whereas G3 would still be phasing in. In practice, since number_dims=2
    for e (no native time-variation), we set e to the full +30% target and
    note that the earlier realisation is the primary distinction.
    """
    e_new = _e0(p) * 1.30
    return {"e": e_new.tolist()}


# ===========================================================================
# DIMENSION 5 — Migration and Brain Drain
# ===========================================================================
# Brain drain modelled by reducing e for top-2 ability groups (J=5,6 in
# 0-index) among working-age workers — representing high-skill emigrants.
# Brain gain (M4) raises top-skill e and increases zeta_K (diaspora capital).

def _top_skill_factor(p, magnitude):
    """
    (S, J) factor array: `magnitude` for top-2 ability groups,
    working-age only.
    """
    factor = np.zeros((p.S, p.J))
    w_factor = _working_age_ramp(p.S, p.starting_age)  # 1.0 for working-age
    factor[:, -2:] = w_factor[:, np.newaxis]
    return factor * magnitude


def m2_moderate_brain_drain(p):
    """M2: Graduate emigration doubles by 2030. Top-skill e −20%."""
    factor = _top_skill_factor(p, -0.20)
    e_new = _e0(p) * (1.0 + factor)
    return {"e": e_new.tolist()}


def m3_severe_brain_drain(p):
    """M3: 20% of graduates leave per decade from 2030. Top-skill e −35%."""
    factor = _top_skill_factor(p, -0.35)
    e_new = _e0(p) * (1.0 + factor)
    return {"e": e_new.tolist()}


def m4_brain_gain(p):
    """
    M4: Net skilled diaspora return. Top-skill e +25%, zeta_K +0.10
    (diaspora remittances and investment raise domestic capital).
    """
    factor = _top_skill_factor(p, +0.25)
    e_new = _e0(p) * (1.0 + factor)
    current_zeta_K = float(np.array(p.zeta_K).flatten()[0])
    return {
        "e": e_new.tolist(),
        "zeta_K": [min(current_zeta_K + 0.10, 0.99)],
    }


# ===========================================================================
# DIMENSION 6 — Fiscal Policy and Youth Investment
# ===========================================================================

def f2_education_surge(p):
    """F2: Government education spending +2% of GDP. alpha_G += 0.02."""
    current_alpha_G = float(np.array(p.alpha_G).flatten()[0])
    return {"alpha_G": [current_alpha_G + 0.020]}


def f3_employment_subsidy(p):
    """
    F3: Wage subsidy for formal youth hiring.
    Modelled as e +10% for ages 20-35 (subsidy lowers effective labour
    cost → employers hire more → workers become more productive in formal
    roles) plus frisch +0.10 (reduced entry barriers raise labour supply
    elasticity).
    """
    factor = _age_ramp(p.S, p.starting_age, 30, 45, 0.10)
    return {
        "e": _apply_age_boost(_e0(p), factor).tolist(),
        "frisch": float(p.frisch) + 0.10,
    }


def f4_gender_investment(p):
    """
    F4: Targeted fiscal transfers to raise female participation.
    Two channels: (1) alpha_T +0.01 (transfer payments enabling
    participation) and (2) e uniform +10% (quality gains from supported
    female employment).
    """
    current_alpha_T = float(np.array(p.alpha_T).flatten()[0])
    e_new = _e0(p) * 1.10
    return {
        "alpha_T": [current_alpha_T + 0.010],
        "e": e_new.tolist(),
    }


def f5_imf_constraint(p):
    """F5: IMF fiscal consolidation — youth spending −1.5% of GDP."""
    current_alpha_G = float(np.array(p.alpha_G).flatten()[0])
    return {"alpha_G": [max(current_alpha_G - 0.015, 0.01)]}


# ===========================================================================
# DIMENSION 7 — Integrated Policy Package
# ===========================================================================

def _combine_e_shocks(p, *e_arrays):
    """
    Multiplicatively compose multiple (S, J) e arrays relative to baseline.
    Each e_array is the RESULT of a shock function (already boosted from e0).
    We compose as: e_combined = e0 × ∏(e_i / e0).
    """
    e0 = _e0(p)
    combined_factor = np.ones_like(e0)
    for e_i in e_arrays:
        e_arr = np.array(e_i, dtype=float)
        if e_arr.ndim == 3:
            e_arr = e_arr[0]
        combined_factor *= (e_arr / e0)
    return (e0 * combined_factor).tolist()


def i1_moderate(p):
    """I1: E2 + L2 + G2 + F2 (moderate integrated package)."""
    # Collect constituent e arrays
    e_e2 = np.array(e2_tvet_moderate(p)["e"])
    e_l2 = np.array(l2_moderate_formalisation(p)["e"])
    e_g2 = np.array(g2_partial_flfp(p)["e"])

    current_alpha_G = float(np.array(p.alpha_G).flatten()[0])
    return {
        "e": _combine_e_shocks(p, e_e2, e_l2, e_g2),
        "frisch": float(p.frisch) + 0.05,
        "alpha_G": [current_alpha_G + 0.020],
    }


def i2_ambitious(p):
    """I2: E3 + L3 + G3 + F2 (ambitious integrated package)."""
    e_e3 = np.array(e3_university_strong(p)["e"])
    e_l3 = np.array(l3_strong_formalisation(p)["e"])
    e_g3 = np.array(g3_full_flfp_2040(p)["e"])

    current_alpha_G = float(np.array(p.alpha_G).flatten()[0])
    return {
        "e": _combine_e_shocks(p, e_e3, e_l3, e_g3),
        "frisch": float(p.frisch) + 0.10,
        "alpha_G": [current_alpha_G + 0.020],
    }


def i3_maximum(p):
    """I3: E4 + L4 + G4 + M4 (maximum dividend)."""
    e_e4 = np.array(e4_combined_max(p)["e"])
    e_l4 = np.array(l4_full_formalisation(p)["e"])
    e_g4 = np.array(g4_full_flfp_2030(p)["e"])
    e_m4 = np.array(m4_brain_gain(p)["e"])

    current_zeta_K = float(np.array(p.zeta_K).flatten()[0])
    return {
        "e": _combine_e_shocks(p, e_e4, e_l4, e_g4, e_m4),
        "frisch": float(p.frisch) + 0.15,
        "zeta_K": [min(current_zeta_K + 0.10, 0.99)],
    }


def i4_delayed_action(p, p_base):
    """
    I4: Same as I2 but reforms begin 2035 (t=10), not 2025.
    Implemented by:
      1. Applying I2 parameters via update_specifications
      2. Directly overriding p.e for periods t=0..9 with baseline e,
         creating a 10-year implementation delay.
    This is the 'Cost of Delay' scenario.
    """
    params = i2_ambitious(p)
    # Build the time-varying e: baseline for t<10, I2 for t>=10
    e_i2 = np.array(params["e"], dtype=float)    # (S, J) from i2_ambitious
    e_base_arr = np.array(p_base.e, dtype=float)  # (T, S, J)
    T = e_base_arr.shape[0]

    e_delayed = np.zeros_like(e_base_arr)
    for t in range(T):
        if t < 10:
            e_delayed[t] = e_base_arr[t]   # no reform yet (2025-2034)
        else:
            e_delayed[t] = e_i2             # reforms kick in (2035+)

    return params, {"e": e_delayed}


# ===========================================================================
# Main
# ===========================================================================

def main():
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    print(f"Workers: {num_workers}")

    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    OUT = os.path.join(CUR_DIR, "OG-ETH-YouthDividend-Full")
    os.makedirs(OUT, exist_ok=True)

    # -----------------------------------------------------------------------
    # D1 — Common Baseline
    # -----------------------------------------------------------------------
    d1_dir = os.path.join(OUT, "D1_BASELINE")
    if already_done(d1_dir):
        print("D1 baseline: already complete — loading")
        p_base = build_baseline(d1_dir, num_workers)
    else:
        print("=== D1: Common Baseline ===")
        p_base = build_baseline(d1_dir, num_workers)
        safe_run(p_base, client, "D1")

    # -----------------------------------------------------------------------
    # Build scenario registry: (label, dir, param_updates, direct_overrides)
    # -----------------------------------------------------------------------
    def sd(name):
        return os.path.join(OUT, name)

    # Dimension 1 — Demographics
    d2_params = d2_accelerated_fertility(p_base)
    d3_params, d3_overrides = d3_youth_mortality_shock(p_base)
    d4_params = d4_high_fertility(p_base)

    # Dimension 2 — Education
    e2_params = e2_tvet_moderate(p_base)
    e3_params = e3_university_strong(p_base)
    e4_params = e4_combined_max(p_base)

    # Dimension 3 — Labour
    l2_params = l2_moderate_formalisation(p_base)
    l3_params = l3_strong_formalisation(p_base)
    l4_params = l4_full_formalisation(p_base)

    # Dimension 4 — Gender
    g2_params = g2_partial_flfp(p_base)
    g3_params = g3_full_flfp_2040(p_base)
    g4_params = g4_full_flfp_2030(p_base)

    # Dimension 5 — Migration
    m2_params = m2_moderate_brain_drain(p_base)
    m3_params = m3_severe_brain_drain(p_base)
    m4_params = m4_brain_gain(p_base)

    # Dimension 6 — Fiscal
    f2_params = f2_education_surge(p_base)
    f3_params = f3_employment_subsidy(p_base)
    f4_params = f4_gender_investment(p_base)
    f5_params = f5_imf_constraint(p_base)

    # Dimension 7 — Integrated
    i1_params = i1_moderate(p_base)
    i2_params = i2_ambitious(p_base)
    i3_params = i3_maximum(p_base)
    i4_params, i4_overrides = i4_delayed_action(p_base, p_base)

    scenarios = [
        # label            dir               param_updates  direct_overrides
        ("D2_Fertility_Decline", sd("D2"), d2_params, None),
        ("D3_Mortality_Shock",   sd("D3"), d3_params, d3_overrides),
        ("D4_High_Fertility",    sd("D4"), d4_params, None),
        ("E2_TVET_Moderate",     sd("E2"), e2_params, None),
        ("E3_University_Strong", sd("E3"), e3_params, None),
        ("E4_Combined_Max",      sd("E4"), e4_params, None),
        ("L2_Formalisation_25", sd("L2"), l2_params, None),
        ("L3_Formalisation_40", sd("L3"), l3_params, None),
        ("L4_Formalisation_55", sd("L4"), l4_params, None),
        ("G2_FLFP_Partial",     sd("G2"), g2_params, None),
        ("G3_FLFP_Full_2040",   sd("G3"), g3_params, None),
        ("G4_FLFP_Full_2030",   sd("G4"), g4_params, None),
        ("M2_Brain_Drain_Mod",  sd("M2"), m2_params, None),
        ("M3_Brain_Drain_Sev",  sd("M3"), m3_params, None),
        ("M4_Brain_Gain",       sd("M4"), m4_params, None),
        ("F2_Edu_Surge",        sd("F2"), f2_params, None),
        ("F3_Employ_Subsidy",   sd("F3"), f3_params, None),
        ("F4_Gender_Investment",sd("F4"), f4_params, None),
        ("F5_IMF_Constraint",   sd("F5"), f5_params, None),
        ("I1_Moderate",         sd("I1"), i1_params, None),
        ("I2_Ambitious",        sd("I2"), i2_params, None),
        ("I3_Maximum",          sd("I3"), i3_params, None),
        ("I4_Delayed_Action",   sd("I4"), i4_params, i4_overrides),
    ]

    # -----------------------------------------------------------------------
    # Run all scenarios
    # -----------------------------------------------------------------------
    print(f"\n=== Running {len(scenarios)} reform scenarios ===")
    for label, sdir, params, overrides in scenarios:
        print(f"\n--- {label} ---")
        os.makedirs(sdir, exist_ok=True)
        p_s = run_scenario(p_base, sdir, params, overrides)
        safe_run(p_s, client, label)

    client.close()

    # -----------------------------------------------------------------------
    # Results: % change vs D1 baseline
    # -----------------------------------------------------------------------
    start_year = p_base.start_year
    num_years = 2050 - start_year + 1  # 26 years

    plot_dir = os.path.join(OUT, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    print("\n" + "=" * 72)
    print("RESULTS: % change relative to D1 baseline")
    print("=" * 72)

    all_results = {}
    for label, sdir, _, _ in scenarios:
        tbl = pct_table(d1_dir, sdir, num_years, start_year)
        if tbl is not None:
            all_results[label] = tbl
            csv_path = os.path.join(OUT, f"{label}_vs_D1.csv")
            tbl.to_csv(csv_path)
            print(f"\n{label}:")
            print(tbl[["Y", "C", "K", "L", "r", "w"]].iloc[:, :6].to_string()
                  if hasattr(tbl, "columns") else tbl.to_string())
        # Plots
        try:
            op.plot_all(d1_dir, sdir, os.path.join(plot_dir, label))
        except Exception as exc:
            print(f"  [plot warning] {label}: {exc}")

    # -----------------------------------------------------------------------
    # Cost of Delay: I2 vs I4
    # -----------------------------------------------------------------------
    i2_dir = sd("I2")
    i4_dir = sd("I4")
    if already_done(i2_dir) and already_done(i4_dir):
        cod = pct_table(i2_dir, i4_dir, num_years, start_year)
        if cod is not None:
            cod_path = os.path.join(OUT, "COST_OF_DELAY_I4_vs_I2.csv")
            cod.to_csv(cod_path)
            print("\n=== COST OF DELAY (I4 vs I2: reforms delayed 10 years) ===")
            print(cod.to_string())

    print(f"\nAll outputs saved to: {OUT}")


if __name__ == "__main__":
    main()

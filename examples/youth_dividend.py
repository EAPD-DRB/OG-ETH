"""
Ethiopia Youth Dividend Analysis — OG-ETH/OG-Core Implementation
=================================================================
Concept note: "Harnessing Ethiopia's Youth Dividend"

Runs six scenarios against a frozen-demographics counterfactual and a
live policy baseline, then saves CSV tables and plots.

Scenario definitions (matching concept note exactly)
----------------------------------------------------
FROZEN_BASE  Counterfactual: constant_demographics=True. No population
             transition. Used only to isolate the pure demographic dividend.

BASE         Standard OG-ETH baseline: actual UN WPP demographic trajectory
             + current fiscal/labor/education policy. This IS Scenario S1
             (demographic dividend alone) relative to FROZEN_BASE.

S2           BASE + education investment: raises age-efficiency units (e)
             for young workers (ages 20-50), tapering to zero by age 55.
             Concept note reference: "raising the age-efficiency units of
             young workers in the model's labour supply calibration".

S3           BASE + labour market reform: increases Frisch elasticity (more
             responsive labour supply) + moderate e boost for working-age
             adults to model formal-sector expansion.
             Concept note reference: "Scenario S3 models labour market
             reforms that expand youth formal sector employment."

S4           BASE + gender inclusion: uniform scale-up of e to represent
             female FLFP converging toward male levels (Ethiopian female
             FLFP ~39% → ~77%). The 30 % boost corresponds to the aggregate
             labour supply gain from closing that gap for ~50 % of the
             workforce.
             Concept note reference: "raising female labour force
             participation parameters toward male levels."

S5           BASE + all three reforms simultaneously (S2 + S3 + S4).
             Concept note reference: "maximum achievable youth dividend."

Key dependent variables read from model output
----------------------------------------------
  Y  — aggregate output / GDP proxy
  C  — aggregate consumption
  K  — aggregate private capital stock
  L  — aggregate labour
  r  — interest rate (return to capital)
  w  — real wage

Key independent (calibration) parameters modified per scenario
--------------------------------------------------------------
  e             (S × J) age-efficiency units — S2, S4, S5
  frisch        Frisch elasticity of labour supply — S3, S5
  constant_demographics  bool — FROZEN_BASE only
"""

import multiprocessing
import os
import json
import time
import copy
from importlib.resources import files

import numpy as np
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

# =========================================================================
# Parameter shock helpers
# =========================================================================


def _modify_e(e_orig, age_factor):
    """
    Apply a 1-D age-varying multiplier (shape S) to an e matrix.

    OG-Core stores e internally as (T, S, J) after update_specifications,
    but update_specifications only accepts (S, J).  This function always
    returns a 2-D (S, J) array so the result can be fed directly back into
    update_specifications.

    Args:
        e_orig (np.ndarray): original age-efficiency matrix, (S, J) or (T, S, J)
        age_factor (np.ndarray): shape (S,), multiplicative factor per age

    Returns:
        np.ndarray: modified (S, J) array ready for update_specifications
    """
    e = np.array(e_orig, dtype=float)
    if e.ndim == 3:   # (T, S, J) — take baseline period only
        e = e[0]      # → (S, J)
    if e.ndim != 2:
        raise ValueError(f"Unexpected e shape after normalisation: {e.shape}")
    e *= (1.0 + age_factor)[:, np.newaxis]
    return e


def _age_boost(S, starting_age, peak_age, taper_age, magnitude):
    """
    Create a (S,) age-varying boost vector.
    Full `magnitude` from `starting_age` to `peak_age`, then linear taper
    to 0 at `taper_age`, then 0 thereafter.
    """
    ages = np.linspace(starting_age, starting_age + S, S, endpoint=False)
    factor = np.zeros(S)
    for i, age in enumerate(ages):
        if age <= peak_age:
            factor[i] = magnitude
        elif age < taper_age:
            factor[i] = magnitude * (taper_age - age) / (taper_age - peak_age)
    return factor


def education_shock(p, boost=0.20, peak_age=30, taper_age=55):
    """
    Scenario S2 — Education & Human Capital Investment.

    Raises age-efficiency units for young workers by `boost` at peak,
    tapering to zero by `taper_age`. This feeds through to higher
    equilibrium wages and greater capital accumulation.

    Concept note: "raising the age-efficiency units of young workers in
    the model's labor supply calibration."

    Args:
        p (Specifications): model parameters (used for S, starting_age)
        boost (float): fractional productivity increase at peak (default 0.20)
        peak_age (int): age at which boost peaks (default 30)
        taper_age (int): age at which boost reaches 0 (default 55)

    Returns:
        dict: {"e": modified_e_list}
    """
    factor = _age_boost(p.S, p.starting_age, peak_age, taper_age, boost)
    e_new = _modify_e(np.array(p.e), factor)
    return {"e": e_new.tolist()}


def labor_market_shock(p, frisch_increase=0.15, formal_boost=0.08,
                       work_start=20, work_peak=50, work_taper=65):
    """
    Scenario S3 — Labour Market Reform.

    Two channels:
      1. Higher Frisch elasticity: workers respond more strongly to wages,
         modelling reduced labour market frictions and formal-sector expansion.
      2. Modest e boost for all working-age adults: models quality/hours
         gains from formalisation (stable wages, benefits, longer hours).

    Concept note: "Scenario S3 models labour market reforms that expand
    youth formal sector employment."

    Args:
        p (Specifications): model parameters
        frisch_increase (float): addition to existing Frisch elasticity
        formal_boost (float): fractional e increase for working-age adults
        work_start, work_peak, work_taper (int): age profile of boost

    Returns:
        dict: {"frisch": new_frisch, "e": modified_e_list}
    """
    new_frisch = float(p.frisch) + frisch_increase
    factor = _age_boost(
        p.S, p.starting_age, work_peak, work_taper, formal_boost
    )
    # Apply full boost across the core working years
    ages = np.linspace(p.starting_age, p.starting_age + p.S, p.S, endpoint=False)
    for i, age in enumerate(ages):
        if age < work_start:
            factor[i] = 0.0
    e_new = _modify_e(np.array(p.e), factor)
    return {"frisch": new_frisch, "e": e_new.tolist()}


def gender_shock(p, flfp_boost=0.30):
    """
    Scenario S4 — Gender Inclusion.

    Approximates raising female FLFP toward male levels by scaling all
    age-efficiency units upward. Derivation:

      Ethiopian female FLFP ≈ 39 %, male ≈ 77 %
      Assuming 50/50 gender split, current aggregate labour efficiency
        per worker = 0.5 × 77 % + 0.5 × 39 % = 58 % of full-participation.
      Full FLFP convergence raises this to 0.5 × 77 % + 0.5 × 77 % = 77 %.
      Fractional gain = (77 - 58) / 58 ≈ 33 %, rounded to 30 % net of
        implementation frictions.

    OG-Core does not separate gender explicitly; the aggregate e scale-up
    is the standard approximation used in OG-Core country calibrations.

    Concept note: "raising female labour force participation parameters
    toward male levels."

    Args:
        p (Specifications): model parameters
        flfp_boost (float): uniform fractional increase in e (default 0.30)

    Returns:
        dict: {"e": modified_e_list}
    """
    e = np.array(p.e, dtype=float)
    if e.ndim == 3:
        e = e[0]  # (T, S, J) → (S, J) for update_specifications
    e_new = e * (1.0 + flfp_boost)
    return {"e": e_new.tolist()}


def integrated_shock(p, edu_boost=0.20, edu_peak=30, edu_taper=55,
                     frisch_increase=0.15, formal_boost=0.08,
                     flfp_boost=0.30):
    """
    Scenario S5 — Integrated Policy Package.

    Applies S2 + S3 + S4 simultaneously. The e modifications are composed
    multiplicatively (not additive) to avoid double-counting.

    Concept note: "Scenario S5 combines all of these reforms into an
    integrated policy package that represents the maximum achievable youth
    dividend."

    Returns:
        dict: {"frisch": ..., "e": modified_e_list}
    """
    S, starting_age = p.S, p.starting_age
    ages = np.linspace(starting_age, starting_age + S, S, endpoint=False)

    # Education factor (S2)
    edu_factor = _age_boost(S, starting_age, edu_peak, edu_taper, edu_boost)

    # Labour market factor (S3)
    work_factor = _age_boost(S, starting_age, 50, 65, formal_boost)
    for i, age in enumerate(ages):
        if age < 20:
            work_factor[i] = 0.0

    # Gender factor (S4): uniform
    gender_factor = flfp_boost * np.ones(S)

    # Combined multiplicative boost
    combined = (1.0 + edu_factor) * (1.0 + work_factor) * (1.0 + gender_factor)
    e_orig = np.array(p.e, dtype=float)
    if e_orig.ndim == 3:
        e_orig = e_orig[0]  # (T, S, J) → (S, J) for update_specifications
    e_new = e_orig * combined[:, np.newaxis]

    new_frisch = float(p.frisch) + frisch_increase
    return {"frisch": new_frisch, "e": e_new.tolist()}


# =========================================================================
# Baseline builder
# =========================================================================


def build_baseline(baseline_dir, num_workers, constant_demographics=False):
    """
    Construct and run a full baseline Specifications object.

    Args:
        baseline_dir (str): directory for baseline output
        num_workers (int): number of parallel workers
        constant_demographics (bool): if True, freeze demographics at
            initial steady state (used for FROZEN_BASE counterfactual)

    Returns:
        Specifications: calibrated, run-ready parameter object
    """
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

    if constant_demographics:
        p.update_specifications({"constant_demographics": True})

    return p


def run_reform(p_base, reform_dir, param_updates, fresh_solve=False):
    """
    Create a reform Specifications object derived from a baseline run.

    Args:
        p_base (Specifications): calibrated baseline parameters
        reform_dir (str): directory for reform output
        param_updates (dict): parameters to change for this scenario
        fresh_solve (bool): if True, do not warm-start from baseline solution

    Returns:
        Specifications: reform parameter object (not yet run)
    """
    p = copy.deepcopy(p_base)
    p.baseline = False
    p.output_base = reform_dir
    p.update_specifications(param_updates)
    if fresh_solve:
        p.reform_use_baseline_solution = False
    return p


# =========================================================================
# Results helper
# =========================================================================


def macro_pct_table(base_dir, reform_dir, num_years, start_year):
    """
    Load saved TPI outputs and return an ot.macro_table % change DataFrame.
    Returns None if either output is missing.
    """
    try:
        base_tpi = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
        base_params = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
        ref_tpi = safe_read_pickle(
            os.path.join(reform_dir, "TPI", "TPI_vars.pkl")
        )
        ref_params = safe_read_pickle(
            os.path.join(reform_dir, "model_params.pkl")
        )
        return ot.macro_table(
            base_tpi,
            base_params,
            reform_tpi=ref_tpi,
            reform_params=ref_params,
            var_list=["Y", "C", "K", "L", "r", "w"],
            output_type="pct_diff",
            num_years=num_years,
            start_year=start_year,
        )
    except FileNotFoundError as exc:
        print(f"  [WARNING] Output file missing — {exc}")
        return None


# =========================================================================
# Main
# =========================================================================


def main():
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    print(f"Workers: {num_workers}")

    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(CUR_DIR, "OG-ETH-YouthDividend")
    os.makedirs(save_dir, exist_ok=True)

    frozen_dir = os.path.join(save_dir, "FROZEN_BASE")
    base_dir = os.path.join(save_dir, "BASE")
    s2_dir = os.path.join(save_dir, "S2_EDUCATION")
    s3_dir = os.path.join(save_dir, "S3_LABOR_MARKET")
    s4_dir = os.path.join(save_dir, "S4_GENDER")
    s5_dir = os.path.join(save_dir, "S5_INTEGRATED")

    # ------------------------------------------------------------------ #
    # FROZEN_BASE — demographic counterfactual (constant_demographics=True)
    # Skip if already completed.
    # ------------------------------------------------------------------ #
    frozen_done = os.path.exists(
        os.path.join(frozen_dir, "TPI", "TPI_vars.pkl")
    )
    if frozen_done:
        print("\n=== FROZEN_BASE: already complete, loading ===")
        p_frozen = build_baseline(
            frozen_dir, num_workers, constant_demographics=True
        )
    else:
        print("\n=== FROZEN_BASE: Demographic counterfactual ===")
        p_frozen = build_baseline(
            frozen_dir, num_workers, constant_demographics=True
        )
        t0 = time.time()
        runner(p_frozen, time_path=True, client=client)
        print(f"  FROZEN_BASE runtime: {time.time() - t0:.0f}s")

    # ------------------------------------------------------------------ #
    # BASE — standard OG-ETH run (actual demographic transition, current
    # policy).  This IS Scenario S1 relative to FROZEN_BASE.
    # Skip if already completed.
    # ------------------------------------------------------------------ #
    base_done = os.path.exists(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
    if base_done:
        print("\n=== BASE: already complete, loading ===")
        p_base = build_baseline(base_dir, num_workers, constant_demographics=False)
    else:
        print("\n=== BASE (= S1: Demographic Dividend alone) ===")
        p_base = build_baseline(base_dir, num_workers, constant_demographics=False)
        t0 = time.time()
        runner(p_base, time_path=True, client=client)
        print(f"  BASE runtime: {time.time() - t0:.0f}s")

    # ------------------------------------------------------------------ #
    # S2 — Education & Human Capital Investment
    # ------------------------------------------------------------------ #
    print("\n=== S2: Education Investment ===")
    p2 = run_reform(p_base, s2_dir, education_shock(p_base))
    t0 = time.time()
    runner(p2, time_path=True, client=client)
    print(f"  S2 runtime: {time.time() - t0:.0f}s")

    # ------------------------------------------------------------------ #
    # S3 — Labour Market Reform
    # ------------------------------------------------------------------ #
    print("\n=== S3: Labour Market Reform ===")
    p3 = run_reform(p_base, s3_dir, labor_market_shock(p_base))
    t0 = time.time()
    runner(p3, time_path=True, client=client)
    print(f"  S3 runtime: {time.time() - t0:.0f}s")

    # ------------------------------------------------------------------ #
    # S4 — Gender Inclusion
    # ------------------------------------------------------------------ #
    print("\n=== S4: Gender Inclusion ===")
    p4 = run_reform(p_base, s4_dir, gender_shock(p_base))
    t0 = time.time()
    runner(p4, time_path=True, client=client)
    print(f"  S4 runtime: {time.time() - t0:.0f}s")

    # ------------------------------------------------------------------ #
    # S5 — Integrated Policy Package
    # ------------------------------------------------------------------ #
    print("\n=== S5: Integrated Policy Package ===")
    p5 = run_reform(p_base, s5_dir, integrated_shock(p_base))
    t0 = time.time()
    runner(p5, time_path=True, client=client)
    print(f"  S5 runtime: {time.time() - t0:.0f}s")

    client.close()

    # ================================================================== #
    # Results
    # Project 2025-2050 = 25 years from start_year
    # ================================================================== #
    start_year = p_base.start_year
    num_years = 2050 - start_year + 1  # inclusive

    print("\n" + "=" * 70)
    print("RESULTS: % change relative to respective baseline")
    print("=" * 70)

    # ------------------------------------------------------------------
    # S1 (demographic dividend): BASE vs FROZEN_BASE
    # ------------------------------------------------------------------
    print("\n--- S1: Demographic Dividend (BASE vs FROZEN_BASE) ---")
    s1_table = macro_pct_table(frozen_dir, base_dir, num_years, start_year)
    if s1_table is not None:
        print(s1_table.to_string())
        s1_table.to_csv(os.path.join(save_dir, "S1_demographic_dividend.csv"))

    # ------------------------------------------------------------------
    # S2-S5: policy reform vs BASE
    # ------------------------------------------------------------------
    scenarios = {
        "S2_Education": s2_dir,
        "S3_Labor_Market": s3_dir,
        "S4_Gender_Inclusion": s4_dir,
        "S5_Integrated": s5_dir,
    }
    for name, reform_dir_path in scenarios.items():
        print(f"\n--- {name} vs BASE ---")
        tbl = macro_pct_table(base_dir, reform_dir_path, num_years, start_year)
        if tbl is not None:
            print(tbl.to_string())
            tbl.to_csv(os.path.join(save_dir, f"{name}_vs_BASE.csv"))

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------
    plot_dir = os.path.join(save_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    plot_pairs = [
        ("S1_Demographic_Dividend", frozen_dir, base_dir),
        ("S2_Education_vs_BASE", base_dir, s2_dir),
        ("S3_Labor_Market_vs_BASE", base_dir, s3_dir),
        ("S4_Gender_vs_BASE", base_dir, s4_dir),
        ("S5_Integrated_vs_BASE", base_dir, s5_dir),
    ]
    for label, bdir, rdir in plot_pairs:
        out = os.path.join(plot_dir, label)
        try:
            op.plot_all(bdir, rdir, out)
            print(f"Plots saved: {out}")
        except Exception as exc:
            print(f"[WARNING] plot_all failed for {label}: {exc}")

    print(f"\nAll outputs written to: {save_dir}")


if __name__ == "__main__":
    main()

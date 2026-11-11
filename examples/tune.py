"""
Calibration tuning script for OG-ETH.

Loads the packaged JSON plus an optional overrides file, solves the steady
state (and with --tpi the baseline transition) with the same worker pool and
warm start as examples/run_og_eth.py, and prints the calibration dashboard:
every moment against its data target in ogeth/targets.py. With --next it
also writes the overrides for the next iteration, moving each dial toward
its own target:

    dial                               moment (ogeth/targets.py)
    chi_n by age                       hours per person by age (LFMS 2021), SS
    beta_annual across groups          WID 2021 wealth shares, SS
    beta_annual level                  (I + I_g)/Y in FY2024/25
    zeta_K                             K_f/K in FY2024/25
    compliance scale                   PIT/Y in FY2024/25
    adjustment_factor_for_cit_receipts CIT/Y in FY2024/25
    tau_c                              consumption tax/Y in FY2024/25
    p_wealth                           land-use fees/Y in FY2024/25
    pension coverage scale             pension outlays/Y in FY2024/25
    payroll coverage scale             contributions/Y in FY2024/25

It sets dials and nothing more. Fold settled values into the packaged JSON
(and the scales into ogeth/macro_params.py), commit, re-install, and take
every reported number from run_og_eth.py.

    python examples/tune.py [overrides.json] [--label NAME] [--tpi]
                            [--next next.json] [--warm SS_vars.pkl]
"""

import argparse
import importlib.resources
import json
import multiprocessing
import os
import pickle
import time

import numpy as np
from distributed import Client
from ogcore.execute import runner
from ogcore.parameters import Specifications
from ogcore.utils import safe_read_pickle

from ogeth import income, labor
from ogeth import macro_params as mp
from ogeth.calibrate import BETA_BOUNDS, BETA_DAMPING, BETA_STEP
from ogeth.targets import SS_TARGETS, TRANSITION_TARGETS, ss_moments
from ogeth.targets import tpi_moments
from ogeth.warm_start import enable, solve_ss_from

# Damping of the dials tuned to first-year moments: revenue is close to
# proportional to its rate or scale, so those take the full step; the
# investment share responds to patience with an elasticity well above one,
# so the discount-factor level moves by a fraction of the gap, bounded.
LEVEL_DAMPING = 0.15
LEVEL_STEP = 1.02
DIAL_BOUNDS = (0.5, 2.0)


def _ratio(target, model, damping=1.0, bounds=DIAL_BOUNDS):
    if model <= 0 or not np.isfinite(model):
        return 1.0
    return float(np.clip((target / model) ** damping, *bounds))


def scales_from(p):
    """
    The compliance, pension and payroll scales the parameters carry.

    Args:
        p (Specifications): model parameters

    Returns:
        dict: compliance, pension and payroll scales
    """
    nc = np.asarray(p.labor_income_tax_noncompliance_rate)[0]
    shape = 1 - np.array(mp.NONCOMPLIANCE_START)
    j = int(np.argmax(shape))
    tau_p = np.asarray(p.tau_payroll)[0]
    return {
        "compliance": float((1 - nc[j]) / shape[j]),
        "pension": float(
            np.asarray(p.replacement_rate_adjust)[0, -1]
            / mp.PENSION_COVERAGE[-1]
        ),
        "payroll": float(
            tau_p[-1] / (mp.PAYROLL_STATUTORY_RATE * mp.PENSION_COVERAGE[-1])
        ),
    }


def next_overrides(p, ss, tm):
    """
    The dial values for the next iteration.

    Args:
        p (Specifications): parameters just solved
        ss (dict): solved steady state
        tm (dict): first-period transition moments (may be None)

    Returns:
        dict: overrides for the next tune.py run
    """
    out = {}
    # hours by age: chi_n's first-order step
    n_target = labor.labor_supply_target(p.E, p.S, p.ltilde)
    n_model = labor.average_labor_supply(np.asarray(ss["n"]), p.omega_SS)
    chi_n = np.asarray(p.chi_n, dtype=float)
    chi_n = chi_n[-1] if chi_n.ndim > 1 else chi_n
    out["chi_n"] = labor.chi_n_step(chi_n, n_model, n_target, p).tolist()
    # wealth shares across groups: damped step, floored groups tied to the
    # nearest fitted group
    lambdas = np.asarray(p.lambdas).flatten()
    target = income.wealth_share_targets(lambdas)
    fit = target > income.WEALTH_SHARE_FLOOR
    model = income.implied_wealth_shares(np.asarray(ss["b_s"]), p.omega_SS)
    beta = np.asarray(p.beta_annual, dtype=float).flatten()
    step = np.clip((target / model) ** BETA_DAMPING, 1 / BETA_STEP, BETA_STEP)
    beta = beta * np.where(fit, step, 1.0)
    fitted = np.flatnonzero(fit)
    for j in np.flatnonzero(~fit):
        beta[j] = beta[fitted[np.argmin(np.abs(fitted - j))]]
    sc = scales_from(p)
    if tm is not None:
        t = {k: v[0] for k, v in TRANSITION_TARGETS.items()}
        # level of patience: first-year investment share
        beta = beta * _ratio(
            t["(I+I_g)/Y"],
            tm["(I+I_g)/Y"],
            LEVEL_DAMPING,
            (1 / LEVEL_STEP, LEVEL_STEP),
        )
        out["zeta_K"] = [
            float(
                np.clip(
                    np.asarray(p.zeta_K).flatten()[0]
                    * _ratio(t["K_f/K"], tm["K_f/K"]),
                    0.01,
                    0.99,
                )
            )
        ]
        sc["compliance"] = min(
            1.0, sc["compliance"] * _ratio(t["PIT/Y"], tm["PIT/Y"])
        )
        sc["pension"] *= _ratio(t["pensions/Y"], tm["pensions/Y"])
        sc["payroll"] *= _ratio(t["payroll/Y"], tm["payroll/Y"])
        cit = np.asarray(p.adjustment_factor_for_cit_receipts).flatten()
        out["adjustment_factor_for_cit_receipts"] = (
            cit[: len(mp.PROGRAM_YEARS) + 1] * _ratio(t["CIT/Y"], tm["CIT/Y"])
        ).tolist()
        tau_c = np.asarray(p.tau_c)[: len(mp.PROGRAM_YEARS) + 1, 0]
        out["tau_c"] = [
            [float(x)]
            for x in tau_c * _ratio(t["cons tax/Y"], tm["cons tax/Y"])
        ]
        out["p_wealth"] = [
            float(
                np.asarray(p.p_wealth).flatten()[0]
                * _ratio(t["wealth tax/Y"], tm["wealth tax/Y"])
            )
        ]
    out["beta_annual"] = np.clip(beta, *BETA_BOUNDS).tolist()
    out.update(
        mp.compliance_paths(
            mp.DEFAULT_SCENARIO, sc["compliance"], sc["pension"]
        )
    )
    out.update(mp.payroll_tax_params(sc["payroll"]))
    out["_scales"] = sc
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("overrides", nargs="?", default=None)
    ap.add_argument("--label", default="tune")
    ap.add_argument("--warm", default=None)
    ap.add_argument("--tpi", action="store_true")
    ap.add_argument("--next", default=None)
    args = ap.parse_args()

    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)

    cur_dir = os.path.dirname(os.path.realpath(__file__))
    out = os.path.join(cur_dir, "OG-ETH-Tune", args.label)
    p = Specifications(
        baseline=True,
        num_workers=num_workers,
        baseline_dir=out,
        output_base=out,
    )
    with importlib.resources.open_text(
        "ogeth", "ogeth_default_parameters.json"
    ) as file:
        p.update_specifications(json.load(file))
    overrides = {}
    if args.overrides:
        with open(args.overrides) as f:
            overrides = json.load(f)
        overrides.pop("_scales", None)
        p.update_specifications(overrides)
    print(f"label {args.label}; overrides: {sorted(overrides)}", flush=True)

    t0 = time.time()
    if args.warm and not args.tpi:
        ss = solve_ss_from(p, safe_read_pickle(args.warm), client=client)
        os.makedirs(os.path.join(out, "SS"), exist_ok=True)
        with open(os.path.join(out, "SS", "SS_vars.pkl"), "wb") as f:
            pickle.dump(ss, f)
    else:
        enable()
        runner(p, time_path=args.tpi, client=client)
        ss = safe_read_pickle(os.path.join(out, "SS", "SS_vars.pkl"))
    secs = time.time() - t0
    client.close()

    tm = None
    if args.tpi:
        tpi = safe_read_pickle(os.path.join(out, "TPI", "TPI_vars.pkl"))
        tm = tpi_moments(tpi)
        print(f"\n{'FY2024/25 moment':20s} {'model':>8s} {'data':>8s}  dial")
        for k, (target, dial, _) in TRANSITION_TARGETS.items():
            print(f"{k:20s} {tm[k]:8.4f} {target:8.4f}  {dial}")
        for k in sorted(set(tm) - set(TRANSITION_TARGETS)):
            print(f"{k:20s} {tm[k]:8.4f}")

    model = ss_moments(ss)
    n_target = labor.labor_supply_target(p.E, p.S, p.ltilde)
    n_model = labor.average_labor_supply(np.asarray(ss["n"]), p.omega_SS)
    ages = income.model_ages(p.E, p.S)
    fit = (ages >= labor.FIT_AGES[0]) & (ages < labor.FIT_AGES[1])
    chi_n = np.asarray(p.chi_n, dtype=float)
    chi_n = chi_n[-1] if chi_n.ndim > 1 else chi_n
    free = fit & (chi_n < labor.MAX_CHI_N)
    hours_gap = float(np.max(np.abs(n_model[free] / n_target[free] - 1)))
    lambdas = np.asarray(p.lambdas).flatten()
    w_target = income.wealth_share_targets(lambdas)
    w_model = income.implied_wealth_shares(np.asarray(ss["b_s"]), p.omega_SS)
    w_fit = w_target > income.WEALTH_SHARE_FLOOR
    wealth_gap = float(np.max(np.abs(w_model[w_fit] / w_target[w_fit] - 1)))
    rc = float(np.max(np.abs(ss["resource_constraint_error"])))
    print(
        f"\nSS solved in {secs:.0f} s; max |RC error| {rc:.2e}; "
        f"hours gap {hours_gap:.3f}; wealth-share gap {wealth_gap:.3f}"
    )
    print("wealth shares model", np.round(w_model, 3))
    print("wealth shares data ", np.round(w_target, 3))
    for k, (target, dial) in SS_TARGETS.items():
        print(f"SS {k:16s} {model[k]:8.4f} {target:8.4f}  {dial}")
    for k in sorted(set(model) - set(SS_TARGETS)):
        print(f"SS {k:16s} {model[k]:8.4f}")
    summary = {
        "label": args.label,
        "seconds": secs,
        "rc": rc,
        "hours_gap": hours_gap,
        "wealth_gap": wealth_gap,
        "wealth_shares": w_model.tolist(),
        "ss": model,
        "transition": tm,
        "scales": scales_from(p),
        "overrides": overrides,
    }
    with open(os.path.join(out, "dashboard.json"), "w") as f:
        json.dump(summary, f, indent=2, default=float)
    if args.next:
        nxt = next_overrides(p, ss, tm)
        with open(args.next, "w") as f:
            json.dump(nxt, f, default=float)
        print(f"next overrides -> {args.next}; scales {nxt['_scales']}")


if __name__ == "__main__":
    main()

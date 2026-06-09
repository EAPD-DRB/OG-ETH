# =============================================================================
# Fiscal Consolidation, Capital Accumulation, and Intergenerational Welfare
# in Ethiopia: An Overlapping Generations Analysis Using OG-ETH
#
# Tariku Birhanu Diriba
# Head, Department of Economics, Dire Dawa University
# PhD Candidate, UNISA College of Agriculture and Environmental Sciences
# June 2026
#
# Implements the five-scenario design of the research proposal (Table 2):
#   B0  IMF baseline path        debt_ss 0.33->0.24   alpha_G gradual
#   B1  Accelerated              debt_ss 0.33->0.15   alpha_G -3pp
#   B2  Productive investment    debt_ss 0.33->0.42   alpha_I +2pp (K_g)
#   B3  Transfer-led adjustment  debt_ss 0.33->0.24   alpha_T -1.5pp
#   B4  Delayed consolidation    debt_ss 0.33->0.24   tG1 = 8 (5-yr delay)
#
# plus the cohort welfare decomposition (Section 5.5 / Objective 4):
# lifetime consumption-equivalent variation (CEV) by birth cohort and ability
# type, computed from OG-ETH's solved consumption paths and its CRRA utility.
#
# Reference: DeBacker, J., Evans, R.W. and Phillips, K.L. (2019). Integrating
#   microsimulation models of tax policy into a DGE macroeconomic model.
#   Public Finance Review, 47(2), 207-275.
#   PSL Models (2025). OG-Core. https://github.com/PSLmodels/OG-Core
# =============================================================================

# imports
import numpy as np
import pandas as pd
import multiprocessing
from distributed import Client
import os
import json
import time
import copy
import re
import traceback
from importlib.resources import files
import matplotlib.pyplot as plt
from ogeth.calibrate import Calibration
from ogcore.parameters import Specifications
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore import demographics as demog
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle
from ogeth.utils import is_connected
import dask

dask.config.set(scheduler="synchronous")

# This OG-Core build predates pandas 3.0, whose read_csv infers the new
# "str" dtype for text columns. Restore the pre-3.0 object dtype for
# inferred strings so the UN demographic-data parsing keeps working.
pd.set_option("future.infer_string", False)

# Use a custom matplotlib style file for plots
plt.style.use("ogcore.OGcorePlots")

# ---------------------------------------------------------------------------
# UN country code for Ethiopia
# ---------------------------------------------------------------------------
_DEMOG_COUNTRY = "231"  # UN WPP country code for Ethiopia

# Demographic keys that OG-Core derives together and must stay consistent.
_DEMOG_KEYS = (
    "omega",
    "omega_SS",
    "omega_S_preTP",
    "g_n",
    "g_n_ss",
    "imm_rates",
    "rho",
)

# Cache the baseline UN data fetch so re-runs don't hit the network twice.
_DEMOG_BASE_CACHE = {}

# ---------------------------------------------------------------------------
# OG-ETH BASELINE CALIBRATION - Ethiopia 2024/25 (proposal Table 1)
# All values sourced from:
#   MoF Ethiopia Public Sector Debt Portfolio Report 2024
#   IMF ECF-EFF 4th Review / Article IV 2025/26
#   UNDP Quarterly Economic Profile April 2025
#   National Bank of Ethiopia (NBE) monetary data
#   World Bank-IMF Joint DSA 2025
# ---------------------------------------------------------------------------
ETH_CALIBRATION = {
    # Debt / fiscal parameters
    "initial_debt_ratio": 0.329,  # Total debt/GDP, end-June 2024 (MoF)
    "debt_ratio_ss_baseline": 0.240,  # IMF ECF-EFF DSA target by 2030
    "alpha_G": 0.105,  # Govt consumption/GDP (IMF GFS)
    "alpha_T": 0.030,  # Transfers/GDP (MoF / UNDP 2025)
    "alpha_I_pub": 0.045,  # Public investment/GDP (MoF capex 2024)
    # Macroeconomic calibration
    "g_y_annual": 0.040,  # TFP growth rate (NBE / World Bank WDI)
    # Govt borrowing-rate scale (Table 1). NOTE: the source note cites an
    # 18% T-bill vs an estimated r~6%, a ratio nearer 3.0; r_gov_scale=1.33
    # therefore UNDERSTATES that gap. Kept at the Table 1 value; revisit if
    # the crowding-out result (headline #1) is to reflect the full 18% yield.
    "r_gov_premium": 1.33,  # -> r_gov_scale
    # Consolidation timeline (ECF-EFF program)
    "tG1": 3,  # Consolidation start period (2027)
    "tG2": 20,  # Steady-state reached (OG-ETH convention)
    # Descriptive only (not model parameters)
    "invest_gdp": 0.205,  # Total investment/GDP (UNDP April 2025)
    "tbill_yield": 0.180,  # Weighted avg T-bill yield June 2025 (NBE)
    "gdp_growth_2024": 0.073,  # Real GDP growth 2024 (NBE)
}


def _sanitize_un_token(path="un_api_token.txt"):
    """Ensure un_api_token.txt holds only the bare UN API token.

    Creates an empty file if none exists so OG-Core uses the EAPD-DRB GitHub
    fallback rather than blocking on a stdin prompt for a token.
    """
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("")
        print(f"No {path}; created empty token file (GitHub fallback).")
        return
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    token = raw.strip()
    if token and "\n" not in token and " " not in token:
        return  # already a bare token
    match = re.search(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", raw)
    cleaned = match.group(0) if match else ""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(cleaned)
    if cleaned:
        print(f"Sanitized {path} to the bare UN API token.")
    else:
        print(f"No token in {path}; blanked it to use the GitHub fallback.")


def _baseline_rate_matrices(p, country_id):
    """Fetch and cache the baseline fertility/mortality rate matrices.

    Uses the same data-year window as OG-ETH's calibration
    (initial_data_year = start_year-1, final_data_year = start_year+1).
    Cached so all demographic variants share a single network fetch.
    """
    idy, fdy = int(p.start_year - 1), int(p.start_year + 1)
    totpers = int(p.E + p.S)
    key = (country_id, idy, fdy, totpers)
    if key not in _DEMOG_BASE_CACHE:
        fert = demog.get_fert(totpers, 0, 99, country_id, idy, fdy)
        mort, infmort = demog.get_mort(totpers, 0, 99, country_id, idy, fdy)
        _DEMOG_BASE_CACHE[key] = (fert, mort, infmort)
    return _DEMOG_BASE_CACHE[key]


def _recompute_demographics(p, country_id=_DEMOG_COUNTRY):
    """Recompute OG-Core's full, mutually-consistent demographic object set.

    Uses Ethiopia's UN WPP data.  Calling with no shocks reproduces the
    packaged baseline exactly, providing a consistent demographic foundation
    for all fiscal consolidation scenarios (which do not alter demographics).

    Returns the dict from demog.get_pop_objs.
    """
    idy, fdy = int(p.start_year - 1), int(p.start_year + 1)
    fert, mort, infmort = _baseline_rate_matrices(p, country_id)
    return demog.get_pop_objs(
        p.E,
        p.S,
        p.T,
        0,
        99,
        fert_rates=fert.copy(),
        mort_rates=mort.copy(),
        infmort_rates=infmort.copy(),
        country_id=country_id,
        initial_data_year=idy,
        final_data_year=fdy,
        GraphDiag=False,
    )


def load_outputs(output_dir):
    """Return (tpi, params) for a solved scenario, or (None, None).

    Returns (None, None) if any of the SS, TPI, or model-params pickles is
    missing OR fails to unpickle (e.g. a half-written file left by a killed
    run). Callers treat (None, None) as 'not done' and re-solve.
    """
    ss = os.path.join(output_dir, "SS", "SS_vars.pkl")
    tpi_path = os.path.join(output_dir, "TPI", "TPI_vars.pkl")
    par = os.path.join(output_dir, "model_params.pkl")
    if not (
        os.path.exists(ss) and os.path.exists(tpi_path) and os.path.exists(par)
    ):
        return None, None
    try:
        safe_read_pickle(ss)
        tpi = safe_read_pickle(tpi_path)
        params = safe_read_pickle(par)
    except Exception:
        return None, None
    return tpi, params


def run_scenario(name, p_reform, ctx):
    """Solve one scenario, with checkpoint/resume and an immediate report.

    Checkpoint: if the scenario's model outputs already exist and load
    cleanly (and ctx['force'] is False), the expensive solve is skipped.
    Missing or corrupt outputs are treated as not-done and overwritten.
    A failure in one scenario is caught and recorded so others continue.
    """
    output_dir = p_reform.output_base
    csv_path = os.path.join(ctx["save_dir"], f"results_{name}.csv")

    # --- Checkpoint ---
    if not ctx["force"]:
        tpi, params = load_outputs(output_dir)
        if tpi is not None:
            if os.path.exists(csv_path):
                print(
                    f"=== {name}: already complete (model + report) - "
                    "skipping ===",
                    flush=True,
                )
                ctx["run_log"][name] = {
                    "status": "skipped",
                    "seconds": 0.0,
                    "error": None,
                }
            else:
                print(
                    f"=== {name}: model already solved - building report "
                    "only ===",
                    flush=True,
                )
                _build_report(name, output_dir, tpi, params, ctx)
                ctx["run_log"][name] = {
                    "status": "report-only",
                    "seconds": 0.0,
                    "error": None,
                }
            return True

    # --- Fresh solve ---
    print(f"\n=== Running scenario {name} ===", flush=True)
    start = time.time()
    try:
        runner(p_reform, time_path=True, client=ctx["client"])
    except Exception:
        elapsed = time.time() - start
        tb = traceback.format_exc()
        print(
            f"!!! Scenario {name} FAILED after {elapsed:.1f}s - skipping.",
            flush=True,
        )
        print(tb, flush=True)
        ctx["run_log"][name] = {
            "status": "failed",
            "seconds": elapsed,
            "error": tb,
        }
        return False

    elapsed = time.time() - start
    print(f"{name} solved in {elapsed:.1f}s - building report...", flush=True)
    tpi, params = load_outputs(output_dir)
    if tpi is None:
        print(
            f"!!! {name} ran but its outputs are missing/corrupt - "
            "report skipped.",
            flush=True,
        )
        ctx["run_log"][name] = {
            "status": "failed",
            "seconds": elapsed,
            "error": "outputs missing/corrupt after run",
        }
        return False
    _build_report(name, output_dir, tpi, params, ctx)
    ctx["run_log"][name] = {"status": "ok", "seconds": elapsed, "error": None}
    return True


def _build_report(name, output_dir, reform_tpi, reform_params, ctx):
    """Write the %-change CSV and comparison plots for one scenario.

    Called as soon as a scenario solves (or when resuming), so each
    scenario's report is on disk the moment it finishes - a later crash
    never loses it.
    """
    try:
        tbl = ot.macro_table(
            ctx["base_tpi"],
            ctx["base_params"],
            reform_tpi=reform_tpi,
            reform_params=reform_params,
            var_list=ctx["var_list"],
            output_type="pct_diff",
            num_years=ctx["num_years"],
            start_year=ctx["start_year"],
        )
        tbl.to_csv(os.path.join(ctx["save_dir"], f"results_{name}.csv"))
        print(f"\n{name.upper()} results (% change vs. B0 baseline):")
        print(tbl, flush=True)
    except Exception:
        print(f"!!! Building results table for {name.upper()} failed:")
        print(traceback.format_exc(), flush=True)
        return
    try:
        op.plot_all(
            ctx["base_dir"],
            output_dir,
            os.path.join(ctx["save_dir"], f"plots_{name}"),
        )
    except Exception:
        print(f"  (plots for {name.upper()} failed)")
        print(traceback.format_exc(), flush=True)


# ===========================================================================
# Intergenerational welfare: lifetime consumption-equivalent variation (CEV)
# ---------------------------------------------------------------------------
# Proposal Section 5.5 / Objective 4: "lifetime utility by birth cohort,
# expressed as equivalent variation in consumption."
#
# OG-ETH's period utility of consumption is CRRA (marg_ut_cons => c^{-sigma}),
# so the per-period felicity is c^{1-sigma}/(1-sigma). For a cohort we form
# discounted expected lifetime consumption utility along its life-cycle
# diagonal of the solved consumption array c[t, s, j], using the model's own
# discount factor beta_j, survival (1-rho_s), and the balanced-growth weight
# e^{g_y*(1-sigma)} per period (consumption is stationarized, so the common
# trend cancels between baseline and reform for a given cohort).
#
# CEV(alpha) solves  V_base((1+alpha) c) = V_reform.  Because felicity is
# CRRA, V_base((1+alpha)c) = (1+alpha)^{1-sigma} V_base, giving the closed
# form  alpha = (V_reform / V_base)^{1/(1-sigma)} - 1.  alpha > 0 means the
# cohort is better off under the reform (would need its baseline consumption
# scaled UP by alpha to be made indifferent).
#
# This is a consumption-based welfare measure (as the proposal specifies). It
# captures the transition-path wage suppression highlighted in the expected
# findings: suppressed wages depress c for the affected cohorts, yielding a
# negative CEV for them. It does not net out changes in labor disutility; a
# full-utility CEV would additionally reconstruct OG-ETH's elliptical labor
# term, which is left to extended robustness work.
# ===========================================================================
def _cohort_welfare(base_c, reform_c, p, s0, t0):
    """Per-ability lifetime consumption utilities and CEV for one cohort.

    The cohort is at age-index ``s0`` at model time ``t0`` and is tracked
    forward along its life-cycle diagonal (age s0+a at time t0+a). Returns
    ``(cev_j, cev_agg)`` where ``cev_j`` is the CEV by ability type (shape J)
    and ``cev_agg`` is the lambda-weighted (utilitarian) cohort CEV.
    """
    S, J = int(p.S), int(p.J)
    sigma = float(p.sigma)
    g_y = float(p.g_y)
    beta = np.array(p.beta).flatten()  # (J,) per-period discount
    rho_ss = np.array(p.rho)[-1, :]  # (S,) stationary mortality by age
    lam = np.array(p.lambdas).flatten()  # (J,) ability-type population shares

    a = np.arange(S - s0)  # remaining-life step index
    ages = s0 + a  # age indices over the life-cycle
    times = t0 + a  # corresponding model times
    keep = times < base_c.shape[0]  # stay inside the transition horizon
    a, ages, times = a[keep], ages[keep], times[keep]

    # Survival from age s0: surv[0] = 1, surv[k] = prod_{i<k}(1 - rho_{s0+i}).
    if ages.size > 1:
        surv = np.concatenate([[1.0], np.cumprod(1.0 - rho_ss[ages[:-1]])])
    else:
        surv = np.array([1.0])

    # Effective discount weight per remaining-life step, by ability type.
    disc = (
        (beta[None, :] ** a[:, None])
        * np.exp(g_y * (1.0 - sigma) * a[:, None])
        * surv[:, None]
    )  # (n_rem, J)

    cev_j = np.zeros(J)
    Vb_j = np.zeros(J)
    Vr_j = np.zeros(J)
    for j in range(J):
        cb = np.maximum(base_c[times, ages, j], 1e-8)
        cr = np.maximum(reform_c[times, ages, j], 1e-8)
        Vb_j[j] = np.sum(disc[:, j] * cb ** (1.0 - sigma) / (1.0 - sigma))
        Vr_j[j] = np.sum(disc[:, j] * cr ** (1.0 - sigma) / (1.0 - sigma))
        cev_j[j] = (Vr_j[j] / Vb_j[j]) ** (1.0 / (1.0 - sigma)) - 1.0

    Vb = np.sum(lam * Vb_j)
    Vr = np.sum(lam * Vr_j)
    cev_agg = (Vr / Vb) ** (1.0 / (1.0 - sigma)) - 1.0
    return cev_j, cev_agg


def build_welfare_tables(base_dir, scenario_dirs, p, save_dir):
    """Write the intergenerational CEV decomposition for every scenario.

    Produces three CSVs in ``save_dir``:
      welfare_cev_by_age.csv      CEV (%) by current age, scenario columns
      welfare_cev_by_ability.csv  CEV (%) by ability type (age-20 cohort)
      welfare_cev_summary.csv     25-45 band average and long-run-newborn CEV
    """
    base_tpi, _ = load_outputs(base_dir)
    if base_tpi is None or "c" not in base_tpi:
        print("Skipping welfare decomposition: B0 consumption path missing.")
        return
    base_c = np.array(base_tpi["c"])

    S = int(p.S)
    T = int(p.T)
    start_age = int(p.starting_age)
    ages_actual = start_age + np.arange(S)  # 20 .. 99
    # Far-future newborn whose whole life sits in the late transition (~SS).
    t0_ss = max(T - S - 1, 1)

    by_age = {"age": ages_actual}
    by_ability = {"ability_type": [f"j{j + 1}" for j in range(int(p.J))]}
    summary = {
        "scenario": [],
        "cev_25_45_avg_pct": [],
        "cev_newborn_ss_pct": [],
    }

    for name, d in scenario_dirs.items():
        rtpi, _ = load_outputs(d)
        if rtpi is None or "c" not in rtpi:
            print(
                f"  (welfare: {name} consumption path unavailable - skipped)"
            )
            continue
        rc = np.array(rtpi["c"])

        # CEV by current age (lambda-weighted across ability types), cohorts
        # alive at the reform start (t0 = 0, age-index s0 = 0 .. S-1).
        age_col = np.array(
            [_cohort_welfare(base_c, rc, p, s0, 0)[1] for s0 in range(S)]
        )
        by_age[name] = 100.0 * age_col

        # CEV by ability type for the youngest current cohort (age 20, s0=0).
        by_ability[name] = 100.0 * _cohort_welfare(base_c, rc, p, 0, 0)[0]

        # Headline summary: average over the 25-45 band, and the long-run
        # (steady-state) newborn cohort.
        band = (ages_actual >= 25) & (ages_actual <= 45)
        cev_ss = _cohort_welfare(base_c, rc, p, 0, t0_ss)[1]
        summary["scenario"].append(name)
        summary["cev_25_45_avg_pct"].append(100.0 * age_col[band].mean())
        summary["cev_newborn_ss_pct"].append(100.0 * cev_ss)

    df_age = pd.DataFrame(by_age).set_index("age")
    df_abi = pd.DataFrame(by_ability).set_index("ability_type")
    df_sum = pd.DataFrame(summary).set_index("scenario")

    df_age.to_csv(os.path.join(save_dir, "welfare_cev_by_age.csv"))
    df_abi.to_csv(os.path.join(save_dir, "welfare_cev_by_ability.csv"))
    df_sum.to_csv(os.path.join(save_dir, "welfare_cev_summary.csv"))

    print(
        "\n=== INTERGENERATIONAL WELFARE (CEV vs B0 baseline) ==="
    )
    print("CEV (% of lifetime consumption) vs B0 baseline; + = better off.\n")
    print("By current age (selected ages):")
    show = df_age.loc[df_age.index.isin(range(20, 96, 5))]
    print(show.round(3).to_string())
    print("\nBy ability type, youngest current cohort (age 20):")
    print(df_abi.round(3).to_string())
    print("\nHeadline summary:")
    print(df_sum.round(3).to_string(), flush=True)


class _SerialClient:
    """Falsy stand-in for a Dask client that forces OG-Core's serial path.

    OG-Core 0.14.x calls client.scatter() unconditionally in TPI.run_TPI
    (outside its 'if client:' guard), so passing client=None raises
    AttributeError.  This shim is falsy - so all guarded calls take the
    serial branch - while still answering .scatter() and .close().
    Net effect: a fully serial, single-process run with no Dask overhead.
    """

    def __bool__(self):
        return False

    def scatter(self, obj, *args, **kwargs):
        return obj

    def close(self):
        pass


def main():
    # Repair a malformed un_api_token.txt before any UN-data fetch.
    _sanitize_un_token()

    # ------------------------------------------------------------------
    # Execution mode.
    # Set USE_DASK = True to attempt parallel execution via Dask.
    # Serial mode is the default: see youth_dividend_new.py for the reason
    # (Dask heartbeat storms on Windows; _SerialClient workaround).
    # ------------------------------------------------------------------
    USE_DASK = False
    if USE_DASK:
        num_workers = min(multiprocessing.cpu_count(), 2)
        client = Client(n_workers=num_workers, threads_per_worker=1)
        print(f"Dask workers = {num_workers}")
    else:
        num_workers = 1
        client = _SerialClient()
        print("Running serially for stability (USE_DASK = False).")

    # Per-scenario success/failure log.
    run_log = {}

    # ------------------------------------------------------------------
    # Directory layout (proposal Table 2: five scenarios B0-B4)
    # ------------------------------------------------------------------
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(CUR_DIR, "DebtConsolidation")

    base_dir = os.path.join(save_dir, "OUTPUT_B0_IMF_BASELINE")
    b1_dir = os.path.join(save_dir, "OUTPUT_B1_ACCELERATED")
    b2_dir = os.path.join(save_dir, "OUTPUT_B2_PRODUCTIVE_INVEST")
    b3_dir = os.path.join(save_dir, "OUTPUT_B3_TRANSFER_CUT")
    b4_dir = os.path.join(save_dir, "OUTPUT_B4_DELAYED_CONSOLIDATION")

    for d in [save_dir, base_dir, b1_dir, b2_dir, b3_dir, b4_dir]:
        os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------------
    # Initialise OG-ETH baseline specifications
    # ------------------------------------------------------------------
    p = Specifications(
        baseline=True,
        num_workers=num_workers,
        baseline_dir=base_dir,
        output_base=base_dir,
    )
    with (
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .open("r") as file
    ):
        defaults = json.load(file)
    p.update_specifications(defaults)
    if is_connected():
        c = Calibration(p, update_from_api=False)
        p.update_specifications(c.get_dict())

    # ------------------------------------------------------------------
    # Apply Ethiopia-specific calibration overrides (Table 1).
    # NOTE: the debt target, consolidation timeline (tG1/tG2), public
    # investment share, and gov borrowing-rate scale are applied HERE so the
    # solved model reflects Ethiopia's IMF ECF-EFF path rather than OG-Core's
    # generic defaults. r_gov_shift is set to 0 so r_gov = r_gov_scale * r.
    # ------------------------------------------------------------------
    cal = ETH_CALIBRATION
    p.update_specifications(
        {
            "alpha_G": [cal["alpha_G"]],
            "alpha_T": [cal["alpha_T"]],
            # OG-Core uses g_y for TFP growth. Annual rate from NBE/WDI.
            "g_y_annual": cal["g_y_annual"],
            "initial_debt_ratio": cal["initial_debt_ratio"],
            "debt_ratio_ss": cal["debt_ratio_ss_baseline"],
            "tG1": cal["tG1"],
            "tG2": cal["tG2"],
            "alpha_I": [cal["alpha_I_pub"]],
            "r_gov_scale": [cal["r_gov_premium"]],
            "r_gov_shift": [0.0],
        }
    )
    print(
        f"\nETH_CALIBRATION applied (Table 1):"
        f"\n  alpha_G        = {cal['alpha_G']:.3f} (Govt consumption/GDP)"
        f"\n  alpha_T        = {cal['alpha_T']:.3f} (Transfers/GDP)"
        f"\n  alpha_I        = {cal['alpha_I_pub']:.3f} (Public investment/GDP)"
        f"\n  g_y_annual     = {cal['g_y_annual']:.3f} (TFP growth)"
        f"\n  debt/GDP (t=0) = {cal['initial_debt_ratio']:.3f}"
        f"\n  debt/GDP (SS)  = {cal['debt_ratio_ss_baseline']:.3f} (IMF target)"
        f"\n  tG1 / tG2      = {cal['tG1']} / {cal['tG2']} (consolidation window)"
        f"\n  r_gov_scale    = {cal['r_gov_premium']:.3f} (gov borrowing premium)"
    )

    # ------------------------------------------------------------------
    # Localise demographics to Ethiopia (country code 231).
    # All fiscal scenarios share the same demographic baseline (demographics
    # are NOT perturbed in this study - only fiscal parameters change).
    # ------------------------------------------------------------------
    print(
        f"\nRecomputing demographics for Ethiopia "
        f"(country {_DEMOG_COUNTRY}) ...",
        flush=True,
    )
    demog_eth = _recompute_demographics(p)
    for _k in _DEMOG_KEYS:
        setattr(p, _k, demog_eth[_k])
    print(f"  Ethiopia g_n_ss = {float(p.g_n_ss):.5f}", flush=True)

    # ------------------------------------------------------------------
    # Checkpoint / resume control.
    # FORCE_RERUN = False -> skip scenarios whose outputs already exist.
    # FORCE_RERUN = True  -> re-solve everything from scratch.
    # ------------------------------------------------------------------
    FORCE_RERUN = False

    # ------------------------------------------------------------------
    # Solve the Baseline (B0) - IMF ECF-EFF Path
    # Gradual expenditure rationalisation: debt/GDP 33% -> 24% by 2030.
    # This is the reference against which all B1-B4 scenarios are measured.
    # ------------------------------------------------------------------
    base_tpi, base_params = (None, None)
    if not FORCE_RERUN:
        base_tpi, base_params = load_outputs(base_dir)

    if base_tpi is not None:
        print("B0 BASELINE: already solved and valid - skipping (checkpoint).")
        run_log["B0_BASELINE"] = {
            "status": "skipped",
            "seconds": 0.0,
            "error": None,
        }
    else:
        print("\n=== Running B0 BASELINE (IMF ECF-EFF path) ===", flush=True)
        start_time = time.time()
        try:
            runner(p, time_path=True, client=client)
        except Exception:
            print("!!! B0 BASELINE run failed - cannot compute comparisons.")
            print(traceback.format_exc())
            if client is not None:
                client.close()
            return
        baseline_seconds = time.time() - start_time
        print(f"B0 baseline run time = {baseline_seconds:.1f}s")
        run_log["B0_BASELINE"] = {
            "status": "ok",
            "seconds": baseline_seconds,
            "error": None,
        }
        base_tpi, base_params = load_outputs(base_dir)

    if base_tpi is None:
        print("!!! B0 baseline outputs missing/corrupt - cannot proceed.")
        if client is not None:
            client.close()
        return

    # Safety: the comparison baseline MUST share the Ethiopia demographics.
    if not np.isclose(float(base_params.g_n_ss), float(p.g_n_ss), rtol=1e-3):
        print(
            "!!! Baseline demographics do not match Ethiopia "
            f"(country {_DEMOG_COUNTRY}):\n"
            f"      baseline g_n_ss = {float(base_params.g_n_ss):.5f}, "
            f"expected ~= {float(p.g_n_ss):.5f}.\n"
            "    A baseline from a different country/run is on disk. Delete\n"
            "    DebtConsolidation/OUTPUT_B0_IMF_BASELINE and stale CSVs,\n"
            "    then re-run so the baseline re-solves."
        )
        if client is not None:
            client.close()
        return

    # Shared context passed into every run_scenario / _build_report call.
    ctx = {
        "client": client,
        "run_log": run_log,
        "save_dir": save_dir,
        "base_dir": base_dir,
        "base_tpi": base_tpi,
        "base_params": base_params,
        "var_list": ["Y", "C", "K", "L", "r", "w"],
        "num_years": 10,
        "start_year": base_params.start_year,
        "force": FORCE_RERUN,
    }

    # Baseline fiscal levels reused as the reference point for the reforms.
    current_alpha_G = float(np.array(p.alpha_G).flatten()[0])
    current_alpha_T = float(np.array(p.alpha_T).flatten()[0])
    current_alpha_I = float(np.array(p.alpha_I).flatten()[0])

    # ====================================================================
    # SCENARIO B1 - Accelerated Consolidation
    # Policy: aggressive tightening; alpha_G -3pp; SS debt target 0.15.
    # Source: IMF ECF-EFF 4th Review 2026; World Bank DSA 2025.
    # ====================================================================
    p_b1 = copy.deepcopy(p)
    p_b1.baseline = False
    p_b1.output_base = b1_dir
    accelerated_alpha_G = max(current_alpha_G - 0.030, 0.01)  # floor at 1%
    p_b1.update_specifications(
        {"alpha_G": [accelerated_alpha_G], "debt_ratio_ss": 0.15}
    )
    print(
        f"\nB1: alpha_G {current_alpha_G:.3f} -> {accelerated_alpha_G:.3f} "
        f"(-3 pp); debt SS -> 0.15 (accelerated tightening)"
    )
    run_scenario("B1_ACCELERATED", p_b1, ctx)

    # ====================================================================
    # SCENARIO B2 - Productive Debt-Financed Infrastructure Investment
    # Policy: HGER 2.0 push; alpha_I +2pp (builds public capital K_g, which
    #   enters the production function, gamma_g > 0); SS debt target 0.42.
    # Source: World Bank HGER 2.0 (~US$10bn); MoF capex budget 2024.
    # ====================================================================
    p_b2 = copy.deepcopy(p)
    p_b2.baseline = False
    p_b2.output_base = b2_dir
    invest_alpha_I = current_alpha_I + 0.020  # +2 pp public investment push
    p_b2.update_specifications(
        {"alpha_I": [invest_alpha_I], "debt_ratio_ss": 0.42}
    )
    print(
        f"\nB2: alpha_I {current_alpha_I:.3f} -> {invest_alpha_I:.3f} "
        f"(+2 pp public investment, HGER 2.0); debt SS -> 0.42"
    )
    run_scenario("B2_PRODUCTIVE_INVEST", p_b2, ctx)

    # ====================================================================
    # SCENARIO B3 - Transfer-Led Adjustment
    # Policy: reach the same debt target as B0 (0.24) by cutting transfers
    #   (alpha_T -1.5pp) rather than government consumption.
    # Source: UNDP Quarterly Profile 2025; MoF social spending data.
    # ====================================================================
    p_b3 = copy.deepcopy(p)
    p_b3.baseline = False
    p_b3.output_base = b3_dir
    transfer_cut_alpha_T = max(current_alpha_T - 0.015, 0.005)  # floor 0.5%
    p_b3.update_specifications(
        {"alpha_T": [transfer_cut_alpha_T], "debt_ratio_ss": 0.24}
    )
    print(
        f"\nB3: alpha_T {current_alpha_T:.3f} -> {transfer_cut_alpha_T:.3f} "
        f"(-1.5 pp); debt SS -> 0.24 (transfer compression)"
    )
    run_scenario("B3_TRANSFER_CUT", p_b3, ctx)

    # ====================================================================
    # SCENARIO B4 - Delayed Consolidation (Cost of Reform Inaction)
    # Policy: the same B0 path and SS target (0.24) but started 5 years
    #   later - the consolidation window opens at tG1 = 8 instead of 3.
    #   B0 consolidates via the debt closure rule over the tG1->tG2 window,
    #   so the cost of delay is modelled by shifting that window, NOT by
    #   ramping alpha_G. alpha_G stays at the baseline level.
    # Source: IMF ECF-EFF risk scenarios; DeBacker & Evans 2023.
    # ====================================================================
    p_b4 = copy.deepcopy(p)
    p_b4.baseline = False
    p_b4.output_base = b4_dir
    p_b4.update_specifications({"tG1": 8, "debt_ratio_ss": 0.24})
    print(
        f"\nB4: tG1 {cal['tG1']} -> 8 (consolidation delayed 5 years; "
        f"same SS target 0.24 as B0)"
    )
    run_scenario("B4_DELAYED_CONSOLIDATION", p_b4, ctx)

    # ====================================================================
    # Objective 5 - Cost of delay: B4 vs B0
    # How much permanent GDP does a 5-year delay cost?
    # ====================================================================
    b4_tpi, b4_p = load_outputs(b4_dir)
    if b4_tpi is not None:
        try:
            delay_cost = ot.macro_table(
                base_tpi,
                base_params,
                reform_tpi=b4_tpi,
                reform_params=b4_p,
                var_list=ctx["var_list"],
                output_type="pct_diff",
                num_years=ctx["num_years"],
                start_year=ctx["start_year"],
            )
            delay_cost.to_csv(
                os.path.join(save_dir, "results_B4_vs_B0_cost_of_delay.csv")
            )
            print("\n=== COST OF DELAY: B4 vs B0 (5-year delay) ===")
            print(delay_cost)
        except Exception:
            print("!!! Cost-of-delay table (B4 vs B0) failed:")
            print(traceback.format_exc())
    else:
        print("Skipping cost-of-delay table: B4 not available.")

    # ====================================================================
    # Objective 6 - Instrument equity: B1 (accelerated G-cut) vs B3
    # (transfer compression). Which instrument distributes the burden
    # more equitably for a comparable consolidation effort?
    # ====================================================================
    b1_tpi, b1_p = load_outputs(b1_dir)
    b3_tpi, b3_p = load_outputs(b3_dir)
    if b1_tpi is not None and b3_tpi is not None:
        try:
            instrument_equity = ot.macro_table(
                b1_tpi,
                b1_p,
                reform_tpi=b3_tpi,
                reform_params=b3_p,
                var_list=ctx["var_list"],
                output_type="pct_diff",
                num_years=ctx["num_years"],
                start_year=ctx["start_year"],
            )
            instrument_equity.to_csv(
                os.path.join(
                    save_dir, "results_B3_vs_B1_instrument_equity.csv"
                )
            )
            print(
                "\n=== INSTRUMENT EQUITY: Transfer-cut (B3) vs G-cut (B1) ==="
            )
            print(instrument_equity)
        except Exception:
            print("!!! Instrument equity table (B3 vs B1) failed:")
            print(traceback.format_exc())
    else:
        print("Skipping instrument equity table: B1 and/or B3 not available.")

    # ====================================================================
    # Objective 4 - Intergenerational welfare decomposition (CEV by cohort)
    # ====================================================================
    welfare_dirs = {
        "B1_ACCELERATED": b1_dir,
        "B2_PRODUCTIVE_INVEST": b2_dir,
        "B3_TRANSFER_CUT": b3_dir,
        "B4_DELAYED_CONSOLIDATION": b4_dir,
    }
    try:
        build_welfare_tables(base_dir, welfare_dirs, base_params, save_dir)
    except Exception:
        print("!!! Welfare decomposition failed:")
        print(traceback.format_exc())

    # ====================================================================
    # Final run summary
    # ====================================================================
    if client is not None:
        client.close()

    print("\n================ RUN SUMMARY ================")
    all_scenarios = [
        "B0_BASELINE",
        "B1_ACCELERATED",
        "B2_PRODUCTIVE_INVEST",
        "B3_TRANSFER_CUT",
        "B4_DELAYED_CONSOLIDATION",
    ]
    for name in all_scenarios:
        info = run_log.get(name, {"status": "not attempted", "seconds": 0.0})
        print(
            f"  {name:<30} {info['status']:<14} "
            f"{info.get('seconds', 0.0):8.1f}s"
        )

    failed = [n for n, i in run_log.items() if i["status"] == "failed"]
    if failed:
        print(f"\n{len(failed)} scenario(s) FAILED: {', '.join(failed)}")
        print("See tracebacks above for the cause of each failure.")
    else:
        print("\nAll scenarios are complete (freshly solved or resumed).")

    print("\n=== KEY CALIBRATION REMINDER (proposal Table 1 / Table 2) ===")
    print(
        f"  B0 (IMF baseline): debt/GDP "
        f"{ETH_CALIBRATION['initial_debt_ratio']:.3f} -> "
        f"{ETH_CALIBRATION['debt_ratio_ss_baseline']:.3f} SS "
        f"(alpha_G gradual; tG1={ETH_CALIBRATION['tG1']}, "
        f"tG2={ETH_CALIBRATION['tG2']})"
    )
    print("  B1 (Accelerated) : alpha_G -0.030 -> debt SS 0.15")
    print("  B2 (Prod. invest): alpha_I +0.020 -> debt SS 0.42 (HGER 2.0)")
    print("  B3 (Transfer cut): alpha_T -0.015 -> debt SS 0.24 (= B0)")
    print("  B4 (Delay)       : tG1 = 8 -> debt SS 0.24 (5-year delay)")
    print(
        "\nOutput files are in: DebtConsolidation/\n"
        "  results_<scenario>.csv               - % change vs B0 baseline\n"
        "  plots_<scenario>/                    - comparison plots\n"
        "  results_B4_vs_B0_cost_of_delay.csv\n"
        "  results_B3_vs_B1_instrument_equity.csv\n"
        "  welfare_cev_by_age.csv               - CEV by current age\n"
        "  welfare_cev_by_ability.csv           - CEV by ability type\n"
        "  welfare_cev_summary.csv              - 25-45 band + long-run newborn"
    )


if __name__ == "__main__":
    main()

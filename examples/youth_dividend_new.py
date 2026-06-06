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
# "str" dtype for text columns. ogcore.demographics.get_un_data then assigns
# an int into a string column (df.loc[df.age == "100+", "age"] = 100), which
# pandas 3.0 rejects with a TypeError. Restore the pre-3.0 object dtype for
# inferred strings so the UN demographic-data parsing keeps working.
pd.set_option("future.infer_string", False)

# Use a custom matplotlib style file for plots
plt.style.use("ogcore.OGcorePlots")


# Demographic objects that OG-Core derives together and that must stay
# mutually consistent; see _recompute_demographics.
_DEMOG_KEYS = (
    "omega",
    "omega_SS",
    "omega_S_preTP",
    "g_n",
    "g_n_ss",
    "imm_rates",
    "rho",
)

# Cache the baseline UN data fetch so demographic scenarios don't hit the
# network (or re-prompt for a UN API token) once per scenario.
_DEMOG_BASE_CACHE = {}


def _sanitize_un_token(path="un_api_token.txt"):
    """Ensure un_api_token.txt holds only the bare UN API token.

    The UN data portal presents the token wrapped in instructions ("Key:
    Authorization", "Bearer <jwt>", usage examples). OG-Core builds the
    request header as "Bearer " + the file's contents, so any extra text or
    line breaks produce a requests InvalidHeader and the run dies before it
    starts. Pasting the whole block into the file is an easy mistake, and an
    open editor can re-save the bad version over a manual fix, so we repair
    it automatically here: extract the JWT and rewrite the file with just
    that. If no token is found, blank the file so OG-Core falls back to the
    EAPD-DRB GitHub population data rather than sending a malformed header.

    Looked up CWD-relative, exactly as ogcore.demographics.get_un_data does.
    """
    if not os.path.exists(path):
        # No token file at all is the dangerous case: ogcore.demographics
        # .get_un_data falls through to input() to prompt for a token, which
        # blocks a non-interactive/background run FOREVER (no stdin to answer
        # — observed as a multi-hour hang at ~0 CPU on the demographics step).
        # Create an empty file so OG-Core takes the file branch instead: it
        # sends an empty Bearer token, gets a non-200, and falls back to the
        # EAPD-DRB GitHub population data. Never prompts, never hangs.
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("")
        print(f"No {path}; created empty token file (GitHub fallback).")
        return
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    token = raw.strip()
    if token and "\n" not in token and " " not in token:
        return  # already just a bare token — nothing to do
    match = re.search(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", raw)
    cleaned = match.group(0) if match else ""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(cleaned)
    if cleaned:
        print(f"Sanitized {path} to the bare UN API token.")
    else:
        print(f"No token in {path}; blanked it to use the GitHub fallback.")


# OG-ETH calibrates its demographics to UN country  over the
# (start_year-1 .. start_year+1) data window (see ogeth/calibrate.py). We
# reuse that exact recipe so a no-shock recompute reproduces the packaged
# baseline, and a shocked scenario is a pure perturbation of that baseline.
_DEMOG_COUNTRY = "231"  # UN code for Ethiopia previous was  South Africa


def _baseline_rate_matrices(p, country_id):
    """Fetch and cache the baseline fertility/mortality rate matrices.

    Uses the same country and data-year window as OG-ETH's calibration
    (initial_data_year = start_year-1, final_data_year = start_year+1), so
    these are the rates that generated the packaged baseline demographics.
    Cached so the demographic scenarios share a single network fetch.

    Returns (fert, mort, infmort) with shapes (T0, E+S), (T0, E+S), (T0,),
    where T0 = final_data_year - initial_data_year + 1.
    """
    idy, fdy = int(p.start_year - 1), int(p.start_year + 1)
    totpers = int(p.E + p.S)
    key = (country_id, idy, fdy, totpers)
    if key not in _DEMOG_BASE_CACHE:
        fert = demog.get_fert(totpers, 0, 99, country_id, idy, fdy)
        mort, infmort = demog.get_mort(totpers, 0, 99, country_id, idy, fdy)
        _DEMOG_BASE_CACHE[key] = (fert, mort, infmort)
    return _DEMOG_BASE_CACHE[key]


def _recompute_demographics(
    p, fert_mult=None, mort_mult=None, country_id=_DEMOG_COUNTRY
):
    """Recompute OG-Core's full, mutually-consistent demographic object set.

    OG-Core's seven demographic objects (omega, omega_SS, omega_S_preTP, g_n,
    g_n_ss, imm_rates, rho) are not independent dials: they are all derived
    together from the underlying fertility, mortality and immigration rate
    matrices via demog.get_pop_objs. Perturbing one in isolation (e.g. only
    g_n, or only rho) leaves the population accounting internally inconsistent,
    which OG-Core rejects with "resource constraint not satisfied" in SS or a
    TPI RC_error.

    This reproduces OG-ETH's own calibration recipe exactly (the same country
    and start_year-1..start_year+1 data window as ogeth/calibrate.py) and feeds
    it the baseline fertility/mortality matrices with optional age multipliers
    applied. With fert_mult = mort_mult = None the result is identical to the
    solved baseline, so a shocked scenario is measured as a *pure* perturbation
    of that baseline — there is no recompute-vs-baseline artifact, and the real
    declining-fertility transition is preserved. Population and immigration are
    inferred internally by get_pop_objs, exactly as in the baseline
    calibration, which is what keeps the new steady state consistent.

    ``fert_mult`` / ``mort_mult`` are length-(E+S) age multipliers on the
    baseline rates (None = leave that channel unchanged; a 1.0 entry = no
    change at that age).

    Requires internet at call time (UN WPP API, with the EAPD-DRB GitHub copy
    as fallback). Returns the dict from demog.get_pop_objs.
    """
    idy, fdy = int(p.start_year - 1), int(p.start_year + 1)
    fert, mort, infmort = _baseline_rate_matrices(p, country_id)
    fert, mort, infmort = fert.copy(), mort.copy(), infmort.copy()
    if fert_mult is not None:
        fert = fert * np.asarray(fert_mult, dtype=float)[np.newaxis, :]
    if mort_mult is not None:
        mort = np.clip(
            mort * np.asarray(mort_mult, dtype=float)[np.newaxis, :], 0.0, 1.0
        )
    return demog.get_pop_objs(
        p.E,
        p.S,
        p.T,
        0,
        99,
        fert_rates=fert,
        mort_rates=mort,
        infmort_rates=infmort,
        country_id=country_id,
        initial_data_year=idy,
        final_data_year=fdy,
        GraphDiag=False,
    )


def load_outputs(output_dir):
    """Return (tpi, params) for a solved scenario, or (None, None).

    Returns (None, None) if any of the SS, TPI, or model-params pickles is
    missing OR fails to unpickle (e.g. a half-written file left by a run that
    was killed mid-save). Callers treat (None, None) as "not done" and
    re-solve the scenario, which overwrites the corrupt files. This is what
    makes the checkpoint safe against corrupted output.
    """
    ss = os.path.join(output_dir, "SS", "SS_vars.pkl")
    tpi_path = os.path.join(output_dir, "TPI", "TPI_vars.pkl")
    par = os.path.join(output_dir, "model_params.pkl")
    if not (
        os.path.exists(ss) and os.path.exists(tpi_path) and os.path.exists(par)
    ):
        return None, None
    try:
        safe_read_pickle(ss)  # validate SS integrity (value not needed here)
        tpi = safe_read_pickle(tpi_path)
        params = safe_read_pickle(par)
    except Exception:
        return None, None
    return tpi, params


def _phase_in_e_path(p, peak_boost, years_to_full):
    """Build a time-varying (T, S, J) ``e`` array that ramps a uniform
    efficiency boost in linearly from 0 to ``peak_boost`` over the first
    ``years_to_full`` model years (starting at the model's first period),
    then holds it at the peak.

    Used for the FLFP-convergence scenarios (G3/G4), where the policy question
    is the *speed* of convergence: the same long-run +``peak_boost`` boost
    reached by different dates. The full-strength 2-D (S, J) target is composed
    separately into the integrated packages (I2/I3); this path is the
    standalone scenario's transition, so a faster ramp is a distinct shock.
    """
    e_base_full = np.array(p.e, dtype=float)  # (T, S, J)
    T = e_base_full.shape[0]
    e_path = np.empty_like(e_base_full)
    for t in range(T):
        frac = min(t / years_to_full, 1.0)
        e_path[t] = e_base_full[t] * (1.0 + peak_boost * frac)
    return e_path


def _build_report(name, output_dir, reform_tpi, reform_params, ctx):
    """Write the %-change CSV and comparison plots for one scenario.

    Called as soon as a scenario solves (or when resuming a scenario whose
    model outputs already exist), so each scenario's report is on disk the
    moment that scenario finishes — a later crash never loses it.
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
        print(f"\n{name.upper()} results")
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


def run_scenario(name, p_reform, ctx):
    """Solve one scenario, with checkpoint/resume and an immediate report.

    Checkpoint: if the scenario's model outputs already exist and load
    cleanly (and ctx['force'] is False), the expensive solve is skipped so a
    re-run continues from where a crash or freeze left off. Missing or
    corrupt outputs are treated as not-done and overwritten.

    On a fresh solve, any failure is caught with its full traceback and
    recorded, so one bad scenario never aborts the batch. After solving (or
    on a checkpoint hit) the scenario's CSV + plots are written immediately.
    """
    output_dir = p_reform.output_base
    csv_path = os.path.join(ctx["save_dir"], f"results_{name}.csv")

    # --- Checkpoint: already solved and valid? ---
    if not ctx["force"]:
        tpi, params = load_outputs(output_dir)
        if tpi is not None:
            if os.path.exists(csv_path):
                print(
                    f"=== {name}: already complete (model + report) — "
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
                    f"=== {name}: model already solved — building report "
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

    # --- Solve (fresh, or previous outputs missing/corrupt -> overwrite) ---
    print(f"\n=== Running scenario {name} ===", flush=True)
    start = time.time()
    try:
        runner(p_reform, time_path=True, client=ctx["client"])
    except Exception:
        elapsed = time.time() - start
        tb = traceback.format_exc()
        print(
            f"!!! Scenario {name} FAILED after {elapsed:.1f}s — skipping.",
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
    print(f"{name} solved in {elapsed:.1f}s — building report...", flush=True)
    tpi, params = load_outputs(output_dir)
    if tpi is None:
        print(
            f"!!! {name} ran but its outputs are missing/corrupt — "
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


class _SerialClient:
    """Falsy stand-in for a Dask client that forces OG-Core's serial path.

    This OG-Core build (0.14.x, locally patched) calls ``client.scatter()``
    unconditionally in ``TPI.run_TPI`` — outside its ``if client:`` guard —
    so passing ``client=None`` crashes there with AttributeError. Every
    other client use in SS.py/TPI.py is gated by ``if client:``.

    This shim is falsy (``__bool__`` returns False), so all those guards take
    the serial branch, but it still answers ``.scatter()`` (returning the
    object unchanged) and ``.close()`` so the one unguarded call and our
    cleanup both succeed. Net effect: a fully serial, single-process run.
    """

    def __bool__(self):
        return False

    def scatter(self, obj, *args, **kwargs):
        return obj

    def close(self):
        pass


def main():
    # Repair a malformed un_api_token.txt (a common paste mistake) before any
    # UN-data fetch, so the demographic scenarios can't die on InvalidHeader.
    _sanitize_un_token()

    # ------------------------------------------------------------------
    # Execution mode.
    #
    # This OG-Core build parallelises the household loop across a Dask
    # cluster (client.scatter/submit/gather) and falls back to serial if the
    # cluster errors. On Windows that fallback runs in the main thread and
    # freezes the in-process Dask scheduler's event loop, so the scheduler
    # declares the healthy workers dead and enters a nanny restart storm —
    # the run hangs for many minutes and emits an uninformative
    # "Dask computation failed with error: ." (an empty-message
    # CancelledError). So we run serially by default.
    #
    # We cannot simply pass client=None: TPI.run_TPI calls client.scatter()
    # unconditionally (a library bug), which raises AttributeError on None.
    # Instead we pass a falsy _SerialClient shim, which forces OG-Core's
    # serial path while satisfying that one unguarded call — identical
    # numerics, no cluster, no heartbeat storms. Set USE_DASK = True to
    # attempt parallel execution.
    # ------------------------------------------------------------------
    USE_DASK = False
    if USE_DASK:
        num_workers = min(multiprocessing.cpu_count(), 2)
        client = Client(n_workers=num_workers, threads_per_worker=1)
        print("Number of Dask workers = ", num_workers)
    else:
        num_workers = 1
        client = _SerialClient()
        print("Running serially for stability.")

    # Tracks per-scenario success/failure for the end-of-run summary.
    run_log = {}

    # Directories to save data
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(CUR_DIR, "YouthDividend")
    base_dir = os.path.join(save_dir, "OUTPUT_BASELINE")

    # Reform directories — one per scenario
    d2_dir = os.path.join(save_dir, "OUTPUT_D2_FERTILITY_DECLINE")
    d3_dir = os.path.join(save_dir, "OUTPUT_D3_MORTALITY_SHOCK")
    d4_dir = os.path.join(save_dir, "OUTPUT_D4_HIGH_FERTILITY")

    e2_dir = os.path.join(save_dir, "OUTPUT_E2_TVET_MODERATE")
    e3_dir = os.path.join(save_dir, "OUTPUT_E3_UNIVERSITY_STRONG")
    e4_dir = os.path.join(save_dir, "OUTPUT_E4_COMBINED_MAX")

    l2_dir = os.path.join(save_dir, "OUTPUT_L2_FORMALISATION_25")
    l3_dir = os.path.join(save_dir, "OUTPUT_L3_FORMALISATION_40")
    l4_dir = os.path.join(save_dir, "OUTPUT_L4_FORMALISATION_55")

    g2_dir = os.path.join(save_dir, "OUTPUT_G2_FLFP_PARTIAL")
    g3_dir = os.path.join(save_dir, "OUTPUT_G3_FLFP_FULL_2040")
    g4_dir = os.path.join(save_dir, "OUTPUT_G4_FLFP_FULL_2030")

    m2_dir = os.path.join(save_dir, "OUTPUT_M2_BRAIN_DRAIN_MOD")
    m3_dir = os.path.join(save_dir, "OUTPUT_M3_BRAIN_DRAIN_SEV")
    m4_dir = os.path.join(save_dir, "OUTPUT_M4_BRAIN_GAIN")

    f2_dir = os.path.join(save_dir, "OUTPUT_F2_EDU_SURGE")
    f3_dir = os.path.join(save_dir, "OUTPUT_F3_EMPLOY_SUBSIDY")
    f4_dir = os.path.join(save_dir, "OUTPUT_F4_GENDER_INVESTMENT")
    f5_dir = os.path.join(save_dir, "OUTPUT_F5_IMF_CONSTRAINT")

    i1_dir = os.path.join(save_dir, "OUTPUT_I1_MODERATE")
    i2_dir = os.path.join(save_dir, "OUTPUT_I2_AMBITIOUS")
    i3_dir = os.path.join(save_dir, "OUTPUT_I3_MAXIMUM")
    i4_dir = os.path.join(save_dir, "OUTPUT_I4_DELAYED_ACTION")

    """
    ---------------------------------------------------------------------------
    Run baseline policy (D1)
    UN WPP 2024 medium-fertility, current fiscal policy
    ---------------------------------------------------------------------------
    """
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
    # Localize ALL demographics to Ethiopia, up front (single network window).
    #
    # The packaged JSON is calibrated to country  (South Africa). Here we
    # recompute the full, mutually-consistent demographic set for
    # _DEMOG_COUNTRY (= "231", Ethiopia): once with no shock for the baseline
    # (and the 20 non-demographic scenarios, which inherit p's demographics via
    # deepcopy), and once per fertility/mortality shock for D2/D3/D4. Doing it
    # all now means the only network access in the whole run happens in these
    # few minutes — the multi-hour solve that follows runs fully offline, so a
    # later connection drop cannot kill it. The baseline override (setattr on
    # p) keeps the baseline, the non-demographic scenarios, and D2/D3/D4 all on
    # the same Ethiopia base, so the comparisons stay apples-to-apples.
    # ------------------------------------------------------------------
    print(
        f"Recomputing demographics for country {_DEMOG_COUNTRY} ...",
        flush=True,
    )
    mort_mult_d3 = np.ones(p.E + p.S)
    mort_mult_d3[20:36] = 1.15  # youth mortality +15%, ages 20-35
    demog_base = _recompute_demographics(p)
    demog_d2 = _recompute_demographics(p, fert_mult=np.full(p.E + p.S, 0.75))
    demog_d3 = _recompute_demographics(p, mort_mult=mort_mult_d3)
    demog_d4 = _recompute_demographics(p, fert_mult=np.full(p.E + p.S, 1.20))
    for _k in _DEMOG_KEYS:
        setattr(p, _k, demog_base[_k])
    print(
        f"  baseline g_n_ss = {float(p.g_n_ss):.5f} "
        f"(country {_DEMOG_COUNTRY})",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Checkpoint / resume.
    #
    # FORCE_RERUN = False -> reuse any scenario whose outputs already exist
    #   and load cleanly (skip the expensive solve); re-solve only what is
    #   missing or corrupt. A re-run then continues from where a crash or
    #   freeze left off instead of starting over.
    # FORCE_RERUN = True  -> ignore existing outputs and re-solve everything.
    # ------------------------------------------------------------------
    FORCE_RERUN = False

    # The baseline is special: every reform table is measured relative to it.
    # Skip it if already solved and valid; otherwise (re)solve and overwrite.
    base_tpi, base_params = (None, None)
    if not FORCE_RERUN:
        base_tpi, base_params = load_outputs(base_dir)

    if base_tpi is not None:
        print("Baseline already solved and valid — skipping (checkpoint).")
        run_log["BASELINE"] = {
            "status": "skipped",
            "seconds": 0.0,
            "error": None,
        }
    else:
        start_time = time.time()
        try:
            runner(p, time_path=True, client=client)
        except Exception:
            print("!!! BASELINE run failed — cannot compute comparisons.")
            print(traceback.format_exc())
            if client is not None:
                client.close()
            return
        baseline_seconds = time.time() - start_time
        print(f"Baseline run time = {baseline_seconds:.1f}s")
        run_log["BASELINE"] = {
            "status": "ok",
            "seconds": baseline_seconds,
            "error": None,
        }
        base_tpi, base_params = load_outputs(base_dir)

    if base_tpi is None:
        print("!!! Baseline outputs missing/corrupt — cannot proceed.")
        if client is not None:
            client.close()
        return

    # Safety: the comparison baseline MUST share the demographics we just
    # applied to p (same country). If an older baseline solved under different
    # demographics is sitting on disk — the common mistake of switching
    # country without deleting OUTPUT_BASELINE — every reform table would
    # measure the demographic gap instead of the policy. Catch it here rather
    # than silently producing wrong reports for all 23 scenarios.
    if not np.isclose(float(base_params.g_n_ss), float(p.g_n_ss), rtol=1e-3):
        print(
            "!!! Baseline demographics do not match the configured country "
            f"({_DEMOG_COUNTRY}):\n"
            f"      baseline g_n_ss = {float(base_params.g_n_ss):.5f}, "
            f"expected ~= {float(p.g_n_ss):.5f}.\n"
            "    A baseline from a different country/run is on disk. Delete\n"
            "    examples/YouthDividend/OUTPUT_BASELINE and the stale\n"
            "    results_*.csv, then re-run so the baseline re-solves."
        )
        if client is not None:
            client.close()
        return

    # Shared context for running scenarios and building their reports.
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

    """
    ---------------------------------------------------------------------------
    DIMENSION 1 — Demographic Foundation
    ---------------------------------------------------------------------------
    """

    ##### D2 — Accelerated Fertility Decline
    # TFR reaches 2.5 by 2035 rather than 2045
    # Modelled as 30% faster decline in population growth over 2025-2035
    # [Source: UN WPP 2024 low-fertility variant; ILO 2023]
    p_d2 = copy.deepcopy(p)
    p_d2.baseline = False
    p_d2.output_base = d2_dir

    # Accelerated fertility decline = 25%-lower fertility regime. Demographics
    # were recomputed up front (demog_d2) as a full consistent set, so the SS
    # and TPI resource constraints hold by construction.
    for _k in _DEMOG_KEYS:
        setattr(p_d2, _k, demog_d2[_k])

    run_scenario("D2", p_d2, ctx)

    ##### D3 — High Youth Mortality Shock
    # Conflict or health crisis raises youth mortality by 15%
    # Affects model age periods 0-15 (ages 20-35) for first 20 periods
    # [Source: World Bank Ethiopia Conflict Impact Report 2023]
    p_d3 = copy.deepcopy(p)
    p_d3.baseline = False
    p_d3.output_base = d3_dir

    # Youth mortality +15% for ages 20-35 (model-age indices 20:36).
    # Demographics were recomputed up front (demog_d3) as a consistent set,
    # not a rho-only override (which left omega/g_n at baseline and failed the
    # SS resource constraint).
    for _k in _DEMOG_KEYS:
        setattr(p_d3, _k, demog_d3[_k])

    run_scenario("D3", p_d3, ctx)

    ##### D4 — High Fertility Upper Bound
    # Population exceeds 200M by 2050 — UN high-fertility variant
    # 30% higher population growth through 2035, slower decline thereafter
    # [Source: UN WPP 2024 high-fertility variant]
    p_d4 = copy.deepcopy(p)
    p_d4.baseline = False
    p_d4.output_base = d4_dir

    # UN high-fertility variant = 20%-higher fertility regime. Demographics
    # were recomputed up front (demog_d4), same machinery as D2.
    for _k in _DEMOG_KEYS:
        setattr(p_d4, _k, demog_d4[_k])

    run_scenario("D4", p_d4, ctx)

    """
    ---------------------------------------------------------------------------
    DIMENSION 2 — Education and Human Capital
    ---------------------------------------------------------------------------
    """

    ##### E2 — Moderate TVET Expansion
    # Age-efficiency units of young workers (ages 20-35) raised by 10%
    # tapering to 0 by age 55. Represents improved vocational training.
    # [Source: World Bank Ethiopia Education Report 2023; ILO 2023]
    p_e2 = copy.deepcopy(p)
    p_e2.baseline = False
    p_e2.output_base = e2_dir

    e0_e2 = np.array(p.e, dtype=float)
    e0_e2 = e0_e2[0] if e0_e2.ndim == 3 else e0_e2  # (S, J)
    ages_e2 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    factor_e2 = np.zeros(p.S)
    for i, a in enumerate(ages_e2):
        if a <= 35:
            factor_e2[i] = 0.10
        elif a < 55:
            factor_e2[i] = 0.10 * (55 - a) / (55 - 35)
    e_new_e2 = e0_e2 * (1.0 + factor_e2[:, np.newaxis])

    p_e2.update_specifications({"e": e_new_e2.tolist()})

    run_scenario("E2", p_e2, ctx)

    ##### E3 — Strong University Quality Improvement
    # Age-efficiency units raised by 20% — stronger reform
    # [Source: World Bank Ethiopia Education Report 2023]
    p_e3 = copy.deepcopy(p)
    p_e3.baseline = False
    p_e3.output_base = e3_dir

    e0_e3 = np.array(p.e, dtype=float)
    e0_e3 = e0_e3[0] if e0_e3.ndim == 3 else e0_e3
    ages_e3 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    factor_e3 = np.zeros(p.S)
    for i, a in enumerate(ages_e3):
        if a <= 35:
            factor_e3[i] = 0.20
        elif a < 55:
            factor_e3[i] = 0.20 * (55 - a) / (55 - 35)
    e_new_e3 = e0_e3 * (1.0 + factor_e3[:, np.newaxis])

    p_e3.update_specifications({"e": e_new_e3.tolist()})

    run_scenario("E3", p_e3, ctx)

    ##### E4 — Combined TVET + University Reform (Maximum Human Capital)
    # Age-efficiency units raised by 25% — full combined reform
    # [Source: World Bank Ethiopia Education Report 2023; ILO 2023]
    p_e4 = copy.deepcopy(p)
    p_e4.baseline = False
    p_e4.output_base = e4_dir

    e0_e4 = np.array(p.e, dtype=float)
    e0_e4 = e0_e4[0] if e0_e4.ndim == 3 else e0_e4
    ages_e4 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    factor_e4 = np.zeros(p.S)
    for i, a in enumerate(ages_e4):
        if a <= 35:
            factor_e4[i] = 0.25
        elif a < 55:
            factor_e4[i] = 0.25 * (55 - a) / (55 - 35)
    e_new_e4 = e0_e4 * (1.0 + factor_e4[:, np.newaxis])

    p_e4.update_specifications({"e": e_new_e4.tolist()})

    run_scenario("E4", p_e4, ctx)

    """
    ---------------------------------------------------------------------------
    DIMENSION 3 — Labour Market and Formalisation
    Productivity premium derivation (ILO 2023):
      Formal workers earn 2.5x informal workers in Ethiopia
      Baseline: 0.13*2.5 + 0.87*1.0 = 1.195
      L2 (25%): 0.25*2.5 + 0.75*1.0 = 1.375 -> boost = +15.1%
      L3 (40%): 0.40*2.5 + 0.60*1.0 = 1.600 -> boost = +33.9%
      L4 (55%): 0.55*2.5 + 0.45*1.0 = 1.825 -> boost = +52.7%
    ---------------------------------------------------------------------------
    """

    ##### L2 — Moderate Formalisation (13% -> 25% formal share by 2035)
    # e +15.1% for working-age workers; frisch +0.05 (reduced frictions)
    # [Source: ILO Ethiopia Labour Market Profile 2023]
    p_l2 = copy.deepcopy(p)
    p_l2.baseline = False
    p_l2.output_base = l2_dir

    e0_l2 = np.array(p.e, dtype=float)
    e0_l2 = e0_l2[0] if e0_l2.ndim == 3 else e0_l2
    ages_l2 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    factor_l2 = np.zeros(p.S)
    for i, a in enumerate(ages_l2):
        if 20 <= a <= 55:
            factor_l2[i] = 0.151
        elif 55 < a < 65:
            factor_l2[i] = 0.151 * (65 - a) / (65 - 55)
    e_new_l2 = e0_l2 * (1.0 + factor_l2[:, np.newaxis])

    p_l2.update_specifications(
        {
            "e": e_new_l2.tolist(),
            "frisch": float(p.frisch) + 0.05,
        }
    )

    run_scenario("L2", p_l2, ctx)

    ##### L3 — Strong Formalisation (13% -> 40% formal share by 2035)
    # e +33.9% for working-age workers; frisch +0.10
    # [Source: ILO Ethiopia Labour Market Profile 2023]
    p_l3 = copy.deepcopy(p)
    p_l3.baseline = False
    p_l3.output_base = l3_dir

    e0_l3 = np.array(p.e, dtype=float)
    e0_l3 = e0_l3[0] if e0_l3.ndim == 3 else e0_l3
    ages_l3 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    factor_l3 = np.zeros(p.S)
    for i, a in enumerate(ages_l3):
        if 20 <= a <= 55:
            factor_l3[i] = 0.339
        elif 55 < a < 65:
            factor_l3[i] = 0.339 * (65 - a) / (65 - 55)
    e_new_l3 = e0_l3 * (1.0 + factor_l3[:, np.newaxis])

    p_l3.update_specifications(
        {
            "e": e_new_l3.tolist(),
            "frisch": float(p.frisch) + 0.10,
        }
    )

    run_scenario("L3", p_l3, ctx)

    ##### L4 — Full Formalisation (13% -> 55% middle-income average by 2035)
    # e +52.7% for working-age workers; frisch +0.15
    # [Source: ILO Ethiopia Labour Market Profile 2023; World Bank 2023]
    p_l4 = copy.deepcopy(p)
    p_l4.baseline = False
    p_l4.output_base = l4_dir

    e0_l4 = np.array(p.e, dtype=float)
    e0_l4 = e0_l4[0] if e0_l4.ndim == 3 else e0_l4
    ages_l4 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    factor_l4 = np.zeros(p.S)
    for i, a in enumerate(ages_l4):
        if 20 <= a <= 55:
            factor_l4[i] = 0.527
        elif 55 < a < 65:
            factor_l4[i] = 0.527 * (65 - a) / (65 - 55)
    e_new_l4 = e0_l4 * (1.0 + factor_l4[:, np.newaxis])

    p_l4.update_specifications(
        {
            "e": e_new_l4.tolist(),
            "frisch": float(p.frisch) + 0.15,
        }
    )

    run_scenario("L4", p_l4, ctx)

    """
    ---------------------------------------------------------------------------
    DIMENSION 4 — Gender Inclusion (Female Labour Force Participation)
    FLFP derivation (ILO 2023):
      Ethiopia female LFP = 39%, male LFP = 77%; 50/50 gender split assumed
      Current aggregate = 0.5*77% + 0.5*39% = 58% of male-equivalent
      Full convergence  = 0.5*77% + 0.5*77% = 77% of male-equivalent
      Gain = (77-58)/58 = 33%; rounded to 30% net of frictions
      G2 (half convergence) = +15%; G3/G4 (full convergence) = +30%
    ---------------------------------------------------------------------------
    """

    ##### G2 — Partial FLFP Convergence by 2040 (halfway toward male levels)
    # Uniform e +15% across all workers (aggregate labour supply effect)
    # [Source: ILO Ethiopia Labour Market Profile 2023]
    p_g2 = copy.deepcopy(p)
    p_g2.baseline = False
    p_g2.output_base = g2_dir

    e0_g2 = np.array(p.e, dtype=float)
    e0_g2 = e0_g2[0] if e0_g2.ndim == 3 else e0_g2
    e_new_g2 = e0_g2 * 1.15

    p_g2.update_specifications({"e": e_new_g2.tolist()})

    run_scenario("G2", p_g2, ctx)

    ##### G3 — Full FLFP Convergence by 2040 (female LFP matches male)
    # Uniform e +30% across all workers, phased in linearly over 2025-2040
    # (15 model years) then held. The full-strength +30% (S, J) target is
    # reused as the static building block for the I2 integrated package.
    # [Source: ILO Ethiopia Labour Market Profile 2023]
    p_g3 = copy.deepcopy(p)
    p_g3.baseline = False
    p_g3.output_base = g3_dir

    e0_g3 = np.array(p.e, dtype=float)
    e0_g3 = e0_g3[0] if e0_g3.ndim == 3 else e0_g3
    e_new_g3 = e0_g3 * 1.30  # long-run target (S, J) — composed into I2
    p_g3.e = _phase_in_e_path(p, 0.30, 15)  # time-varying — full by 2040

    run_scenario("G3", p_g3, ctx)

    ##### G4 — Accelerated Full FLFP Convergence by 2030 (10 years earlier)
    # Same long-run +30% as G3 but phased in over 2025-2030 (5 model years)
    # then held — the "speed of convergence" counterfactual. The +30% (S, J)
    # target is reused as the static building block for the I3 package.
    # [Source: ILO Ethiopia Labour Market Profile 2023]
    p_g4 = copy.deepcopy(p)
    p_g4.baseline = False
    p_g4.output_base = g4_dir

    e0_g4 = np.array(p.e, dtype=float)
    e0_g4 = e0_g4[0] if e0_g4.ndim == 3 else e0_g4
    e_new_g4 = e0_g4 * 1.30  # long-run target (S, J) — composed into I3
    p_g4.e = _phase_in_e_path(p, 0.30, 5)  # time-varying — full by 2030

    run_scenario("G4", p_g4, ctx)

    """
    ---------------------------------------------------------------------------
    DIMENSION 5 — Migration and Brain Drain
    Brain drain modelled by reducing e for top-2 ability groups (highest
    skill) among working-age workers — representing high-skill emigrants.
    Brain gain (M4) raises top-skill e and increases zeta_K (diaspora
    foreign capital inflow). [Source: World Bank Ethiopia Diaspora Report 2024]
    ---------------------------------------------------------------------------
    """

    ##### M2 — Moderate Brain Drain (graduate emigration doubles by 2030)
    # Top-2 skill groups (J=4,5 in 0-index), working-age: e -20%
    # [Source: World Bank Ethiopia Diaspora Report 2024; ILO 2023]
    p_m2 = copy.deepcopy(p)
    p_m2.baseline = False
    p_m2.output_base = m2_dir

    e0_m2 = np.array(p.e, dtype=float)
    e0_m2 = e0_m2[0] if e0_m2.ndim == 3 else e0_m2
    ages_m2 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    w_factor_m2 = np.zeros(p.S)
    for i, a in enumerate(ages_m2):
        if 20 <= a <= 55:
            w_factor_m2[i] = 1.0
        elif 55 < a < 65:
            w_factor_m2[i] = (65 - a) / (65 - 55)
    factor_m2 = np.zeros((p.S, p.J))
    factor_m2[:, -2:] = w_factor_m2[:, np.newaxis]
    e_new_m2 = e0_m2 * (1.0 + factor_m2 * (-0.20))

    p_m2.update_specifications({"e": e_new_m2.tolist()})

    run_scenario("M2", p_m2, ctx)

    ##### M3 — Severe Brain Drain (20% of graduates leave per decade from 2030)
    # Top-2 skill groups, working-age: e -35%
    # [Source: World Bank Ethiopia Diaspora Report 2024]
    p_m3 = copy.deepcopy(p)
    p_m3.baseline = False
    p_m3.output_base = m3_dir

    e0_m3 = np.array(p.e, dtype=float)
    e0_m3 = e0_m3[0] if e0_m3.ndim == 3 else e0_m3
    ages_m3 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    w_factor_m3 = np.zeros(p.S)
    for i, a in enumerate(ages_m3):
        if 20 <= a <= 55:
            w_factor_m3[i] = 1.0
        elif 55 < a < 65:
            w_factor_m3[i] = (65 - a) / (65 - 55)
    factor_m3 = np.zeros((p.S, p.J))
    factor_m3[:, -2:] = w_factor_m3[:, np.newaxis]
    e_new_m3 = e0_m3 * (1.0 + factor_m3 * (-0.35))

    p_m3.update_specifications({"e": e_new_m3.tolist()})

    run_scenario("M3", p_m3, ctx)

    ##### M4 — Brain Gain (net skilled diaspora return)
    # Top-2 skill groups, working-age: e +25%; zeta_K +0.10 (diaspora capital)
    # [Source: World Bank Ethiopia Diaspora Report 2024]
    p_m4 = copy.deepcopy(p)
    p_m4.baseline = False
    p_m4.output_base = m4_dir

    e0_m4 = np.array(p.e, dtype=float)
    e0_m4 = e0_m4[0] if e0_m4.ndim == 3 else e0_m4
    ages_m4 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    w_factor_m4 = np.zeros(p.S)
    for i, a in enumerate(ages_m4):
        if 20 <= a <= 55:
            w_factor_m4[i] = 1.0
        elif 55 < a < 65:
            w_factor_m4[i] = (65 - a) / (65 - 55)
    factor_m4 = np.zeros((p.S, p.J))
    factor_m4[:, -2:] = w_factor_m4[:, np.newaxis]
    e_new_m4 = e0_m4 * (1.0 + factor_m4 * 0.25)
    current_zeta_K = float(np.array(p.zeta_K).flatten()[0])

    p_m4.update_specifications(
        {
            "e": e_new_m4.tolist(),
            "zeta_K": [min(current_zeta_K + 0.10, 0.99)],
        }
    )

    run_scenario("M4", p_m4, ctx)

    """
    ---------------------------------------------------------------------------
    DIMENSION 6 — Fiscal Policy and Youth Investment
    ---------------------------------------------------------------------------
    """

    ##### F2 — Education Investment Surge (+2% of GDP government spending)
    # alpha_G += 0.020
    # [Source: Ethiopian NPC Ten-Year Development Plan 2021-2030]
    p_f2 = copy.deepcopy(p)
    p_f2.baseline = False
    p_f2.output_base = f2_dir

    current_alpha_G_f2 = float(np.array(p.alpha_G).flatten()[0])
    p_f2.update_specifications({"alpha_G": [current_alpha_G_f2 + 0.020]})

    run_scenario("F2", p_f2, ctx)

    ##### F3 — Youth Employment Subsidy (wage subsidy for formal youth hiring)
    # e +10% for ages 20-35 (subsidy lowers effective labour cost);
    # frisch +0.10 (reduced entry barriers raise labour supply elasticity)
    # [Source: World Bank Ethiopia Economic Update 2023]
    p_f3 = copy.deepcopy(p)
    p_f3.baseline = False
    p_f3.output_base = f3_dir

    e0_f3 = np.array(p.e, dtype=float)
    e0_f3 = e0_f3[0] if e0_f3.ndim == 3 else e0_f3
    ages_f3 = np.linspace(
        p.starting_age, p.starting_age + p.S, p.S, endpoint=False
    )
    factor_f3 = np.zeros(p.S)
    for i, a in enumerate(ages_f3):
        if a <= 30:
            factor_f3[i] = 0.10
        elif a < 45:
            factor_f3[i] = 0.10 * (45 - a) / (45 - 30)
    e_new_f3 = e0_f3 * (1.0 + factor_f3[:, np.newaxis])

    p_f3.update_specifications(
        {
            "e": e_new_f3.tolist(),
            "frisch": float(p.frisch) + 0.10,
        }
    )

    run_scenario("F3", p_f3, ctx)

    ##### F4 — Gender Inclusion Investment (targeted transfers + participation)
    # alpha_T +0.010 (transfer payments enabling female participation)
    # e uniform +10% (quality gains from supported female employment)
    # [Source: Ministry of Women and Social Affairs Ethiopia 2024]
    p_f4 = copy.deepcopy(p)
    p_f4.baseline = False
    p_f4.output_base = f4_dir

    e0_f4 = np.array(p.e, dtype=float)
    e0_f4 = e0_f4[0] if e0_f4.ndim == 3 else e0_f4
    e_new_f4 = e0_f4 * 1.10
    current_alpha_T_f4 = float(np.array(p.alpha_T).flatten()[0])

    p_f4.update_specifications(
        {
            "alpha_T": [current_alpha_T_f4 + 0.010],
            "e": e_new_f4.tolist(),
        }
    )

    run_scenario("F4", p_f4, ctx)

    ##### F5 — IMF Fiscal Consolidation Constraint (-1.5% of GDP spending)
    # alpha_G -= 0.015; floored at 0.01 to prevent non-positive government
    # [Source: IMF Ethiopia Article IV Consultation 2024]
    p_f5 = copy.deepcopy(p)
    p_f5.baseline = False
    p_f5.output_base = f5_dir

    current_alpha_G_f5 = float(np.array(p.alpha_G).flatten()[0])
    p_f5.update_specifications(
        {"alpha_G": [max(current_alpha_G_f5 - 0.015, 0.01)]}
    )

    run_scenario("F5", p_f5, ctx)

    """
    ---------------------------------------------------------------------------
    DIMENSION 7 — Integrated Policy Package
    Shocks are multiplicatively composed: e_combined = e0 * prod(e_i / e0)
    ---------------------------------------------------------------------------
    """

    ##### I1 — Moderate Integrated Package (E2 + L2 + G2 + F2)
    # [Source: Ethiopian NPC Ten-Year Development Plan 2021-2030]
    p_i1 = copy.deepcopy(p)
    p_i1.baseline = False
    p_i1.output_base = i1_dir

    e0_i1 = np.array(p.e, dtype=float)
    e0_i1 = e0_i1[0] if e0_i1.ndim == 3 else e0_i1
    # Multiplicative composition of E2, L2, G2 efficiency shocks
    e_i1 = (
        e0_i1
        * (np.array(e_new_e2) / e0_i1)
        * (np.array(e_new_l2) / e0_i1)
        * (np.array(e_new_g2) / e0_i1)
    )
    current_alpha_G_i1 = float(np.array(p.alpha_G).flatten()[0])

    p_i1.update_specifications(
        {
            "e": e_i1.tolist(),
            "frisch": float(p.frisch) + 0.05,
            "alpha_G": [current_alpha_G_i1 + 0.020],
        }
    )

    run_scenario("I1", p_i1, ctx)

    ##### I2 — Ambitious Integrated Package (E3 + L3 + G3 + F2)
    # [Source: Ethiopian NPC Ten-Year Development Plan 2021-2030]
    p_i2 = copy.deepcopy(p)
    p_i2.baseline = False
    p_i2.output_base = i2_dir

    e0_i2 = np.array(p.e, dtype=float)
    e0_i2 = e0_i2[0] if e0_i2.ndim == 3 else e0_i2
    e_i2 = (
        e0_i2
        * (np.array(e_new_e3) / e0_i2)
        * (np.array(e_new_l3) / e0_i2)
        * (np.array(e_new_g3) / e0_i2)
    )
    current_alpha_G_i2 = float(np.array(p.alpha_G).flatten()[0])

    p_i2.update_specifications(
        {
            "e": e_i2.tolist(),
            "frisch": float(p.frisch) + 0.10,
            "alpha_G": [current_alpha_G_i2 + 0.020],
        }
    )

    run_scenario("I2", p_i2, ctx)

    ##### I3 — Maximum Dividend (E4 + L4 + G4 + M4)
    # All dimensions at full convergence — ceiling of the dividend
    # [Source: Ethiopian NPC Ten-Year Development Plan 2021-2030]
    p_i3 = copy.deepcopy(p)
    p_i3.baseline = False
    p_i3.output_base = i3_dir

    e0_i3 = np.array(p.e, dtype=float)
    e0_i3 = e0_i3[0] if e0_i3.ndim == 3 else e0_i3
    e_i3 = (
        e0_i3
        * (np.array(e_new_e4) / e0_i3)
        * (np.array(e_new_l4) / e0_i3)
        * (np.array(e_new_g4) / e0_i3)
        * (np.array(e_new_m4) / e0_i3)
    )
    current_zeta_K_i3 = float(np.array(p.zeta_K).flatten()[0])

    p_i3.update_specifications(
        {
            "e": e_i3.tolist(),
            "frisch": float(p.frisch) + 0.15,
            "zeta_K": [min(current_zeta_K_i3 + 0.10, 0.99)],
        }
    )

    run_scenario("I3", p_i3, ctx)

    ##### I4 — Delayed Action (same as I2 but reforms begin 2035, not 2025)
    # THE COST OF DELAY SCENARIO: baseline e for periods t=0..9 (2025-2034),
    # then I2 e for t>=10 (2035+). Direct override of time-varying e array.
    # [Source: DeBacker & Evans 2023; Ethiopian NPC 2021]
    p_i4 = copy.deepcopy(p)
    p_i4.baseline = False
    p_i4.output_base = i4_dir

    # Apply I2 scalar parameters first
    current_alpha_G_i4 = float(np.array(p.alpha_G).flatten()[0])
    p_i4.update_specifications(
        {
            "frisch": float(p.frisch) + 0.10,
            "alpha_G": [current_alpha_G_i4 + 0.020],
        }
    )
    # Build time-varying e: baseline for t<10, I2 for t>=10
    e_base_full = np.array(p.e, dtype=float)  # shape (T, S, J)
    T_i4 = e_base_full.shape[0]
    e_delayed = np.zeros_like(e_base_full)
    for t in range(T_i4):
        if t < 10:
            e_delayed[t] = e_base_full[t]  # no reform 2025-2034
        else:
            e_delayed[t] = e_i2  # reforms begin 2035
    p_i4.e = e_delayed  # direct override — time-varying, bypasses paramtools

    run_scenario("I4", p_i4, ctx)

    if client is not None:
        client.close()

    """
    ---------------------------------------------------------------------------
    Cross-scenario report + run summary

    Per-scenario CSVs and plots are written as each scenario finishes (inside
    run_scenario), so this final section only needs the cross-scenario
    comparison (Cost of Delay: I4 vs I2) plus the overall run summary.
    ---------------------------------------------------------------------------
    """
    # Cost of Delay: I4 vs I2 directly (only if both are solved and valid)
    i2_tpi, i2_params = load_outputs(i2_dir)
    i4_tpi, i4_params = load_outputs(i4_dir)
    if i2_tpi is not None and i4_tpi is not None:
        try:
            ans_cost_of_delay = ot.macro_table(
                i2_tpi,
                i2_params,
                reform_tpi=i4_tpi,
                reform_params=i4_params,
                var_list=ctx["var_list"],
                output_type="pct_diff",
                num_years=ctx["num_years"],
                start_year=ctx["start_year"],
            )
            ans_cost_of_delay.to_csv(
                os.path.join(save_dir, "results_cost_of_delay.csv")
            )
            print(
                "\n=== COST OF DELAY (I4 vs I2: reforms delayed 10 years) ==="
            )
            print(ans_cost_of_delay)
        except Exception:
            print("!!! Cost-of-delay table failed:")
            print(traceback.format_exc())
    else:
        print("Skipping cost-of-delay table: I2 and/or I4 not available.")

    # Run summary — status of every scenario this run
    print("\n================ RUN SUMMARY ================")
    for name, info in run_log.items():
        print(f"  {name:<10} {info['status']:<11} {info['seconds']:8.1f}s")
    failed = [n for n, i in run_log.items() if i["status"] == "failed"]
    if failed:
        print(f"\n{len(failed)} scenario(s) FAILED: {', '.join(failed)}")
        print("See the tracebacks above for the underlying cause of each.")
    else:
        print("\nAll scenarios are complete (freshly solved or resumed).")


if __name__ == "__main__":
    main()

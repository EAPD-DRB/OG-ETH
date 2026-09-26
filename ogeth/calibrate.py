from ogeth import macro_params, income
from ogeth import input_output as io
import os
import numpy as np
import pandas as pd
import datetime
import warnings

CUR_PATH = os.path.abspath(os.path.dirname(__file__))
# UN M49 code for Ethiopia, used for the UN population data
UN_COUNTRY_CODE = "231"
# Ethiopia's rows of the EAPD-DRB/Demographic-Gradients library: DHS
# wealth-quintile tilts for fertility and infant mortality (2024 survey) and
# the 2007 census household-deaths gradient for adult mortality by age band
GRADIENT_FILE = os.path.join(CUR_PATH, "data", "demographic_gradients_ETH.csv")
# the library's tilt is the change in the log rate from the bottom to the
# top of the wealth distribution; OG-Core's gradient is per centered
# percentile point
TILT_PER_PERCENTILE = 1 / 100
# the census bands from this age on measure higher mortality in wealthier
# households, which the library flags as at least partly a reporting
# artefact (the 15-59 summary is flat), so no tilt is applied there
OLDEST_MEASURED_MORTALITY_AGE = 45
# ages 1-4 take the under-five tilt; age 0 is handled by infmort_gradient
UNDER_FIVE_AGES = (1, 5)
# The adult-mortality gradient steepens as a country gets richer. The
# library's income rule (general_gradient.csv, fitted on 17 censuses between
# about $200 and $10,000 of GNI per head, r = -0.88) is
#     tilt(45q15) = 1.291 - 0.2443 ln(GNI per capita, current US$),
# and Ethiopia's census measurement is from 2007, when GNI per head was a
# fifth of today's. The measured tilts are therefore shifted by the rule's
# change since the census year, and keep shifting along the model's own
# per-capita growth, capped where the rule's fit ends.
INCOME_RULE_SLOPE = -0.2443
INCOME_RULE_MAX_GNI = 10000.0
# World Bank Atlas GNI per capita, current US$ (NY.GNP.PCAP.CD)
GNI_PER_CAPITA = {2007: 210.0, 2024: 1100.0}
CENSUS_YEAR = 2007
GNI_LATEST_YEAR = 2024
# the rule describes mortality between 15 and 60, so the shift is applied
# at those ages only
INCOME_RULE_AGES = (15, 60)


def measured_mortality_gradient(E, S, df):
    """
    The census adult-mortality tilts by single age, at the census year.

    Args:
        E (int): age at which agents become economically active
        S (int): number of model periods in a lifetime
        df (Pandas DataFrame): the library's Ethiopian rows

    Returns:
        mort (Numpy array): gradient by age, length E+S, on OG-Core's scale

    """
    ages = np.arange(E + S)
    mort = np.zeros(E + S)
    u5 = df[df.indicator == "U5MR"]
    if not u5.empty:
        mort[(ages >= UNDER_FIVE_AGES[0]) & (ages < UNDER_FIVE_AGES[1])] = (
            float(u5.slope.iloc[0]) * TILT_PER_PERCENTILE
        )
    bands = df[(df.indicator == "AMR") & (df.measure == "mx")]
    for row in bands.itertuples():
        if row.age_lo >= OLDEST_MEASURED_MORTALITY_AGE:
            continue
        sel = (ages >= row.age_lo) & (ages <= row.age_hi)
        mort[sel] = float(row.slope) * TILT_PER_PERCENTILE
    return mort


def mortality_gradient_path(mort, T, S, start_year, g_y_annual):
    """
    Spread the census-year mortality gradient over the model's time path,
    steepening it with income per head along the library's income rule.

    Args:
        mort (Numpy array): gradient by age at the census year, length E+S
        T (int): number of periods in the transition path
        S (int): number of model periods in a lifetime
        start_year (int): calendar year of the first model period
        g_y_annual (float): annual growth of income per head

    Returns:
        path (Numpy array): gradient by period and age, size (T+S, E+S)

    """
    years = start_year + np.arange(T + S)
    gni = GNI_PER_CAPITA[GNI_LATEST_YEAR] * (1 + g_y_annual) ** (
        years - GNI_LATEST_YEAR
    )
    gni = np.minimum(gni, INCOME_RULE_MAX_GNI)
    shift = (
        INCOME_RULE_SLOPE
        * np.log(gni / GNI_PER_CAPITA[CENSUS_YEAR])
        * TILT_PER_PERCENTILE
    )
    ages = np.arange(mort.shape[0])
    adult = (ages >= INCOME_RULE_AGES[0]) & (ages < INCOME_RULE_AGES[1])
    path = np.tile(mort, (T + S, 1))
    path[:, adult] += shift.reshape(-1, 1)
    return path


def demographic_gradients(
    E, S, T=None, start_year=None, g_y_annual=None, path=GRADIENT_FILE
):
    """
    Income gradients in fertility and mortality for OG-Core's demographics,
    read from the packaged Ethiopian rows of the Demographic-Gradients
    library and converted to OG-Core's per-percentile-point scale.

    Model periods are years, so the mortality gradient is built by single
    age from 0 to E+S-1. When T, start_year and g_y_annual are given it is
    also spread over the T+S periods of the population path, steepening
    with income per head; otherwise it is the census-year gradient.

    Args:
        E (int): age at which agents become economically active
        S (int): number of model periods in a lifetime
        T (int): number of periods in the transition path
        start_year (int): calendar year of the first model period
        g_y_annual (float): annual growth of income per head
        path (str): CSV with the library's rows for Ethiopia

    Returns:
        gradients (dict): fert_gradient and infmort_gradient (scalars) and
            mort_gradient (length E+S, or size (T+S, E+S) with a time
            path), ready for get_pop_objs

    """
    df = pd.read_csv(path)

    def tilt(indicator):
        rows = df[df.indicator == indicator]
        if rows.empty:
            raise ValueError(f"No {indicator} gradient in {path}")
        return float(rows.slope.iloc[0]) * TILT_PER_PERCENTILE

    mort = measured_mortality_gradient(E, S, df)
    if T is not None:
        mort = mortality_gradient_path(
            mort, int(T), S, int(start_year), float(g_y_annual)
        )
    return {
        "fert_gradient": tilt("TFR"),
        "infmort_gradient": tilt("IMR"),
        "mort_gradient": mort,
    }


# Steady-state matching: the largest relative gap accepted on every target,
# the damping of the bequest-weight update (its effect on wealth shares is
# less than one for one), and the number of solves allowed
MATCH_TOL = 0.02
MATCH_MAX_ITER = 15
# the discount factor by lifetime-income group is the instrument for the
# wealth shares (OG-USA's convention) and its level for the wealth-to-GDP
# anchor; a group's steady-state wealth is very elastic to its beta, so the
# update is heavily damped and each step bounded
BETA_DAMPING = 0.3
BETA_STEP = 1.03
BETA_BOUNDS = (0.5, 0.995)
# OG-USA's bequest weight, kept for every group
CHI_B_DEFAULT = 80.0
# no parameter moves by more than this factor between two solves (chi_n
# takes its full first-order step, which converges in a solve or two once
# the other parameters stop moving), and a solve that fails is retried from
# halfway back to the last solved point
MATCH_STEP_BOUNDS = (0.5, 2.0)
MATCH_RETRIES = 3


def steady_state_moments(ss, p, compliance_start, compliance_end):
    """
    The moments the steady-state matching works with, from a solved steady
    state.

    Args:
        ss (dict): output of ogcore.SS.run_SS
        p (OG-Core Specifications object): the parameters it was solved with
        compliance_start (Numpy array): FY2024/25 compliance by group
        compliance_end (Numpy array): long-run compliance by group

    Returns:
        moments (dict): n_model (labor supply by age), wealth_shares (by
            group), pension_outlays (share of GDP), pit_start (personal
            income tax in FY2024/25 as a share of GDP, approximated from
            the steady-state incidence)
    """
    from ogeth import income, labor

    omega = p.omega_SS
    Y = float(np.asarray(ss["Y"]).sum())
    inc = (np.asarray(ss["before_tax_income"]) * omega).sum(axis=0)
    pit_ss = float(np.asarray(ss["iit_revenue"]).sum()) / Y
    base_end = float((compliance_end * inc).sum())
    pit_start = (
        pit_ss * float((compliance_start * inc).sum()) / base_end
        if base_end > 0
        else 0.0
    )
    return {
        "n_model": labor.average_labor_supply(np.asarray(ss["n"]), omega),
        "wealth_ratio": float(np.asarray(ss["B"]).sum()) / Y,
        "wealth_shares": income.implied_wealth_shares(
            np.asarray(ss["b_s"]), omega
        ),
        "pension_outlays": float(np.asarray(ss["agg_pension_outlays"])) / Y,
        "pit_start": pit_start,
        "r": float(ss["r"]),
        "TR": float(ss["TR"]),
        "factor": float(ss["factor"]),
    }


def match_steady_state(
    p,
    client=None,
    max_iter=MATCH_MAX_ITER,
    tol=MATCH_TOL,
    verbose=True,
    checkpoint=None,
):
    """
    Calibrate together, by repeated steady-state solves, the parameters
    whose targets are steady-state moments: chi_n to LFMS hours by age,
    the discount factors beta_j to WID wealth shares by group and their
    level to the household-wealth anchor, the pension coverage scale to
    pension outlays as a share of GDP, and the compliance scale to
    personal-income-tax collections in the first period.

    Args:
        p (OG-Core Specifications object): model parameters
        client (Dask client object): client for parallel computation
        max_iter (int): maximum number of steady-state solves
        tol (float): largest relative gap accepted on every target
        verbose (bool): print the gaps after each solve
        checkpoint (callable): called after every solve with the
            parameters just solved and the moments, e.g. to save progress

    Returns:
        params (dict): the calibrated parameters, ready for the JSON
        history (list): one dict per solve with the moments and the values
            used
    """
    import copy

    from ogcore import SS

    from ogeth import income, labor

    p = copy.deepcopy(p)
    lambdas = np.asarray(p.lambdas).flatten()
    n_target = labor.labor_supply_target(p.E, p.S, p.ltilde)
    ages = income.model_ages(p.E, p.S)
    fit = (ages >= labor.FIT_AGES[0]) & (ages < labor.FIT_AGES[1])
    wealth_target = income.wealth_share_targets(lambdas)
    # a group at the floor is asked to hold less than a no-borrowing
    # household saves for retirement anyway, so it is not part of the fit
    wealth_fit = wealth_target > income.WEALTH_SHARE_FLOOR
    wealth_level_target = macro_params.INITIAL_WEALTH_RATIO

    def tie_floored(beta):
        # a group at the floor cannot reach its target however impatient it
        # is made, so it takes the discount factor of the nearest fitted group
        beta = beta.copy()
        fitted = np.flatnonzero(wealth_fit)
        for j in np.flatnonzero(~wealth_fit):
            beta[j] = beta[fitted[np.argmin(np.abs(fitted - j))]]
        return beta

    pension_target = (
        macro_params.PENSIONS_SHARE_OF_GDP
        / 100
        * macro_params.PENSION_OUTLAYS_SS_TO_START
    )
    pit_target = (
        macro_params.PIT_REVENUE_TARGET * macro_params.PIT_START_CORRECTION
    )
    state = {
        "chi_n": labor.steady_state_chi_n(p),
        "beta": np.asarray(p.beta_annual, dtype=float).flatten().copy(),
        # start from the scales the parameters already carry, so that a run
        # resumes from its own checkpoint rather than from the constants
        "compliance_scale": float(
            1 - np.asarray(p.labor_income_tax_noncompliance_rate)[0, -1]
        ),
        "pension_scale": float(
            np.asarray(p.replacement_rate_adjust)[0, -1]
            / macro_params.PENSION_COVERAGE[-1]
        ),
    }

    def as_params(s):
        return {
            "chi_n": s["chi_n"].tolist(),
            "beta_annual": s["beta"].tolist(),
            "chi_b": [CHI_B_DEFAULT] * len(s["beta"]),
            **macro_params.compliance_paths(
                macro_params.DEFAULT_SCENARIO,
                s["compliance_scale"],
                s["pension_scale"],
            ),
        }

    def halfway(new, old):
        # geometric midpoint: the updates are multiplicative
        return {
            k: np.sqrt(np.asarray(new[k]) * np.asarray(old[k]))
            if k != "compliance_scale"
            else min(1.0, float(np.sqrt(new[k] * old[k])))
            for k in new
        }

    history = []
    solved = None
    # per-group damping of the beta step: halved for a group whenever the
    # sign of its wealth-share gap flips between solves, because the share
    # of the most patient groups is very elastic to beta once beta(1 + r)
    # nears one and a fixed step overshoots and oscillates
    beta_damping = np.full(len(state["beta"]), BETA_DAMPING)
    prev_sign = None
    for iteration in range(max_iter):
        for attempt in range(MATCH_RETRIES + 1):
            p.update_specifications(as_params(state))
            try:
                ss = SS.run_SS(p, client=client)
                break
            except RuntimeError as exc:
                if solved is None or attempt == MATCH_RETRIES:
                    raise
                print(
                    f"steady state did not solve ({exc}); halving the step",
                    flush=True,
                )
                state = halfway(state, solved)
        paths = as_params(state)
        c_start = 1 - np.array(paths["labor_income_tax_noncompliance_rate"][0])
        c_end = 1 - np.array(paths["labor_income_tax_noncompliance_rate"][-1])
        m = steady_state_moments(ss, p, c_start, c_end)
        gaps = {
            # ages where chi_n sits at OG-Core's cap cannot be fitted
            "hours": np.abs(m["n_model"] / n_target - 1)[
                fit & (state["chi_n"] < labor.MAX_CHI_N)
            ].max(),
            "wealth": np.abs(m["wealth_shares"] / wealth_target - 1)[
                wealth_fit
            ].max(),
            "wealth_level": abs(m["wealth_ratio"] / wealth_level_target - 1),
            "pensions": abs(m["pension_outlays"] / pension_target - 1)
            if macro_params.PENSIONS_ON
            else 0.0,
            "pit": abs(m["pit_start"] / pit_target - 1),
        }
        solved = {
            k: (v.copy() if hasattr(v, "copy") else v)
            for k, v in state.items()
        }
        history.append({"iteration": iteration, "gaps": gaps, **solved, **m})
        if verbose:
            print(
                f"match iteration {iteration}: gaps "
                + ", ".join(f"{k} {v:.3f}" for k, v in gaps.items())
                + f"; r {m['r']:.4f}, wealth shares "
                + np.array2string(m["wealth_shares"], precision=3)
                + f", B/Y {m['wealth_ratio']:.3f}, beta "
                + np.array2string(state["beta"], precision=4)
                + f", pension outlays {m['pension_outlays']:.4f}, "
                f"PIT t0 {m['pit_start']:.4f}, compliance scale "
                f"{state['compliance_scale']:.3f}, pension scale "
                f"{state['pension_scale']:.3f}",
                flush=True,
            )
        if checkpoint is not None:
            checkpoint(as_params(solved), m)
        if max(gaps.values()) < tol:
            break
        lo, hi = MATCH_STEP_BOUNDS
        sign = np.sign(wealth_target - m["wealth_shares"])
        if prev_sign is not None:
            beta_damping = np.where(
                sign * prev_sign < 0, beta_damping / 2, beta_damping
            )
        prev_sign = sign
        step = BETA_STEP ** (beta_damping / BETA_DAMPING)
        share_ratio = np.clip(
            (wealth_target / m["wealth_shares"]) ** beta_damping,
            1 / step,
            step,
        )
        level_ratio = np.clip(
            (wealth_level_target / m["wealth_ratio"]) ** BETA_DAMPING,
            1 / BETA_STEP,
            BETA_STEP,
        )
        state = {
            "chi_n": labor.chi_n_step(
                state["chi_n"], m["n_model"], n_target, p
            ),
            "beta": tie_floored(
                np.clip(
                    state["beta"] * share_ratio * level_ratio, *BETA_BOUNDS
                )
            ),
            "compliance_scale": min(
                1.0,
                state["compliance_scale"]
                * np.clip(pit_target / m["pit_start"], lo, hi),
            )
            if m["pit_start"] > 0
            else state["compliance_scale"],
            "pension_scale": state["pension_scale"]
            * np.clip(pension_target / m["pension_outlays"], lo, hi)
            if macro_params.PENSIONS_ON and m["pension_outlays"] > 0
            else state["pension_scale"],
        }
        p.update_specifications(
            {
                "initial_guess_r_SS": labor.R_GUESS_MARGIN * m["r"],
                "initial_guess_TR_SS": m["TR"],
                "initial_guess_factor_SS": labor.factor_guess(m["factor"]),
            }
        )
    else:
        print(
            f"steady-state matching did not converge in {max_iter} solves; "
            "keeping the last solved values",
            flush=True,
        )
    last = history[-1]
    params = as_params(solved)
    params.update(
        {
            "initial_guess_r_SS": round(labor.R_GUESS_MARGIN * last["r"], 4),
            "initial_guess_TR_SS": round(last["TR"], 5),
            "initial_guess_factor_SS": round(
                labor.factor_guess(last["factor"]), 0
            ),
            "compliance_scale": solved["compliance_scale"],
            "pension_coverage_scale": solved["pension_scale"],
        }
    )
    return params, history


def main():
    """
    Run the steady-state matching on the packaged parameters and write the
    result into the packaged JSON; the two calibrated scales are printed so
    that macro_params.COMPLIANCE_SCALE and PENSION_COVERAGE_SCALE can be
    set to them.
    """
    import json
    import multiprocessing

    from distributed import Client
    from ogcore.parameters import Specifications

    from ogeth import income

    json_path = os.path.join(CUR_PATH, "ogeth_default_parameters.json")
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    p = Specifications(baseline=True, num_workers=num_workers)
    with open(json_path, encoding="utf-8") as f:
        p.update_specifications(json.load(f))

    def save(params, moments):
        income.write_json_parameters(json_path, params)

    params, history = match_steady_state(p, client=client, checkpoint=save)
    client.close()
    scales = {
        k: params.pop(k)
        for k in ("compliance_scale", "pension_coverage_scale")
    }
    print("calibrated scales:", scales)
    print(
        "beta_annual by group:",
        np.array2string(np.asarray(params["beta_annual"]), precision=4),
    )
    income.write_json_parameters(json_path, params)
    print(f"wrote the matched parameters to {json_path}")


class Calibration:
    """OG-ETH calibration class"""

    def __init__(
        self,
        p,
        macro_data_start_year=datetime.datetime(1947, 1, 1),
        macro_data_end_year=datetime.datetime(2024, 12, 31),
        demographic_data_path=None,
        output_path=None,
        # Set True to update from World Bank and UN APIs
        update_from_api=False,
    ):
        """
        Constructor for the Calibration class.

        Args:
            p (OG-Core Specifications object): model parameters
            demographic_data_path (str): path to save demographic data
            output_path (str): path to save output to
            update_from_api (bool): Set True to pull updated macro data
                from World Bank and UN APIs

        Returns:
            None

        """
        # Create output_path if it doesn't exist
        if output_path is not None:
            if not os.path.exists(output_path):
                os.makedirs(output_path)

        # Initialize attributes — populated only when update succeeds
        self.macro_params = {}
        self.demographic_params = {}
        self.e = None
        self.alpha_c = np.array([1.0]) if p.I == 1 else None
        self.io_matrix = np.array([[1.0]]) if p.M == 1 else None

        if not update_from_api:
            return

        # --- Online path: try each source independently ---

        # Macro estimation
        try:
            self.macro_params = macro_params.get_macro_params(
                macro_data_start_year,
                macro_data_end_year,
                update_from_api=update_from_api,
            )
        except Exception as exc:
            warnings.warn(f"Macro params update failed: {exc}", stacklevel=2)

        # io matrix and alpha_c (multi-sector only)
        if p.I > 1:
            try:
                alpha_c_dict = io.get_alpha_c()
                assert p.I == len(list(alpha_c_dict.keys()))
                self.alpha_c = np.array(list(alpha_c_dict.values()))
            except Exception as exc:
                warnings.warn(f"alpha_c update failed: {exc}", stacklevel=2)
        if p.M > 1:
            try:
                io_df = io.get_io_matrix()
                assert p.M == len(list(io_df.keys()))
                self.io_matrix = io_df.values
            except Exception as exc:
                warnings.warn(f"io_matrix update failed: {exc}", stacklevel=2)

        # Demographics + income (atomic — e depends on demographic output)
        try:
            self.update_demographics(p, demographic_data_path, output_path)
        except Exception as exc:
            warnings.warn(
                f"Demographics/income update failed: {exc}", stacklevel=2
            )
            self.demographic_params = {}
            self.e = None

    def update_demographics(
        self, p, demographic_data_path=None, output_path=None
    ):
        """
        Rebuild the demographics from the UN data, with Ethiopia's income
        gradients in fertility and mortality, and everything derived from
        them: the earnings matrix, the remittance growth path and
        allocation, and the transfer allocation.

        Args:
            p (OG-Core Specifications object): model parameters
            demographic_data_path (str): path to save demographic data
            output_path (str): path to save plots to

        Returns:
            None

        """
        from ogcore import demographics

        self.demographic_params = demographics.get_pop_objs(
            p.E,
            p.S,
            p.T,
            0,
            99,
            country_id=UN_COUNTRY_CODE,
            initial_data_year=p.start_year - 1,
            final_data_year=p.start_year + 1,
            income_percentiles=p.lambdas.flatten(),
            GraphDiag=False,
            download_path=demographic_data_path,
            **demographic_gradients(p.E, p.S, p.T, p.start_year, p.g_y_annual),
        )

        # earnings profiles, reshaped with Ethiopian data and scaled on
        # the model's own joint age-by-group population distribution
        self.e = income.get_e_interp(
            p.E,
            p.S,
            p.J,
            p.lambdas,
            self.demographic_params["omega_SS"],
            plot_path=output_path,
        )

        # the remittance growth path and allocation matrix are derived
        # from these demographics, so they travel with them
        self.demographic_params.update(
            macro_params.derive_remittance_params(
                p.g_y,
                self.demographic_params["g_n"],
                self.demographic_params["omega_SS"],
                p.lambdas,
            )
        )
        # so is the transfer allocation matrix (per capita within the
        # targeted groups, pensions to the retired)
        retire_idx = int(np.asarray(p.retirement_age).flatten()[0]) - int(p.E)
        self.demographic_params["eta"] = macro_params.transfer_eta(
            self.demographic_params["omega_SS"], p.lambdas, retire_idx
        ).tolist()

    # method to return all newly calibrated parameters in a dictionary
    def get_dict(self):
        d = {}
        d.update(self.macro_params)
        d.update(self.demographic_params)
        if self.e is not None:
            d["e"] = self.e
        if self.alpha_c is not None:
            d["alpha_c"] = self.alpha_c
        if self.io_matrix is not None:
            d["io_matrix"] = self.io_matrix
        return d


if __name__ == "__main__":
    main()

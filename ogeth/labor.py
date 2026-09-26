"""
Labor supply targets and the chi_n calibration for OG-ETH.

chi_n, the age profile of the disutility of labor, is calibrated so that
the model's average labor supply by age matches hours worked per person
in Ethiopia's 2021 Labour Force and Migration Survey (LFMS). The
calibration solves the steady state repeatedly, rescaling chi_n between
solves by the ratio of marginal disutilities at the model's and the
data's labor supply, which is the exact adjustment when consumption and
prices are held fixed.
"""

import copy
import json
import os

import numpy as np
import pandas as pd
from ogcore import SS, household

from ogeth import income

CUR_PATH = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(CUR_PATH, "data")

LFMS_YEAR = 2021
# OG-USA's convention: labor supply is the share of a 16-hour waking day,
# seven days a week
WEEKLY_TIME_ENDOWMENT = (24 - 8) * 7
# LFMS five-year bands placed at their midpoint; the open 65+ band at 67
HOURS_BAND_MIDPOINTS = {
    "10-14": 12,
    "15-19": 17,
    "20-24": 22,
    "25-29": 27,
    "30-34": 32,
    "35-39": 37,
    "40-44": 42,
    "45-49": 47,
    "50-54": 52,
    "55-59": 57,
    "60-64": 62,
    "65+": 67,
}
# beyond the survey's last band the target tapers with the NTA per-capita
# labor income profile, and never below this share of the time endowment
OLDEST_SURVEY_AGE = 67
MIN_LABOR_SUPPLY = 0.02
# ages over which the fit is judged; older households supply little labor
# and their targets are extrapolated
FIT_AGES = (20, 80)
DEFAULT_MAX_ITER = 10
DEFAULT_TOL = 0.02
# the steady-state solver needs its interest-rate guess above the solution
R_GUESS_MARGIN = 1.3
# OG-Core caps the factor guess at this value; the solver's own sweep over
# the guess covers the rest
MAX_FACTOR_GUESS = 500000.0
# OG-Core's upper bound on chi_n; it binds only at the oldest ages, where
# the target is an extrapolation and little labor is supplied anyway
MAX_CHI_N = 10000.0


def factor_guess(factor):
    """
    A factor guess OG-Core accepts, from a solved factor.

    Args:
        factor (float): solved steady-state factor

    Returns:
        guess (float): the factor, capped at MAX_FACTOR_GUESS

    """
    return float(min(factor, MAX_FACTOR_GUESS))


def hours_per_person():
    """
    LFMS 2021 hours worked per week per person by age band: the
    employment-to-population ratio times the mean weekly hours of the
    employed.

    Returns:
        df (Pandas DataFrame): age_band, emp_pop_ratio,
            mean_weekly_hours_employed, hours_per_person

    """
    df = pd.read_csv(os.path.join(DATA_DIR, "lfms2021_hours_by_age.csv"))
    df["hours_per_person"] = df.emp_pop_ratio * df.mean_weekly_hours_employed
    return df


def labor_supply_target(E, S, ltilde=1.0):
    """
    Average labor supply by model age, as a share of the time endowment,
    from LFMS hours per person.

    Args:
        E (int): age at which agents become economically active
        S (int): number of model periods in a lifetime
        ltilde (float): time endowment per period

    Returns:
        target (Numpy array): average labor supply by age, length S

    """
    ages = income.model_ages(E, S)
    df = hours_per_person()
    x = df.age_band.map(HOURS_BAND_MIDPOINTS).to_numpy(dtype=float)
    y = df.hours_per_person.to_numpy() / WEEKLY_TIME_ENDOWMENT * ltilde
    order = np.argsort(x)
    x, y = x[order], y[order]
    target = np.interp(ages, x, y)
    old = ages > OLDEST_SURVEY_AGE
    if old.any():
        nta = income.nta_labor_income(
            "ETH", np.concatenate(([OLDEST_SURVEY_AGE], ages[old]))
        )
        target[old] = np.interp(OLDEST_SURVEY_AGE, x, y) * nta[1:] / nta[0]
    return np.maximum(target, MIN_LABOR_SUPPLY * ltilde)


def average_labor_supply(n, omega_SS):
    """
    Population-weighted average labor supply by age.

    Args:
        n (Numpy array): labor supply by age and group, size (S, J)
        omega_SS (Numpy array): joint population distribution, size (S, J)

    Returns:
        n_avg (Numpy array): average labor supply by age, length S

    """
    return (n * omega_SS).sum(axis=1) / omega_SS.sum(axis=1)


def marginal_disutility(n, p):
    """
    Marginal disutility of labor with unit weights, from OG-Core's
    elliptical utility function.

    Args:
        n (Numpy array): labor supply, length S
        p (OG-Core Specifications object): model parameters

    Returns:
        mdu (Numpy array): marginal disutility at each labor supply

    """
    n = np.asarray(n, dtype=float)
    return household.marg_ut_labor(n, np.ones_like(n), p)


def chi_n_step(chi_n, n_model, n_target, p):
    """
    Rescale chi_n so that, at fixed consumption and prices, the labor
    supply first-order condition holds at the target instead of the model
    value.

    Args:
        chi_n (Numpy array): current disutility weights, length S
        n_model (Numpy array): model average labor supply, length S
        n_target (Numpy array): target average labor supply, length S
        p (OG-Core Specifications object): model parameters

    Returns:
        chi_n_new (Numpy array): updated disutility weights, length S

    """
    return np.minimum(
        chi_n
        * marginal_disutility(n_model, p)
        / marginal_disutility(n_target, p),
        MAX_CHI_N,
    )


def steady_state_chi_n(p):
    """
    The steady-state row of chi_n, whatever its stored shape.

    Args:
        p (OG-Core Specifications object): model parameters

    Returns:
        chi_n (Numpy array): disutility weights by age, length S

    """
    chi_n = np.asarray(p.chi_n, dtype=float)
    if chi_n.ndim == 2:
        chi_n = chi_n[-1]
    return chi_n.copy()


def estimate_chi_n(
    p,
    client=None,
    max_iter=DEFAULT_MAX_ITER,
    tol=DEFAULT_TOL,
    verbose=True,
):
    """
    Calibrate chi_n to the LFMS labor supply profile by repeated
    steady-state solves.

    Args:
        p (OG-Core Specifications object): model parameters
        client (Dask client object): client for parallel computation
        max_iter (int): maximum number of steady-state solves
        tol (float): largest acceptable relative gap between model and
            target labor supply over FIT_AGES
        verbose (bool): print the gap after each solve

    Returns:
        chi_n (Numpy array): calibrated disutility weights, length S
        target (Numpy array): target labor supply by age, length S
        history (list): one dict per solve with the chi_n used, the model
            labor supply, the largest gap and the solved r, TR and factor

    """
    p = copy.deepcopy(p)
    target = labor_supply_target(p.E, p.S, p.ltilde)
    ages = income.model_ages(p.E, p.S)
    fit = (ages >= FIT_AGES[0]) & (ages < FIT_AGES[1])
    chi_n = steady_state_chi_n(p)
    history = []
    for iteration in range(max_iter):
        ss = SS.run_SS(p, client=client)
        n_model = average_labor_supply(ss["n"], p.omega_SS)
        # ages where chi_n sits at OG-Core's cap cannot be fitted
        gap = np.abs(n_model / target - 1)[fit & (chi_n < MAX_CHI_N)].max()
        history.append(
            {
                "iteration": iteration,
                "chi_n": chi_n.copy(),
                "n_model": n_model,
                "max_gap": gap,
                "r": float(ss["r"]),
                "TR": float(ss["TR"]),
                "factor": float(ss["factor"]),
            }
        )
        if verbose:
            print(
                f"chi_n iteration {iteration}: largest relative gap "
                f"{gap:.3f}, r {ss['r']:.4f}, factor {ss['factor']:.0f}"
            )
        if gap < tol:
            break
        chi_n = chi_n_step(chi_n, n_model, target, p)
        p.update_specifications(
            {
                "chi_n": chi_n.tolist(),
                "initial_guess_r_SS": R_GUESS_MARGIN * float(ss["r"]),
                "initial_guess_TR_SS": float(ss["TR"]),
                "initial_guess_factor_SS": factor_guess(ss["factor"]),
            }
        )
    else:
        print(
            f"chi_n did not converge in {max_iter} solves; keeping the "
            "last solved profile"
        )
        chi_n = history[-1]["chi_n"]
    return chi_n, target, history


def fit_table(target, n_model, E, S):
    """
    Model and target labor supply averaged over the LFMS age bands.

    Args:
        target (Numpy array): target labor supply by age, length S
        n_model (Numpy array): model labor supply by age, length S
        E (int): age at which agents become economically active
        S (int): number of model periods in a lifetime

    Returns:
        df (Pandas DataFrame): age_band, target, model, both as weekly
            hours per person and as shares of the time endowment

    """
    ages = income.model_ages(E, S)
    rows = []
    bands = [(20, 25), (25, 30), (30, 35), (35, 40), (40, 45), (45, 50)]
    bands += [(50, 55), (55, 60), (60, 65), (65, 70), (70, 80), (80, 100)]
    for lo, hi in bands:
        sel = (ages >= lo) & (ages < hi)
        rows.append(
            {
                "age_band": f"{lo}-{hi - 1}",
                "target": target[sel].mean(),
                "model": n_model[sel].mean(),
                "target_hours": target[sel].mean() * WEEKLY_TIME_ENDOWMENT,
                "model_hours": n_model[sel].mean() * WEEKLY_TIME_ENDOWMENT,
            }
        )
    return pd.DataFrame(rows)


def main():
    """
    Calibrate chi_n on the packaged parameters and write it, with the
    steady-state guesses of the last solve, back into the packaged JSON.
    """
    import multiprocessing

    from distributed import Client
    from ogcore.parameters import Specifications

    json_path = os.path.join(CUR_PATH, "ogeth_default_parameters.json")
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    p = Specifications(baseline=True, num_workers=num_workers)
    with open(json_path, encoding="utf-8") as f:
        p.update_specifications(json.load(f))
    chi_n, target, history = estimate_chi_n(p, client=client)
    client.close()
    last = history[-1]
    print(fit_table(target, last["n_model"], p.E, p.S).round(3).to_string())
    income.write_json_parameters(
        json_path,
        {
            "chi_n": chi_n.tolist(),
            "initial_guess_r_SS": round(R_GUESS_MARGIN * last["r"], 4),
            "initial_guess_TR_SS": round(last["TR"], 5),
            "initial_guess_factor_SS": round(factor_guess(last["factor"]), 0),
        },
    )
    print(f"wrote chi_n to {json_path}")


if __name__ == "__main__":
    main()

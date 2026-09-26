"""
Lifetime earnings profiles for OG-ETH.

The ability matrix e starts from the OG-USA profiles, which are estimated
on US micro data, and is reshaped with Ethiopian data along its two
dimensions: over age with the National Transfer Accounts (NTA) labor
income profile per worker, as an Ethiopia-to-United-States ratio; and
across lifetime-income groups so that the income shares the matrix
implies equal the World Inequality Database (WID) pre-tax income shares
for Ethiopia. A caller can pass other target shares, or a single Gini
coefficient to tilt the groups to instead.
"""

import json
import os
import urllib.request

import numpy as np
import pandas as pd
import scipy.interpolate as si
import scipy.optimize as opt
from ogcore import parameter_plots as pp
from ogcore import utils

CUR_PATH = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(CUR_PATH, "data")
OGUSA_PARAMS_URL = (
    "https://raw.githubusercontent.com/PSLmodels/OG-USA/master/"
    "ogusa/ogusa_default_parameters.json"
)
# the OG-USA profiles cover ages 20 to 99 in one-year steps
OGUSA_E = 20
OGUSA_S = 80

# WID pre-tax national income (equal-split adults), the latest year with
# an Ethiopian estimate; the same year is used for the United States
WID_YEAR = 2021
WID_SHARE_VARIABLE = "sptincj992"
WID_GINI_VARIABLE = "gptincj992"
# WID net personal wealth shares (equal-split adults), the target for the
# distribution of wealth across the groups; the bottom quarter's share is
# negative in the data, which the model's no-borrowing households cannot
# reproduce, hence the floor
WID_WEALTH_VARIABLE = "shwealj992"
WEALTH_SHARE_FLOOR = 0.005
# NTA labor income per capita: Ethiopia's only profile is 2005, and 2006
# is the US profile closest to it
NTA_YEAR = {"ETH": 2005, "US": 2006}
# ILOSTAT employment ratios come in five-year bands, placed at the band
# midpoint; the open 65+ band is placed at 70
EMPLOYMENT_BAND_MIDPOINTS = {
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
    "65+": 70,
}
# window over which the two per-worker profiles are normalized before
# taking their ratio
REFERENCE_AGES = (20, 65)
# beyond 65 the employment ratio is a single open band in both countries,
# so per-worker earnings cannot be measured by age; the age factor is held
# at its 60-64 mean from this age on
OLDEST_MEASURED_AGE = 65


def load_ogusa_e():
    """
    Download the OG-USA default parameters and return its ability matrix.

    Returns:
        e_usa (Numpy array): OG-USA ability matrix, size (80, 10)
        lambdas_usa (Numpy array): OG-USA lifetime-income group shares

    """
    with urllib.request.urlopen(OGUSA_PARAMS_URL) as response:
        usa = json.load(response)
    e_usa = np.asarray(usa["e"], dtype=float)
    if e_usa.ndim == 3:
        e_usa = e_usa[0]
    return e_usa, np.asarray(usa["lambdas"], dtype=float)


def group_midpoints(lambdas):
    """
    Percentile midpoints of the lifetime-income groups.

    Args:
        lambdas (Numpy array): population share of each group, length J

    Returns:
        midpoints (Numpy array): midpoint of each group in (0, 1)

    """
    upper = np.cumsum(lambdas)
    return upper - 0.5 * np.asarray(lambdas)


def model_ages(E, S):
    """
    Midpoint age of each model period.

    Args:
        E (int): age at which agents become economically active
        S (int): number of model periods in a lifetime

    Returns:
        ages (Numpy array): midpoint age of each period, length S

    """
    step = OGUSA_S / S
    return np.linspace(E + 0.5 * step, E + S - 0.5 * step, S)


def interpolate_usa_e(e_usa, lambdas_usa, E, S, lambdas):
    """
    Map the OG-USA ability matrix onto the model's age and group grid.

    Args:
        e_usa (Numpy array): OG-USA ability matrix, size (80, 10)
        lambdas_usa (Numpy array): OG-USA group shares, length 10
        E (int): age at which agents become economically active
        S (int): number of model periods in a lifetime
        lambdas (Numpy array): model group shares, length J

    Returns:
        e_base (Numpy array): OG-USA profiles on the model grid, size (S, J)

    """
    lambdas = np.asarray(lambdas, dtype=float)
    if (
        S == OGUSA_S
        and E == OGUSA_E
        and lambdas.shape == lambdas_usa.shape
        and np.allclose(lambdas, lambdas_usa)
    ):
        return e_usa.copy()
    midp = group_midpoints(lambdas)
    midp_usa = group_midpoints(lambdas_usa)
    if midp.min() < midp_usa.min() or midp.max() > midp_usa.max():
        raise RuntimeError(
            "One or more entries in abilities vector (lambdas) is outside "
            "the allowable bounds for interpolation."
        )
    ages_usa = model_ages(OGUSA_E, OGUSA_S)
    j_mesh, s_mesh = np.meshgrid(midp_usa, ages_usa)
    points = np.column_stack((s_mesh.ravel(), j_mesh.ravel()))
    new_j_mesh, new_s_mesh = np.meshgrid(midp, model_ages(E, S))
    return si.griddata(
        points, e_usa.ravel(), (new_s_mesh, new_j_mesh), method="linear"
    )


def employment_ratio(country, year, ages):
    """
    ILOSTAT employment-to-population ratio interpolated to single ages.

    Args:
        country (str): "ETH" or "US"
        year (int): data year
        ages (Numpy array): ages to interpolate to

    Returns:
        ratio (Numpy array): employed share of the population at each age

    """
    df = pd.read_csv(
        os.path.join(DATA_DIR, "ilostat_employment_ratio_by_age.csv")
    )
    df = df[(df.country == country) & (df.year == year)]
    if df.empty:
        raise ValueError(f"No ILOSTAT employment ratio for {country} {year}")
    x = df.age_band.map(EMPLOYMENT_BAND_MIDPOINTS).to_numpy(dtype=float)
    order = np.argsort(x)
    return np.interp(ages, x[order], df.emp_pop_ratio.to_numpy()[order])


def nta_labor_income(country, ages):
    """
    NTA smoothed mean labor income per capita interpolated to single ages.

    Ages beyond the last reported age take its value.

    Args:
        country (str): "ETH" or "US"
        ages (Numpy array): ages to interpolate to

    Returns:
        income (Numpy array): labor income per capita at each age

    """
    df = pd.read_csv(os.path.join(DATA_DIR, "nta_labor_income_by_age.csv"))
    df = df[(df.country == country) & (df.year == NTA_YEAR[country])]
    if df.empty:
        raise ValueError(f"No NTA labor income profile for {country}")
    df = df.sort_values("age")
    return np.interp(
        ages, df.age.to_numpy(dtype=float), df.labor_income.to_numpy()
    )


def per_worker_earnings(country, ages):
    """
    Labor income per worker by age: the NTA per-capita profile divided by
    the employment ratio of the same year.

    Args:
        country (str): "ETH" or "US"
        ages (Numpy array): ages to evaluate at

    Returns:
        earnings (Numpy array): labor income per employed person by age

    """
    return nta_labor_income(country, ages) / employment_ratio(
        country, NTA_YEAR[country], ages
    )


def earnings_age_factor(ages):
    """
    Ethiopia-to-US ratio of per-worker labor income by age.

    Each country's profile is normalized to its mean over REFERENCE_AGES
    before the ratio is taken, so the factor reshapes the age profile
    without changing its level. From OLDEST_MEASURED_AGE on the factor is
    held at its mean over the five preceding ages, because the employment
    ratios that turn per-capita into per-worker income are a single open
    band beyond 65.

    Args:
        ages (Numpy array): model ages, length S

    Returns:
        factor (Numpy array): multiplicative age factor, length S

    """
    ages = np.asarray(ages, dtype=float)
    ref = (ages >= REFERENCE_AGES[0]) & (ages < REFERENCE_AGES[1])
    eth = per_worker_earnings("ETH", ages)
    usa = per_worker_earnings("US", ages)
    factor = (eth / eth[ref].mean()) / (usa / usa[ref].mean())
    old = ages >= OLDEST_MEASURED_AGE
    hold = (ages >= OLDEST_MEASURED_AGE - 5) & ~old
    if old.any() and hold.any():
        factor[old] = factor[hold].mean()
    return factor


def wid_cumulative_shares(country, variable=WID_SHARE_VARIABLE):
    """
    Cumulative shares at the percentile bounds WID reports.

    Args:
        country (str): "ETH" or "US"
        variable (str): WID series, pre-tax income shares by default or
            WID_WEALTH_VARIABLE for net personal wealth

    Returns:
        cumulative (dict): share received by the bottom fraction of adults,
            keyed by that fraction (0.25, 0.5, 0.7, 0.8, 0.9, 0.99 and 1.0)

    """
    df = pd.read_csv(os.path.join(DATA_DIR, "wid_pretax_income_2021.csv"))
    df = df[
        (df.country == country)
        & (df.year == WID_YEAR)
        & (df.variable == variable)
    ]
    if df.empty:
        raise ValueError(f"No WID {variable} shares for {country}")
    s = df.set_index("percentile").value
    bottom_70 = s["p0p50"] + s["p50p90"] - s["p70p80"] - s["p80p90"]
    return {
        0.25: s["p0p25"],
        0.50: s["p0p50"],
        0.70: bottom_70,
        0.80: bottom_70 + s["p70p80"],
        0.90: s["p0p50"] + s["p50p90"],
        0.99: s["p0p50"] + s["p50p90"] + s["p90p100"] - s["p99p100"],
        1.00: 1.0,
    }


def wid_group_shares(country, lambdas, variable=WID_SHARE_VARIABLE):
    """
    WID share of each lifetime-income group, of pre-tax income by default.

    Args:
        country (str): "ETH" or "US"
        lambdas (Numpy array): population share of each group, length J
        variable (str): WID series (see wid_cumulative_shares)

    Returns:
        shares (Numpy array): share of each group, length J

    """
    cumulative = wid_cumulative_shares(country, variable)
    bounds = np.round(np.cumsum(lambdas), 4)
    missing = [b for b in bounds if b not in cumulative]
    if missing:
        raise ValueError(
            "WID shares are available at the cumulative percentiles "
            f"{sorted(cumulative)}; lambdas imply {list(bounds)}"
        )
    cum_shares = np.array([cumulative[b] for b in bounds])
    return np.diff(np.concatenate(([0.0], cum_shares)))


def wid_gini(country):
    """
    WID pre-tax income Gini coefficient.

    Args:
        country (str): "ETH" or "US"

    Returns:
        gini (float): Gini coefficient in (0, 1)

    """
    df = pd.read_csv(os.path.join(DATA_DIR, "wid_pretax_income_2021.csv"))
    df = df[
        (df.country == country)
        & (df.year == WID_YEAR)
        & (df.variable == WID_GINI_VARIABLE)
    ]
    return float(df.value.iloc[0])


def wealth_share_targets(lambdas, country="ETH", floor=WEALTH_SHARE_FLOOR):
    """
    Target share of household wealth for each lifetime-income group, from
    WID's net personal wealth shares. Households in the model cannot borrow,
    so a group whose WID share is negative or below the floor is given the
    floor and the rest is rescaled to sum to one.

    Args:
        lambdas (Numpy array): population share of each group, length J
        country (str): "ETH" or "US"
        floor (float): smallest share any group is asked to hold

    Returns:
        shares (Numpy array): target wealth share of each group, length J

    """
    shares = wid_group_shares(country, lambdas, WID_WEALTH_VARIABLE)
    low = shares < floor
    shares = shares.copy()
    shares[low] = floor
    shares[~low] *= (1.0 - floor * low.sum()) / shares[~low].sum()
    return shares


def implied_wealth_shares(b, age_wgts):
    """
    Share of aggregate household wealth held by each group.

    Args:
        b (Numpy array): savings by age and group, size (S, J)
        age_wgts (Numpy array): joint population distribution, size (S, J)

    Returns:
        shares (Numpy array): wealth share of each group, length J

    """
    wealth = np.asarray(b) * np.asarray(age_wgts)
    return wealth.sum(axis=0) / wealth.sum()


def implied_group_shares(e, age_wgts):
    """
    Share of total ability-weighted labor accruing to each group when
    every household supplies the same labor.

    Args:
        e (Numpy array): ability matrix, size (S, J)
        age_wgts (Numpy array): joint population distribution, size (S, J)

    Returns:
        shares (Numpy array): implied income share of each group, length J

    """
    income = e * age_wgts
    return income.sum(axis=0) / income.sum()


def implied_gini(e, age_wgts, lambdas):
    """
    Gini coefficient of the ability matrix over the population.

    Args:
        e (Numpy array): ability matrix, size (S, J)
        age_wgts (Numpy array): joint population distribution, size (S, J)
        lambdas (Numpy array): population share of each group, length J

    Returns:
        gini (float): Gini coefficient in (0, 1)

    """
    S, J = e.shape
    return utils.Inequality(e, age_wgts, np.asarray(lambdas), S, J).gini()


def scale_groups_to_shares(e, age_wgts, group_shares):
    """
    Rescale each lifetime-income group's profile so that the income shares
    implied by the matrix equal the target shares.

    Args:
        e (Numpy array): ability matrix, size (S, J)
        age_wgts (Numpy array): joint population distribution, size (S, J)
        group_shares (Numpy array): target income share of each group,
            length J; they are normalized to sum to one

    Returns:
        e_scaled (Numpy array): rescaled ability matrix, size (S, J)

    """
    target = np.asarray(group_shares, dtype=float).flatten()
    if target.shape[0] != e.shape[1] or (target <= 0).any():
        raise ValueError("group_shares must be J positive income shares")
    target = target / target.sum()
    scale = target / implied_group_shares(e, age_wgts)
    return e * scale.reshape(1, -1)


def tilt_to_gini(e, age_wgts, lambdas, gini_to_match):
    """
    Tilt the matrix, e * exp(a * e), so that its Gini coefficient over the
    population equals the target. The tilt keeps every profile's shape
    over age and stretches or compresses the gaps between groups.

    Args:
        e (Numpy array): ability matrix, size (S, J)
        age_wgts (Numpy array): joint population distribution, size (S, J)
        lambdas (Numpy array): population share of each group, length J
        gini_to_match (float): target Gini coefficient, in (0, 1) or in
            percent

    Returns:
        e_tilted (Numpy array): tilted ability matrix, size (S, J)

    """
    gini = float(gini_to_match)
    if gini > 1:
        gini = gini / 100
    if not 0 < gini < 1:
        raise ValueError("gini_to_match must be between 0 and 1")

    def gap(a):
        return implied_gini(e * np.exp(a * e), age_wgts, lambdas) - gini

    # the tilt is measured against the largest ability so that the bracket
    # means the same thing whatever the scale of e; widen it until the
    # target is straddled
    scale = 1.0 / float(np.max(e))
    for width in (1.0, 2.0, 4.0, 8.0):
        lo, hi = -width * scale, width * scale
        if gap(lo) < 0 < gap(hi):
            sol = opt.root_scalar(
                gap, bracket=[lo, hi], method="bisect", xtol=1e-12
            )
            return e * np.exp(sol.root * e)
    raise ValueError(f"cannot tilt the ability matrix to a Gini of {gini}")


def get_e_interp(
    E,
    S,
    J,
    lambdas,
    age_wgts,
    group_shares=None,
    gini_to_match=None,
    plot_path=None,
):
    """
    Build the OG-ETH ability matrix from the OG-USA profiles.

    The OG-USA matrix is interpolated onto the model's age and group grid
    and multiplied by the NTA-based age factor. The gaps between the
    lifetime-income groups are then set in one of two ways: to reproduce
    target income shares by group (by default the WID pre-tax income
    shares for Ethiopia), or to reproduce a single target Gini
    coefficient. The result is scaled so that the population-weighted
    average ability is one.

    Args:
        E (int): age at which agents become economically active
        S (int): number of model periods in a lifetime
        J (int): number of lifetime-income groups
        lambdas (Numpy array): population share of each group, length J
        age_wgts (Numpy array): steady-state population distribution,
            either the joint distribution over age and group, size (S, J),
            or the age distribution alone, length S
        group_shares (Numpy array): target income share of each group,
            length J; None uses the WID shares for Ethiopia
        gini_to_match (float): target Gini coefficient; when given, the
            groups are tilted to this Gini instead of to income shares
        plot_path (str): directory to save a plot of the profiles to

    Returns:
        emat_new_scaled (Numpy array): ability matrix scaled so that the
            population-weighted average is 1, size (S, J)

    """
    lambdas = np.asarray(lambdas, dtype=float).flatten()
    age_wgts = np.asarray(age_wgts, dtype=float)
    assert lambdas.shape[0] == J
    if age_wgts.ndim == 1:
        age_wgts = age_wgts.reshape(S, 1) * lambdas.reshape(1, J)
    assert age_wgts.shape == (S, J)
    if gini_to_match is not None and group_shares is not None:
        raise ValueError("pass either group_shares or gini_to_match, not both")
    e_usa, lambdas_usa = load_ogusa_e()
    e_base = interpolate_usa_e(e_usa, lambdas_usa, E, S, lambdas)
    ages = model_ages(E, S)
    e_age = e_base * earnings_age_factor(ages).reshape(S, 1)
    if gini_to_match is not None:
        e_new = tilt_to_gini(e_age, age_wgts, lambdas, gini_to_match)
    else:
        if group_shares is None:
            group_shares = wid_group_shares("ETH", lambdas)
        e_new = scale_groups_to_shares(e_age, age_wgts, group_shares)
    emat_new_scaled = e_new / (e_new * age_wgts).sum()
    if plot_path is not None:
        pp.plot_income_data(
            ages,
            group_midpoints(lambdas),
            lambdas,
            emat_new_scaled,
            path=plot_path,
            filesuffix="_eth",
        )
    return emat_new_scaled


def write_json_parameters(json_path, updates):
    """
    Replace parameters in a packaged JSON file, leaving every other entry
    exactly as it is.

    Args:
        json_path (str): path to the JSON file
        updates (dict): parameter name -> JSON-serializable value

    Returns:
        None

    """
    with open(json_path, encoding="utf-8") as f:
        params = json.load(f)
    params.update(updates)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=4)
        f.write("\n")


def main():
    """
    Regenerate the packaged ability matrix from the packaged demographics
    and print how it compares with the WID shares.
    """
    from ogcore.parameters import Specifications

    json_path = os.path.join(CUR_PATH, "ogeth_default_parameters.json")
    p = Specifications(baseline=True)
    with open(json_path, encoding="utf-8") as f:
        p.update_specifications(json.load(f))
    lambdas = np.asarray(p.lambdas).flatten()
    e = get_e_interp(p.E, p.S, p.J, lambdas, p.omega_SS)
    shares = implied_group_shares(e, p.omega_SS)
    wid_eth = wid_group_shares("ETH", lambdas)
    wid_us = wid_group_shares("US", lambdas)
    print("group      lambda   e mean   model share   WID ETH   WID US")
    means = shares / lambdas
    for j in range(p.J):
        print(
            f"{j + 1:>5}  {lambdas[j]:>9.3f}  {means[j]:>7.3f}  "
            f"{shares[j]:>12.3f}  {wid_eth[j]:>8.3f}  {wid_us[j]:>7.3f}"
        )
    gini = implied_gini(e, p.omega_SS, lambdas)
    print(
        f"model Gini {gini:.3f}; WID Ethiopia {wid_gini('ETH'):.3f}, "
        f"WID US {wid_gini('US'):.3f}"
    )
    e_gini = get_e_interp(
        p.E, p.S, p.J, lambdas, p.omega_SS, gini_to_match=wid_gini("ETH")
    )
    print(
        "for comparison, matching the WID Gini alone gives group means "
        + ", ".join(
            f"{m:.3f}"
            for m in implied_group_shares(e_gini, p.omega_SS) / lambdas
        )
    )
    write_json_parameters(json_path, {"e": e.tolist()})
    print(f"wrote e to {json_path}")


if __name__ == "__main__":
    main()

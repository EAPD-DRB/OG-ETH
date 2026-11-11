"""
This module uses data from World Bank WDI, World Bank Quarterly Public
Sector Debt (QPSD) database, the IMF, and UN ILO to find values for
parameters for the OG-ETH model that rely on macro data for calibration.
"""

# imports
import pandas as pd
import numpy as np
import requests
import datetime
from pathlib import Path

# Solver settings used by the example scripts: the damping of OG-Core's
# outer loops (nu, the weight on the new iterate) and Anderson acceleration
# of the time-path outer loop (PSLmodels/OG-Core master; the example applies
# it only where the installed OG-Core has the parameters). With discount
# factors that differ by lifetime-income group the plain damped iteration
# converges slowly, and a smaller step with acceleration is both faster and
# more robust.
NU = 0.2
TPI_ANDERSON_M = 5
TPI_ANDERSON_BETA = 1.0

# Public capital elasticity; see firms.md.
GAMMA_G_LIC = 0.1

# Window for the g_y_annual average-growth calculation: the mean of the
# year-over-year GDP-per-capita growth rates for G_Y_START_YEAR through
# G_Y_END_YEAR (inclusive). We use the post-2015 decade rather than the
# full available history: the 2004-2015 state-led investment boom (which
# lifted the 2006-2024 average to ~6.0%) is explicitly not expected to
# repeat (IMF Country Report 26/20 DSA assumes long-run growth "slower
# than historical rates of around 10 percent"), so this window gives a
# balanced-growth-path productivity rate that averages over the post-boom
# normalization, the 2020-2022 conflict/COVID dip, and the recent
# gold-driven recovery. Average annual GDP-per-capita growth for the ten
# years 2016-2025 = 4.7% (see macro.md). Computing the growth rate for
# G_Y_START_YEAR requires the previous year's level, so the level filter
# below keeps data back to G_Y_START_YEAR - 1.
G_Y_START_YEAR = 2016
G_Y_END_YEAR = 2025


def _fetch_wb_data(indicators, country_iso, start_year, end_year, source):
    """
    Fetch a set of World Bank indicators and return a single DataFrame.

    Args:
        indicators (dict): mapping of human-readable labels to indicator codes
        country_iso (str): ISO country code
        start_year (int): first year to request
        end_year (int): last year to request
        source (int): World Bank source ID

    Returns:
        pandas.DataFrame: DataFrame indexed by year/quarter label
    """
    if source == 2:
        date_range = f"{start_year}:{end_year}"
    elif source == 20:
        date_range = f"{start_year}Q1:{end_year}Q4"
    else:
        raise ValueError(f"Unsupported World Bank source: {source}")

    data_frames = []
    for label, indicator_code in indicators.items():
        response = requests.get(
            (
                "https://api.worldbank.org/v2/country/"
                f"{country_iso}/indicator/{indicator_code}"
            ),
            params={
                "date": date_range,
                "source": source,
                "format": "json",
                "per_page": 10000,
            },
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError(
                f"Malformed World Bank response for {indicator_code}"
            ) from exc

        if (
            not isinstance(payload, list)
            or len(payload) < 2
            or not isinstance(payload[1], list)
            or not payload[1]
        ):
            raise ValueError(
                f"Empty or malformed World Bank response for {indicator_code}"
            )

        series_data = {}
        for row in payload[1]:
            date = row.get("date")
            if date is None:
                continue
            series_data[date] = row.get("value")

        if not series_data:
            raise ValueError(
                "No dated observations in World Bank response "
                f"for {indicator_code}"
            )

        series = pd.Series(series_data, name=label)
        series = pd.to_numeric(series, errors="coerce")
        data_frames.append(series.to_frame())

    data = pd.concat(data_frames, axis=1)
    data.index.name = "year"
    # Preserve descending time order used by the existing pct_change(-1) logic.
    data = data.sort_index(ascending=False)
    return data


def _get_imf_macro_params(
    country_iso,
    target_year,
    data_path=None,
):
    """
    Fetch IMF GFS data and compute alpha_T and alpha_G.

    Args:
        country_iso (str): ISO alpha-3 country code
        target_year (int): preferred calibration year
        data_path (str | Path | None): optional path to save IMF CSV data

    Returns:
        dict: IMF-derived macro parameters
    """
    required_indicators = {"G2_T", "G24_T", "G27_T", "G271_T"}
    data_path = Path(data_path) if data_path is not None else None
    response = requests.get(
        (
            "https://api.imf.org/external/sdmx/3.0/data/dataflow/"
            f"IMF.STA/GFS_SOO/12.0.0/"
            f"{country_iso}.S1311.G2M.*.POGDP_PT.A"
        ),
        timeout=30,
    )
    response.raise_for_status()
    try:
        payload = response.json()
        data = payload["data"]
        structure = data["structures"][0]
        data_set = data["dataSets"][0]
        series_dimensions = structure["dimensions"]["series"]
        observation_years = [
            value.get("id", value.get("value"))
            for value in structure["dimensions"]["observation"][0]["values"]
        ]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            "Empty or malformed IMF response for GFS_SOO"
        ) from exc

    records = []
    for series_key, series in data_set["series"].items():
        dimension_indexes = [int(idx) for idx in series_key.split(":")]
        labels = {
            dim["id"]: dim["values"][idx]["id"]
            for dim, idx in zip(series_dimensions, dimension_indexes)
        }
        indicator = labels.get("INDICATOR")
        if indicator not in required_indicators:
            continue
        for observation_key, observation in series.get(
            "observations", {}
        ).items():
            value = observation[0]
            if value is None:
                continue
            records.append(
                {
                    "year": observation_years[int(observation_key)],
                    "indicator": indicator,
                    "value": float(value),
                    "country_iso": country_iso,
                    "sector": "S1311",
                    "dataset": "IMF.STA:GFS_SOO(12.0.0)",
                }
            )

    imf_data = pd.DataFrame(records)
    if imf_data.empty:
        raise ValueError("Empty or malformed IMF response for GFS_SOO")

    if data_path is not None:
        data_path.parent.mkdir(parents=True, exist_ok=True)
        imf_data.sort_values(["indicator", "year"]).to_csv(
            data_path, index=False
        )
        print(f"IMF data saved to {data_path}")

    imf_data["year"] = pd.to_numeric(imf_data["year"], errors="coerce")
    imf_data["value"] = pd.to_numeric(imf_data["value"], errors="coerce")
    imf_data = imf_data.dropna(subset=["year", "value"])

    available = (
        imf_data.pivot_table(
            index="year", columns="indicator", values="value", aggfunc="first"
        )
        .sort_index()
        .dropna(subset=sorted(required_indicators))
    )
    available = available.loc[available.index <= int(target_year)]

    if available.empty:
        raise ValueError(
            f"No complete IMF data available for {country_iso} "
            f"up to {target_year}"
        )

    selected_year = (
        int(target_year)
        if int(target_year) in available.index
        else int(available.index.max())
    )
    if selected_year != int(target_year):
        print(
            f"Warning: No IMF data for {target_year}. "
            f"Using last available year: {selected_year}"
        )

    values = available.loc[selected_year]
    return {
        "alpha_T": [(values["G27_T"] - values["G271_T"]) / 100],
        "alpha_G": [
            (values["G2_T"] - values["G24_T"] - values["G27_T"]) / 100
        ],
    }


def get_macro_params(
    data_start_date=datetime.datetime(1947, 1, 1),
    data_end_date=datetime.datetime(2025, 12, 31),
    country_iso="ETH",
    update_from_api=False,
    imf_data_year=None,
    imf_data_path=None,
):
    """
    Compute values of parameters that are derived from macro data

    Args:
        data_start_date (datetime): start date for data
        data_end_date (datetime): end date for data
        country_iso (str): ISO code for country
        imf_data_year (int | None): IMF target year override. Defaults to
            data_end_date.year when None.
        imf_data_path (str | Path | None): optional path to save IMF CSV data

    Returns:
        macro_parameters (dict): dictionary of parameter values
    """
    # initialize a dictionary of parameters
    macro_parameters = {}

    """
    Retrieve data from the World Bank World Development Indicators.
    """
    # Dictionaries of variables and their corresponding World Bank codes
    # Annual data
    wb_a_variable_dict = {
        "GDP per capita (constant 2015 US$)": "NY.GDP.PCAP.KD",
        "Real GDP (constant 2015 US$)": "NY.GDP.MKTP.KD",
        "Nominal GDP (current US$)": "NY.GDP.MKTP.CD",
        (
            "General government final consumption expenditure (current US$)"
        ): "NE.CON.GOVT.CD",
    }
    # Quarterly public-sector-debt (QPSD) indicators are intentionally
    # not fetched for OG-ETH: the World Bank QPSD database has no Ethiopia
    # data. The debt parameters (initial_debt_ratio,
    # initial_foreign_debt_ratio, zeta_D) are hand-calibrated from the
    # Ethiopia MoF Public Sector Debt Bulletin No. 51 (see macro.md).
    if update_from_api:
        try:
            wb_data_a = _fetch_wb_data(
                wb_a_variable_dict,
                country_iso,
                data_start_date.year,
                data_end_date.year,
                source=2,
            )
            # Compute annual GDP-per-capita growth (g_y_annual) from the
            # World Bank WDI series, averaging the year-over-year growth
            # rates over the [G_Y_START_YEAR, G_Y_END_YEAR] window (see
            # macro.md). Debt parameters are not derived here (see note
            # above).
            if "GDP per capita (constant 2015 US$)" in wb_data_a.columns:
                gdp_pc = wb_data_a["GDP per capita (constant 2015 US$)"]
                years = gdp_pc.index.astype(int)
                # Keep one year before G_Y_START_YEAR so the growth rate for
                # G_Y_START_YEAR itself can be formed; pct_change(-1) on the
                # descending series then yields the growth rates for
                # G_Y_START_YEAR..G_Y_END_YEAR (the anchor year becomes NaN
                # and is dropped by mean()).
                gdp_pc = gdp_pc[
                    (years >= G_Y_START_YEAR - 1) & (years <= G_Y_END_YEAR)
                ]
                g_y_series = gdp_pc.pct_change(-1)

                # If all values are NaN, return None
                macro_parameters["g_y_annual"] = (
                    g_y_series.mean() if not g_y_series.isna().all() else None
                )
                print(
                    "g_y_annual updated from World Bank API: "
                    f"{macro_parameters['g_y_annual']}"
                )
            else:
                print(
                    "Warning: Missing GDP per capita data in World "
                    "Bank data. Skipping update for g_y_annual."
                )
        except Exception:
            print("Failed to retrieve data from World Bank")
            print("Will not update g_y_annual")
    else:
        print("Not updating from World Bank API")

    # gamma is deliberately NOT refreshed from the ILOSTAT labour share: the
    # naive 1 - labour share (about 0.515 net of gamma_g) is biased by
    # Ethiopia's self-employment, and the calibrated 0.30 is a triangulated
    # Gollin-adjusted value (firms.md). A live refresh would silently
    # overwrite it, so it is off the live path entirely.

    # alpha_T and alpha_G are NOT pulled from the IMF API for OG-ETH: the
    # IMF SDMX endpoint returns only 2002-vintage data for Ethiopia, and
    # the documented sources differ (alpha_G -> World Bank NE.CON.GOVT.ZS;
    # alpha_T -> IMF GFS + IMF Country Report 26/20, hand-combined). Both
    # stay at the committed values in macro.md. _get_imf_macro_params is
    # retained (tested independently) for reuse if wired to the right data.

    # The government-debt interest-rate parameters (r_gov_scale, r_gov_shift,
    # r_gov_DY, r_gov_DY2) are NOT returned from the live path. r_gov_scale
    # and the base r_gov_shift come from inverting the Li, Magud, Werner,
    # Witte (2021) sovereign-vs-corporate yield relationship (a deterministic
    # calculation reproduced by estimate_r_gov below), but the committed
    # r_gov_shift is then re-centered for the debt-elastic premium
    # (r_gov_DY, r_gov_DY2) so the premium is exactly zero at debt_ratio_ss
    # (see macro.md). Returning the raw LMW shift here would un-center that
    # premium and silently move the steady state, so all four stay frozen at
    # the documented values in ogeth_default_parameters.json.
    if update_from_api:
        print(
            "Not updating r_gov_* (frozen, debt-elastic premium re-centered; "
            "see macro.md and estimate_r_gov)"
        )
    else:
        print("Not computing r_gov_shift, r_gov_scale")

    return macro_parameters


def estimate_r_gov(debt_ratio_ss=0.30, r_gov_DY2=0.04):
    """
    Reproduce the frozen government-debt interest-rate parameters.

    The base level shift and scale invert the sovereign-vs-corporate yield
    relationship estimated by Li, Magud, Werner, Witte (2021),
    https://www.imf.org/en/Publications/WP/Issues/2021/06/04/The-Long-Run-Impact-of-Sovereign-Yields-on-Corporate-Yields-in-Emerging-Markets-50224
    (discussion at https://github.com/EAPD-DRB/OG-ZAF/issues/22): generate
    modelled corporate yields for sovereign yields of 2-12% using Table 8
    column 2, then OLS-regress the sovereign yield on the fitted corporate
    yield.

    A convex debt-elastic premium ``r_gov_DY2 * (D/Y - debt_ratio_ss)**2`` is
    then added and re-centered on ``debt_ratio_ss`` so it is exactly zero at
    the steady-state debt ratio (leaving the steady state unchanged) and only
    prices the transition-path debt overshoot. Expanding the square gives
    ``r_gov_DY = -2 * r_gov_DY2 * debt_ratio_ss`` and shifts the level term by
    ``r_gov_DY2 * debt_ratio_ss**2`` (OG-Core subtracts ``r_gov_shift``, so the
    constant is folded into the shift). See macro.md for the full derivation.

    Args:
        debt_ratio_ss (float): steady-state debt-to-GDP ratio the premium is
            centered on
        r_gov_DY2 (float): curvature of the debt-elastic premium

    Returns:
        dict: {r_gov_scale, r_gov_shift, r_gov_DY, r_gov_DY2}
    """
    import statsmodels.api as sm

    sov_y = np.arange(20, 120) / 10
    corp_yhat = 8.199 - (2.975 * sov_y) + (0.478 * sov_y**2)
    corp_yhat = sm.add_constant(corp_yhat)
    res = sm.OLS(sov_y, corp_yhat).fit()
    # First term is the constant (÷100 for the correct unit); second is slope.
    r_gov_scale = res.params[1]
    r_gov_shift_base = -res.params[0] / 100
    r_gov_shift = r_gov_shift_base - r_gov_DY2 * debt_ratio_ss**2
    r_gov_DY = -2 * r_gov_DY2 * debt_ratio_ss
    return {
        "r_gov_scale": [r_gov_scale],
        "r_gov_shift": [r_gov_shift],
        "r_gov_DY": r_gov_DY,
        "r_gov_DY2": r_gov_DY2,
    }


# ---------------------------------------------------------------------------
# Remittances
#
# Remittances enter OG-Core as an exogenous share of GDP (alpha_RM_1 in the
# first period, alpha_RM_T in the long run) distributed across households by
# eta_RM. Two of the shipped values are derived from the packaged
# demographics rather than hand-set, so they are rebuilt whenever the
# demographics are (update_baseline.py):
#
# * g_RM -- aggregates.get_RM advances detrended remittances by the factor
#   (1 + g_RM[t]) / (exp(g_y) * (1 + g_n[t-1])) between the first period and
#   tG1, independently of that period's output, so remittances keep pace with
#   trend GDP (a constant share on the balanced growth path) only when that
#   factor is one. g_n moves along the transition, so the growth rate that
#   does this is a path, not a scalar (flat_share_g_RM). The shipped path
#   (program_share_g_RM) scales that factor by the ratio of consecutive
#   program-year shares, so RM/Y follows the IMF projection from 5.6 to 4.1
#   percent of GDP over the program and then holds; alpha_RM_T is the
#   program endpoint (remittance_level_params). Along the transition RM/Y
#   then moves inversely with output's deviation from trend.
# * eta_RM -- the share of aggregate remittances each household receives,
#   shaped (S, J). OG-Core's default hands every lifetime-income group
#   exactly its population share; remittance_eta instead maps a data
#   distribution of remittance value across income quintiles onto the
#   model's J groups and spreads it per capita across ages within a group.
# ---------------------------------------------------------------------------

# Share of total remittance VALUE received by each household income
# quintile, poorest to richest. World Bank / Bendixen & Amandi, "Remittances
# to Ethiopia" (Future of African Remittances national survey, 2010; 2,412
# adults): recipients' monthly household income was 9% below ETB 1,000, 47%
# at ETB 1,000-3,500 and 37% above ETB 3,500 (7% no answer). Against 2010
# GDP per capita of ETB 4,262 (about ETB 1,600 a month for a 4.6-person
# household) those brackets map to the bottom two, middle two and top
# quintile; renormalized over respondents and split evenly within each
# pair. See docs/book/content/calibration/macro.md (Remittances).
RM_QUINTILE_VALUE_SHARES = [
    9 / 93 / 2,
    9 / 93 / 2,
    47 / 93 / 2,
    47 / 93 / 2,
    37 / 93,
]


def flat_share_g_RM(g_y, g_n):
    """
    Remittance growth path that keeps aggregate remittances growing with
    trend GDP, so their share is constant on the balanced growth path.

    Args:
        g_y (scalar): model-period productivity growth rate
        g_n (array_like): population growth path, length T + S

    Returns:
        g_RM (Numpy array): growth rate of remittances, length T + S, such
            that ``(1 + g_RM[t]) / (exp(g_y) * (1 + g_n[t - 1])) == 1`` for
            every t >= 1 (the factor ``get_RM`` applies)
    """
    g_n = np.asarray(g_n, dtype=float)
    g_RM = np.exp(g_y) * (1.0 + np.roll(g_n, 1)) - 1.0
    # get_RM never reads g_RM[0]; keep it consistent with period 0 anyway
    g_RM[0] = np.exp(g_y) * (1.0 + g_n[0]) - 1.0
    return g_RM


def program_remittance_shares(shares=None):
    """
    Remittance share of GDP in each program year as the model follows it: a
    geometric glide from the measured first-year share to the program's
    last-year share.

    The IMF's year-by-year projection (5.6, 6.0, 5.9, 5.3, 4.8, 4.6, 4.1
    percent of GDP) peaks in FY2025/26 and then falls by up to 0.6 points
    a year; following it exactly would need remittance growth rates of
    +16 and -4 percent in consecutive periods, outside the [-2%, 15%]
    bounds OG-Core places on ``g_RM``. The glide keeps the two values the
    calibration anchors on -- the measured level and the program endpoint
    -- and spreads the decline evenly between them.

    Args:
        shares (array_like): program projection of the remittance share of
            GDP, percent; defaults to ``IMF_PRIVATE_TRANSFERS``

    Returns:
        Numpy array: smoothed shares, percent, same length as ``shares``
    """
    if shares is None:
        shares = IMF_PRIVATE_TRANSFERS
    s = np.asarray(shares, dtype=float)
    return np.geomspace(s[0], s[-1], s.size)


def program_share_g_RM(g_y, g_n, shares=None):
    """
    Remittance growth path that moves the remittance share of trend GDP
    from the measured level to the IMF program's endpoint over the program
    years and holds it flat afterwards.

    Multiplying the flat-share factor by the ratio of consecutive shares
    along ``program_remittance_shares`` makes ``get_RM`` carry RM/Y (with
    output on trend) from ``shares[0]`` in the first period to
    ``shares[-1]`` in the last program year; from then on the path is
    ``flat_share_g_RM``, so the share stays where the program leaves it.
    Pair it with ``alpha_RM_T = shares[-1]`` so that OG-Core's blend
    toward the long-run share after ``tG1`` is a no-op.

    Args:
        g_y (scalar): model-period productivity growth rate
        g_n (array_like): population growth path, length T + S
        shares (array_like): program projection of the remittance share of
            GDP, percent; defaults to ``IMF_PRIVATE_TRANSFERS``

    Returns:
        g_RM (Numpy array): growth rate of remittances, length T + S
    """
    s = program_remittance_shares(shares)
    g_RM = flat_share_g_RM(g_y, g_n)
    ratio = s[1:] / s[:-1]
    g_RM[1 : s.size] = (1.0 + g_RM[1 : s.size]) * ratio - 1.0
    return g_RM


def remittance_level_params(shares=None, scenario=None):
    """
    The remittance share of GDP in the first period and in the long run.

    Args:
        shares (array_like): remittance share of GDP in each program year,
            percent; defaults to ``IMF_PRIVATE_TRANSFERS``
        scenario (str): ``"history"`` holds the measured FY2024/25 share
            for the long run; ``"program"`` takes the last program-year
            share, held like the other program series; defaults to
            DEFAULT_SCENARIO

    Returns:
        dict: ``{"alpha_RM_1", "alpha_RM_T"}``
    """
    if shares is None:
        shares = IMF_PRIVATE_TRANSFERS
    scenario = check_scenario(scenario)
    long_run = shares[-1] if scenario == "program" else shares[0]
    return {
        "alpha_RM_1": round(to_model(float(shares[0]) / 100), 6),
        "alpha_RM_T": round(to_model(float(long_run) / 100), 6),
    }


def remittance_eta(omega_SS, lambdas, quintile_value_shares=None):
    """
    Allocation matrix distributing aggregate remittances across households.

    Args:
        omega_SS (array_like): steady-state population distribution, (S, J),
            with ``omega_SS.sum(axis=0) == lambdas``
        lambdas (array_like): population shares of the J lifetime-income
            groups, poorest to richest
        quintile_value_shares (array_like): share of total remittance value
            received by each population quintile, poorest to richest;
            defaults to ``RM_QUINTILE_VALUE_SHARES``

    Returns:
        eta_RM (Numpy array): (S, J) matrix summing to one. Each group's
            column sums to its data share of remittance value (the quintile
            shares interpolated onto the group boundaries, assuming a
            uniform density of remittance value within a quintile); within a
            group, remittances are spread per capita across ages, so every
            household in the group receives the same amount.
    """
    omega_SS = np.asarray(omega_SS, dtype=float)
    lambdas = np.asarray(lambdas, dtype=float).flatten()
    if quintile_value_shares is None:
        quintile_value_shares = RM_QUINTILE_VALUE_SHARES
    q = np.asarray(quintile_value_shares, dtype=float)
    q = q / q.sum()
    # cumulative remittance value at each population percentile, evaluated
    # at the lambdas group boundaries
    cum_pop = np.concatenate([[0.0], np.cumsum(np.full(q.size, 1 / q.size))])
    cum_val = np.concatenate([[0.0], np.cumsum(q)])
    bounds = np.concatenate([[0.0], np.cumsum(lambdas)])
    group_share = np.diff(np.interp(bounds, cum_pop, cum_val))
    group_share = group_share / group_share.sum()
    within = omega_SS / omega_SS.sum(axis=0, keepdims=True)
    return within * group_share.reshape(1, -1)


def derive_remittance_params(g_y, g_n, omega_SS, lambdas, scenario=None):
    """
    The remittance parameters that depend on a given set of demographics.

    Args:
        g_y (scalar): model-period productivity growth rate
        g_n (array_like): population growth path, length T + S
        omega_SS (array_like): steady-state population distribution, (S, J)
        lambdas (array_like): population shares of the J groups
        scenario (str): ``"history"`` keeps the remittance share of GDP at
            its measured FY2024/25 value; ``"program"`` moves it along the
            IMF projection (see SCENARIOS); defaults to DEFAULT_SCENARIO

    Returns:
        dict: ``{"g_RM": list, "eta_RM": nested list}`` ready for
            ``Specifications.update_specifications``
    """
    scenario = check_scenario(scenario)
    if scenario == "program":
        g_RM = program_share_g_RM(g_y, g_n)
    else:
        g_RM = flat_share_g_RM(g_y, g_n)
    return {
        "g_RM": g_RM.tolist(),
        "eta_RM": remittance_eta(omega_SS, lambdas).tolist(),
    }


def derived_remittance_params(p, scenario=None):
    """
    The remittance parameters that depend on the demographics in ``p``.

    Args:
        p (Specifications): parameters carrying ``g_y``, ``g_n``,
            ``omega_SS`` and ``lambdas``
        scenario (str): see ``derive_remittance_params``

    Returns:
        dict: see ``derive_remittance_params``
    """
    g_n = np.asarray(p.g_n, dtype=float)[: p.T + p.S]
    return derive_remittance_params(
        p.g_y, g_n, p.omega_SS, p.lambdas, scenario
    )


# ---------------------------------------------------------------------------
# Long-run debt ratio of the program scenario: the IMF program's FY2030/31
# debt ratio is 28.6 percent of GDP and the authorities' medium-term
# objective a ratio near 30 percent (macro.md).

# ---------------------------------------------------------------------------
# GDP basis: the rebased national accounts
#
# Ethiopia rebased its national accounts on 4 November 2026 (Ministry of
# National Strategy, with IMF technical assistance; announced by the Finance
# Minister, ENA): base year FY2024/25, 2008 SNA, wider coverage of informal
# mining and manufacturing, transport and digital services and regional
# state-owned enterprises. FY2024/25 nominal GDP went from 15,094 to 24,030
# billion birr (USD 126.5 to 201.4 billion at the NBE average rate of 119.3)
# and FY2025/26 (preliminary) is 31,860 billion birr. Every ratio to GDP in
# this calibration is to the rebased series.
#
# The IMF tables below are kept exactly as published, on the 2015/16 base
# (IMF CR 26/174, June 2026, Table 1: FY2024/25 actual 15,094 billion birr;
# FY2025/26 projection 19,268; FY2026/27 23,851; WEO October 2026 has the
# same figures). A fiscal flow or stock in birr, or a balance-of-payments
# flow in dollars, has the same numerator on either basis, so its rebased
# ratio is the published ratio times old GDP / new GDP of that year. Years
# the rebasing has not reached yet (FY2026/27 onward, still old-base IMF
# projections) take the FY2025/26 factor: the revision is assumed to stay
# where it was last measured until the IMF re-bases its projections.
# National-accounts components (consumption, investment) are NOT converted
# this way: the rebasing revised their numerators too, so they come from the
# rebased accounts directly (GROSS_CAPITAL_FORMATION etc. below).
# ---------------------------------------------------------------------------
NOMINAL_GDP_OLD_BASE_BIRR_BN = {
    "FY2023/24": 11752.0,
    "FY2024/25": 15094.0,
    "FY2025/26": 19268.0,
    "FY2026/27": 23851.0,
}
NOMINAL_GDP_REBASED_BIRR_BN = {"FY2024/25": 24030.0, "FY2025/26": 31860.0}

# Fiscal program path (IMF Country Report 26/174, fifth ECF review, Tables 1,
# 2b and 4b). Ethiopian fiscal years FY2024/25 (model period 0, start year
# 2025) through FY2030/31 (period 6); the last value of each series is held
# for the long run. Published percent of OLD-base GDP, general government;
# converted below.
# ---------------------------------------------------------------------------
PROGRAM_YEARS = [
    "FY2024/25",
    "FY2025/26",
    "FY2026/27",
    "FY2027/28",
    "FY2028/29",
    "FY2029/30",
    "FY2030/31",
]


def rebase_factors(n=len(PROGRAM_YEARS)):
    """
    Old-base over rebased nominal GDP for each program year: the factor that
    turns a published ratio to old-base GDP into a ratio to rebased GDP when
    the numerator is unaffected by the rebasing.

    Args:
        n (int): number of years from FY2024/25

    Returns:
        Numpy array: length n; years past FY2025/26 hold its factor
    """
    known = [
        NOMINAL_GDP_OLD_BASE_BIRR_BN[y] / NOMINAL_GDP_REBASED_BIRR_BN[y]
        for y in ("FY2024/25", "FY2025/26")
    ]
    return np.array(known + [known[-1]] * (n - len(known)))[:n]


def rebased(series):
    """
    Convert a published old-base percent-of-GDP series (one value per
    program year from FY2024/25) to percent of rebased GDP.

    Args:
        series (array_like): published values

    Returns:
        list: rebased values, rounded to 4 decimals
    """
    x = np.asarray(series, dtype=float)
    return [round(float(v), 4) for v in x * rebase_factors(x.size)]


# Published, percent of old-base GDP (IMF CR 26/174 Tables 1 and 2b).
# Public debt is the general-government gross debt of the IMF's World
# Economic Outlook (October 2026, GGXWDG_NGDP, "2025" = FY2024/25), which
# matches the general-government revenue, spending and interest the model's
# budget uses. The program report's wider public debt (50.5 percent in
# FY2024/25) adds about 7.2 points of NBE long-term foreign liabilities and
# Ethio Telecom external debt that the budget does not service.
IMF_PUBLIC_DEBT_PUBLISHED = [43.3, 40.7, 37.0, 34.2, 31.8, 29.7, 27.5]
IMF_PUBLIC_DEBT_WIDE_PUBLISHED = [50.5, 45.3, 40.8, 37.2, 34.0, 31.2, 28.6]
IMF_REVENUE_PUBLISHED = [9.2, 10.8, 11.4, 11.8, 12.1, 12.2, 12.3]
IMF_TAX_REVENUE_PUBLISHED = [7.8, 9.5, 10.1, 10.5, 10.8, 10.9, 11.0]
IMF_GRANTS_PUBLISHED = [1.7, 1.3, 0.9, 0.3, 0.3, 0.3, 0.1]
IMF_EXPENDITURE_PUBLISHED = [12.0, 14.1, 13.5, 13.5, 14.0, 14.0, 14.0]
IMF_RECURRENT_PUBLISHED = [7.1, 8.2, 8.0, 8.5, 8.6, 8.8, 8.9]
IMF_INTEREST_PUBLISHED = [0.8, 1.3, 1.3, 1.3, 1.3, 1.4, 1.5]
IMF_CAPITAL_PUBLISHED = [5.0, 5.8, 5.5, 5.0, 5.4, 5.2, 5.1]
# goods and services balance (Table 1 "resource gap"; the Table 4b "trade
# balance" row is goods only)
IMF_TRADE_BALANCE_PUBLISHED = [-7.1, -9.0, -7.4, -7.0, -7.1, -6.9, -7.0]
IMF_PRIVATE_TRANSFERS_PUBLISHED = [5.6, 6.0, 5.9, 5.3, 4.8, 4.6, 4.1]
IMF_CURRENT_ACCOUNT_PUBLISHED = [-1.1, -2.5, -1.3, -1.5, -2.0, -2.0, -2.7]
IMF_DOMESTIC_DEBT_PUBLISHED = [18.7, 15.4, 13.7, 12.6, 12.6, 12.5, 11.9]
# real growth is a ratio of volumes, not converted (old base; the rebased
# accounts put FY2025/26 at 7.7 percent, REBASED_REAL_GROWTH_FY2526)
IMF_REAL_GDP_GROWTH = [9.2, 9.2, 7.8, 8.2, 8.2, 8.0, 7.7]
REBASED_REAL_GROWTH_FY2526 = 7.7

# The same series in percent of rebased GDP: what the calibration uses
IMF_PUBLIC_DEBT = rebased(IMF_PUBLIC_DEBT_PUBLISHED)
IMF_REVENUE = rebased(IMF_REVENUE_PUBLISHED)  # excl. grants
IMF_TAX_REVENUE = rebased(IMF_TAX_REVENUE_PUBLISHED)
IMF_GRANTS = rebased(IMF_GRANTS_PUBLISHED)
IMF_EXPENDITURE = rebased(IMF_EXPENDITURE_PUBLISHED)
IMF_RECURRENT = rebased(IMF_RECURRENT_PUBLISHED)
IMF_INTEREST = rebased(IMF_INTEREST_PUBLISHED)
IMF_CAPITAL = rebased(IMF_CAPITAL_PUBLISHED)
IMF_TRADE_BALANCE = rebased(IMF_TRADE_BALANCE_PUBLISHED)
IMF_PRIVATE_TRANSFERS = rebased(IMF_PRIVATE_TRANSFERS_PUBLISHED)
IMF_CURRENT_ACCOUNT = rebased(IMF_CURRENT_ACCOUNT_PUBLISHED)
IMF_DOMESTIC_DEBT = rebased(IMF_DOMESTIC_DEBT_PUBLISHED)
# foreign-held share of general-government debt in FY2024/25: external debt
# (31.8 percent of old GDP in the program's wider perimeter) less the 7.2
# points outside general government, over 43.3
GG_FOREIGN_DEBT_SHARE = round(
    (31.8 - (IMF_PUBLIC_DEBT_WIDE_PUBLISHED[0] - IMF_PUBLIC_DEBT_PUBLISHED[0]))
    / IMF_PUBLIC_DEBT_PUBLISHED[0],
    4,
)

# Rebased expenditure-side national accounts, FY2024/25 (Ministry of National
# Strategy rebasing report, as reported by Birr Metrics, BusinessDay and
# Wazema and checked against the old-base NBE tables): private consumption
# 15.47 trillion birr (64.4 percent), gross capital formation 8.49 trillion
# (35.3 percent, fixed capital plus inventories; old base 20.1), gross
# domestic saving 30.9 percent. Government consumption (about 4.7) and net
# exports (about -4.5, matching the balance-of-payments goods and services
# balance of USD -8.9 billion over USD 201.4 billion) are derived.
PRIVATE_CONSUMPTION_REBASED = 64.4
GROSS_CAPITAL_FORMATION_REBASED = 35.3
GOVERNMENT_CONSUMPTION_REBASED = 4.7
# program investment path for display only: the IMF's old-base path scaled
# by the FY2024/25 level revision
IMF_GROSS_INVESTMENT = [
    round(x * GROSS_CAPITAL_FORMATION_REBASED / 20.1, 2)
    for x in [20.1, 28.7, 27.5, 27.2, 27.2, 27.4, 26.5]
]

# Price basis. OG-Core's output Y is GDP at producer prices: the consumption
# tax is collected on top of it, so GDP at market prices, the basis of every
# data ratio, is Y plus the consumption tax. Shares OG-Core applies to its
# own Y (alpha_G, alpha_T, alpha_I, alpha_FA, alpha_RM, the debt ratios,
# initial wealth and public capital) are the data share times
# MODEL_PER_MARKET_GDP, and model moments are scored over Y plus the
# consumption tax (ogeth/targets.py). The consumption-tax share is the
# FY2024/25 outturn of the revenue mapped to tau_c below, over rebased GDP.
# General-government revenue outturn, FY2024/25, billions of birr (NBE Annual
# Report 2024/25, Table 6.3, from Ministry of Finance data; IMF CR 26/174
# Table 2a has the same totals). Each line is mapped to the model instrument
# that taxes the same margin (taxes.md):
#   personal income tax                         -> income tax (compliance)
#   business profit tax, other income taxes
#     (rental, withholding, interest, capital
#     gains) and government investment income
#     (NBE residual surplus, SOE dividends)     -> CIT collections factor
#   indirect taxes, charges and fees, sales of
#     goods and services                        -> consumption tax tau_c
#   rural and urban land-use fees               -> flat wealth tax
#   "other" non-tax (extraordinary items and
#     pension contributions) and property sales -> not mapped: contributions
#     are the payroll tax, the rest is one-off
REVENUE_FY2425_BIRR_BN = {
    "personal income tax": 194.3,
    "business profit tax": 229.6,
    "other income taxes": 52.9,
    "land-use fees": 44.1,
    "indirect taxes": 650.9,
    "charges and fees": 39.4,
    "government investment income": 20.0,
    "sales of goods and services": 32.8,
    "reimbursements and property sales": 4.7,
    "other non-tax incl. pension contributions": 117.8,
    "grants": 185.0,
}


def revenue_share(*lines, year="FY2024/25"):
    """
    Revenue lines as a share of rebased GDP at market prices.

    Args:
        *lines (str): keys of REVENUE_FY2425_BIRR_BN to add up
        year (str): fiscal year of the GDP denominator

    Returns:
        float: share of GDP
    """
    total = sum(REVENUE_FY2425_BIRR_BN[k] for k in lines)
    return round(total / NOMINAL_GDP_REBASED_BIRR_BN[year], 5)


PIT_REVENUE_SHARE = revenue_share("personal income tax")
CIT_REVENUE_SHARE = revenue_share(
    "business profit tax", "other income taxes", "government investment income"
)
CONS_TAX_SHARE = revenue_share(
    "indirect taxes", "charges and fees", "sales of goods and services"
)
WEALTH_TAX_SHARE = revenue_share("land-use fees")
MODEL_PER_MARKET_GDP = 1 / (1 - CONS_TAX_SHARE)


def to_model(share):
    """
    Convert a share of GDP at market prices into the share of OG-Core's Y.

    Args:
        share (scalar or array_like): share of market-price GDP

    Returns:
        same type: share of the model's Y
    """
    if np.ndim(share):
        return [float(x) * MODEL_PER_MARKET_GDP for x in share]
    return float(share) * MODEL_PER_MARKET_GDP


# Long-run debt ratio of the program scenario: 30 percent of old-base GDP,
# rebased with the latest factor, in model units
PROGRAM_DEBT_RATIO_SS = round(to_model(0.30 * float(rebase_factors()[-1])), 4)
# Initial general-government debt and its foreign-held share, FY2024/25, in
# model units (end of the year before the first model period)
INITIAL_DEBT_RATIO = round(to_model(IMF_PUBLIC_DEBT[0] / 100), 4)

# Cash transfers to households as a share of GDP, published percent of
# old-base GDP. The IMF recurrent line bundles the wage bill, goods and
# services, interest, and transfers; the household-transfer part is the fuel
# and fertilizer subsidies (about 1 percent of GDP in FY2024/25, fuel
# subsidies eliminated by March 2026 and a capped envelope in FY2026/27,
# fertilizer about 1 percent of GDP), the Productive Safety Net Program
# (budget contribution about 0.4 percent of GDP), and public pension payouts
# (about 0.5 percent of GDP). IMF CR 26/174 paragraphs 9, 20-22 and Box on
# social safety nets.
CASH_TRANSFERS_PUBLISHED = [2.0, 1.8, 1.5, 1.5, 1.5, 1.5, 1.5]
CASH_TRANSFERS = rebased(CASH_TRANSFERS_PUBLISHED)

# Long-run grants once the program's donor surge fades: 0.3 percent of
# old-base GDP, rebased with the latest factor
LONG_RUN_GRANTS = round(0.3 * float(rebase_factors(7)[-1]), 4)

# Required real return of foreign investors in Ethiopian capital (OG-Core's
# world_int_rate_annual). The 4 percent risk-free benchmark understates it for
# a frontier market: UNCTAD's World Investment Report 2018 puts the rate of
# return on inward FDI in Africa at 6.3 percent (2017), down from 12.3 percent
# in 2012. With OG-Core's capital split K_f = zeta_K (K_open - K_d), where
# K_open is capital demand at the world rate, this is the lever that sets the
# foreign-owned capital stock against the ~0.24 of GDP FDI stock (UNCTAD).
WORLD_INT_RATE_ANNUAL = 0.063

# Long-run real effective interest rate on public debt. Ethiopia's public
# debt is mostly concessional external debt (average interest on new
# FY2024/25 commitments 0.77 percent, MoF Bulletin 56) and domestic paper
# whose real return has been deeply negative; the program's FY2030/31
# interest bill (1.5 percent of GDP on 28.6 percent debt, a 5.2 percent
# nominal effective rate) against a GDP deflator of 8.6 percent still implies
# a negative real rate. We take 2 percent as the long-run real effective
# rate once inflation settles at the authorities' single-digit objective and
# domestic financing moves to market terms.
LONG_RUN_R_GOV = 0.02
# Periods after the program horizon over which r_gov converges to the
# long-run rate above
R_GOV_CONVERGENCE_PERIODS = 4
# OG-Core clips the sovereign rate at ``r_gov_floor`` (a parameter since
# PSLmodels/OG-Core#1203; the hard-coded 0.0 before that). The shipped shift
# path targets the program-implied negative real rates, and the example
# lowers the floor to R_GOV_FLOOR where the installed ogcore has the
# parameter so they can bind; on an older ogcore the rate sits at zero
# through the program years instead (documented in macro.md).
R_GOV_FLOOR = -0.10
# Steady-state return on capital the r_gov_shift path is evaluated at: the
# solved baseline steady state of examples/run_og_eth.py.
R_SS_FOR_R_GOV = 0.0901

# Informality. 77.65 percent of the employed are in informal employment
# (ILOSTAT harmonised series, SDG 8.3.1, from the 2021 Labour Force and
# Migration Survey; 84.4 percent in agriculture, 65.9 outside it). The
# informality calibration (taxes.md) grades income-tax compliance by
# lifetime-income group, with lifetime income as the proxy for formality:
# the formal 22.35 percent are the richest households, so groups 5-7 (the
# top 20 percent) are formal and group 4 is 23.5 percent formal.
INFORMAL_EMPLOYMENT_SHARE = 0.7765
LAMBDAS = [0.25, 0.25, 0.2, 0.1, 0.1, 0.09, 0.01]


def formal_share_by_group(informal_share, lambdas=LAMBDAS):
    """
    Share of each lifetime-income group that is formal when the formal
    share of the population sits at the top of the lifetime-income
    distribution.

    Args:
        informal_share (scalar): informal share of the employed
        lambdas (array_like): population shares of the groups, poorest
            first

    Returns:
        list: formal share of each group, between 0 and 1
    """
    lam = np.asarray(lambdas, dtype=float)
    top = np.cumsum(lam[::-1])[::-1]  # share at or above each group's floor
    formal = 1.0 - float(informal_share)
    above = top - lam  # share strictly above each group
    share = np.clip((formal - above) / lam, 0.0, 1.0)
    return [round(float(x), 4) for x in share]


# The program's revenue gains are direct-tax heavy -- in the first nine
# months of FY2025/26 federal direct taxes grew 78 percent against 41
# percent for domestic VAT and 5 percent for import taxes (IMF CR 26/174,
# p. 15) -- so in the program scenario part of the gain is the tax base
# broadening: another 6.5 percent of households (the size of the old
# calibration's broadening) become formal over the seven program years,
# linearly, and stay so. The history-anchored baseline holds the start.
NONCOMPLIANCE_START = [
    round(1 - x, 4) for x in formal_share_by_group(INFORMAL_EMPLOYMENT_SHARE)
]
NONCOMPLIANCE_END = [
    round(1 - x, 4)
    for x in formal_share_by_group(INFORMAL_EMPLOYMENT_SHARE - 0.065)
]
# Personal-income-tax revenue the formalization adds by the end of the
# program, percent of GDP, read off the solved transition of the packaged
# calibration (personal income tax 1.4 -> 2.6 percent of GDP by FY2030/31;
# a first estimate from steady-state incidence, 0.7, undershot it).
PIT_FORMALIZATION_GAIN = round(0.012 * float(rebase_factors()[-1]), 5)
# With the statutory schedule as the tax function, the compliance vectors
# above give the *shape* of the formal tax boundary and this scale its
# level: even the top percent remits only part of the tax the schedule
# implies, because much of its income is business and self-employment income
# outside Schedule A. The scale is calibrated so that personal income tax
# collects PIT_REVENUE_TARGET of GDP in FY2024/25
# (examples/tune.py, scored on the first transition year).
COMPLIANCE_SCALE = 0.198381
PIT_REVENUE_TARGET = PIT_REVENUE_SHARE

# Pension coverage by lifetime-income group. Ethiopia's two schemes (PSSSA for
# public servants, POESSA for private formal employees) cover only formal
# employment, a small share of the labour force; the same formality proxy is
# used, so the informal groups draw no public pension.
PENSION_COVERAGE = [0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0]
# The public pension is a defined-benefit scheme (Proclamations 1267/2022 for
# public servants and 1268/2022 for private employees): retirement at 60
# after at least ten years of service, a benefit of 30 percent of the average
# salary of the last three years plus 1.25 percent for every year of service
# beyond ten, capped at 70 percent. A full career from 20 to 60 gives 67.5
# percent. OG-Core's defined-benefit formula is yr_contrib * alpha_db times
# average earnings over avg_earn_num_years, so alpha_db is the replacement
# rate per year of contribution.
PENSIONS_ON = True
PENSION_RETIREMENT_AGE = 60
PENSION_MIN_YEARS = 10
PENSION_BASE_REPLACEMENT = 0.30
PENSION_REPLACEMENT_PER_YEAR = 0.0125
PENSION_MAX_REPLACEMENT = 0.70
PENSION_AVERAGING_YEARS = 3
PENSION_CAREER_YEARS = 40
# The coverage vector above says which groups draw a pension; the scale
# multiplies it so that pension outlays match PENSIONS_SHARE_OF_GDP. The
# formal groups hold 10 percent of households but 40 percent of labor income,
# far more than the scheme's 800,000 pensioners and two percent of the
# working-age population, so the scale is well below one. Calibrated by
# examples/tune.py, scored on the first transition year.
PENSION_COVERAGE_SCALE = 0.876028
# Contributions: 7 percent from the employee and 11 from the employer
# (Proclamations 1267/1268 of 2022). OG-Core's payroll tax can differ by
# lifetime-income group, so the effective rate is the statutory rate on the
# pension-covered groups (the coverage shape above) times a contribution
# scale, zero for the informal groups. The scale is calibrated to
# contributions: about 69 billion birr in FY2024/25, 0.29 percent of rebased
# GDP (POESSA about 29 billion, Reporter 2025; PSSSA about 40 billion,
# extrapolated from 30.5 billion collected in 2023, Addis Fortune). The
# contributions sit inside the 117.8 billion "other" non-tax line of the
# budget outturn. The model's formal groups earn about 40 percent of labor
# income, far more than the real covered wage bill, so the scale is well
# below the pension coverage scale. Contribution data are the least certain
# fiscal anchor here (no official FY2024/25 scheme accounts were found).
PAYROLL_STATUTORY_RATE = 0.18
PAYROLL_REVENUE_SHARE = round(69.0 / 24030.0, 5)
PAYROLL_COVERAGE_SCALE = 0.105

# Personal income tax: the statutory employment-income schedule (Schedule A)
# in birr per month, as (upper bound, marginal rate) with an open last
# bracket. Proclamation 979/2016 applies in FY2024/25 (model period 0) and
# Proclamation 1395/2025, in force from July 2025, from FY2025/26 on.
PIT_SCHEDULE_2016 = [
    (600, 0.0),
    (1650, 0.10),
    (3200, 0.15),
    (5250, 0.20),
    (7800, 0.25),
    (10900, 0.30),
    (None, 0.35),
]
PIT_SCHEDULE_2025 = [
    (2000, 0.0),
    (4000, 0.15),
    (7000, 0.20),
    (10000, 0.25),
    (14000, 0.30),
    (None, 0.35),
]
# Capital income is taxed under Schedule D at flat rates, 10 percent on
# dividends and 5 percent on interest; the model uses the dividend rate.
CAPITAL_INCOME_TAX_RATE = 0.10
# The model's birr are FY2024/25 birr, the start year and the rebased base
# year: mean_income_data is rebased GDP per adult of that year (24,030
# billion birr over the adult population in the middle of the fiscal year,
# World Bank population and age structure, 2024, grown half a year).
# Proclamation 979/2016 applies as written in FY2024/25; the thresholds of
# Proclamation 1395/2025, written in FY2025/26 birr, are deflated by the
# rebased growth of nominal GDP per head between the two years
# (31,860 / 24,030, less population growth) so that they bite at the same
# real incomes. The population is the UN figure the model's demographics use
# (the Ministry of Finance uses 110.6 million).
POPULATION_2024 = 132.06e6
ADULT_SHARE_2024 = (
    0.4986  # aged 20 and over: 1 - 0.3906 (0-14) - 0.1108 (15-19)
)
POPULATION_GROWTH = 0.026
# income grid, birr per year, on which the Gouveia-Strauss form is fitted to
# the schedule: from the old exemption threshold to well past the top decile
# of wage earners (55,000 birr a month)
TAX_FIT_INCOME_RANGE = (12_000.0, 5_000_000.0)
# OG-Core caps the third Gouveia-Strauss parameter; a flat rate is the limit
# of a very large one
GS_FLAT_PHI2 = 2.0e4

# Allocation of the program's revenue gains net of formalization across the
# other instruments: 60 percent to consumption taxes (VAT reform, excises,
# customs) and 40 percent to corporate income tax collections (tax
# administration), following the outturn composition above. FY2024/25 model
# collections these are scaled against: the FY2024/25 outturn mapped to each
# instrument (CONS_TAX_SHARE, CIT_REVENUE_SHARE).
INDIRECT_SHARE_OF_REVENUE_GAIN = 0.6
BASE_CONS_TAX_REVENUE = CONS_TAX_SHARE
BASE_CIT_REVENUE = CIT_REVENUE_SHARE


def program_spending_paths():
    """
    Government spending ratios along the IMF program, mapped onto the model's
    three spending instruments.

    Government consumption is recurrent spending net of interest (which the
    model pays through r_gov) and of cash transfers; transfers are the cash
    items in CASH_TRANSFERS; public investment is capital expenditure. The
    sum reproduces the IMF's primary expenditure to within a tenth of a
    percent of GDP in every program year.

    Returns:
        dict: alpha_G, alpha_T, alpha_I, alpha_FA as lists (length 7 plus
            the long-run value; OG-Core holds the last value thereafter)
    """
    rec = np.array(IMF_RECURRENT) / 100
    interest = np.array(IMF_INTEREST) / 100
    tr = np.array(CASH_TRANSFERS) / 100
    g = rec - interest - tr
    if PENSIONS_ON:
        # pension payouts are paid by the pension system, not as transfers
        tr = tr - PENSIONS_SHARE_OF_GDP / 100
    ig = np.array(IMF_CAPITAL) / 100
    fa = np.array(IMF_GRANTS) / 100
    # shares of market-price GDP -> shares of the model's Y
    return {
        "alpha_G": to_model(list(g) + [g[-1]]),
        "alpha_T": to_model(list(tr) + [tr[-1]]),
        "alpha_I": to_model(list(ig) + [ig[-1]]),
        "alpha_FA": to_model(list(fa) + [LONG_RUN_GRANTS / 100]),
    }


def program_revenue_paths(tau_c_0, cit_factor_0):
    """
    Consumption-tax and CIT-collection paths that raise the model's tax
    revenue by the same percentage points of GDP as the IMF revenue path net
    of what the formalization path delivers, with the remainder allocated per
    INDIRECT_SHARE_OF_REVENUE_GAIN.

    Args:
        tau_c_0 (scalar): FY2024/25 effective consumption-tax rate
        cit_factor_0 (scalar): FY2024/25 CIT collections adjustment factor

    Returns:
        dict: tau_c (list of [rate] per period, I = 1) and
            adjustment_factor_for_cit_receipts (list), each length 7 plus
            the long-run value
    """
    gain = (np.array(IMF_REVENUE) - IMF_REVENUE[0]) / 100
    # the part of the gain the formalization path delivers, phased in with it
    n = len(PROGRAM_YEARS)
    gain = gain - PIT_FORMALIZATION_GAIN * np.arange(n) / (n - 1)
    tau_c = tau_c_0 * (
        1 + INDIRECT_SHARE_OF_REVENUE_GAIN * gain / BASE_CONS_TAX_REVENUE
    )
    cit = cit_factor_0 * (
        1 + (1 - INDIRECT_SHARE_OF_REVENUE_GAIN) * gain / BASE_CIT_REVENUE
    )
    return {
        "tau_c": [[float(x)] for x in list(tau_c) + [tau_c[-1]]],
        "adjustment_factor_for_cit_receipts": [
            float(x) for x in list(cit) + [cit[-1]]
        ],
    }


def program_compliance_paths(
    compliance_scale=None, pension_coverage_scale=None
):
    """
    Income-tax non-compliance paths (labor and capital, identical) that move
    linearly from NONCOMPLIANCE_START to NONCOMPLIANCE_END over the program
    years and stay there, and the pension-coverage matrix.

    Args:
        compliance_scale (scalar): multiplies the compliance (one minus
            non-compliance) of every group at every date; defaults to
            COMPLIANCE_SCALE
        pension_coverage_scale (scalar): multiplies PENSION_COVERAGE;
            defaults to PENSION_COVERAGE_SCALE

    Returns:
        dict: labor_income_tax_noncompliance_rate,
            capital_income_tax_noncompliance_rate (lists of J-vectors, one
            per program year plus the long run) and replacement_rate_adjust
    """
    if compliance_scale is None:
        compliance_scale = COMPLIANCE_SCALE
    if pension_coverage_scale is None:
        pension_coverage_scale = PENSION_COVERAGE_SCALE
    n = len(PROGRAM_YEARS)
    start = 1 - compliance_scale * (1 - np.array(NONCOMPLIANCE_START))
    end = 1 - compliance_scale * (1 - np.array(NONCOMPLIANCE_END))
    path = [
        list(np.round(start + (end - start) * t / (n - 1), 6))
        for t in range(n)
    ] + [list(end)]
    coverage = [float(c * pension_coverage_scale) for c in PENSION_COVERAGE]
    return {
        "labor_income_tax_noncompliance_rate": path,
        "capital_income_tax_noncompliance_rate": [list(r) for r in path],
        "replacement_rate_adjust": [coverage],
    }


def schedule_tax_rates(annual_income, schedule, scale=1.0):
    """
    Effective and marginal rates of a monthly bracket schedule at given
    annual incomes.

    Args:
        annual_income (array_like): income in birr per year
        schedule (list): (monthly upper bound or None, marginal rate) pairs
        scale (scalar): multiplies the bracket thresholds

    Returns:
        etr (Numpy array): tax paid over income
        mtr (Numpy array): marginal rate of the bracket the income falls in
    """
    annual_income = np.asarray(annual_income, dtype=float)
    monthly = annual_income / 12.0
    tax = np.zeros_like(monthly)
    mtr = np.zeros_like(monthly)
    lower = 0.0
    for upper, rate in schedule:
        hi = np.inf if upper is None else upper * scale
        tax += rate * np.clip(monthly - lower, 0.0, hi - lower)
        mtr = np.where((monthly > lower) & (monthly <= hi), rate, mtr)
        lower = hi
    with np.errstate(divide="ignore", invalid="ignore"):
        etr = np.where(annual_income > 0, 12.0 * tax / annual_income, 0.0)
    return etr, mtr


def gs_rates(income, phi, rate_type):
    """
    OG-Core's Gouveia-Strauss tax function.

    Args:
        income (array_like): income in birr per year
        phi (array_like): the three parameters
        rate_type (str): "etr" or "mtr"

    Returns:
        rates (Numpy array): effective or marginal rates
    """
    x = np.asarray(income, dtype=float)
    phi0, phi1, phi2 = phi
    if rate_type == "etr":
        return phi0 * (x - (x**-phi1 + phi2) ** (-1 / phi1)) / x
    return phi0 * (
        1 - x ** (-phi1 - 1) * (x**-phi1 + phi2) ** ((-1 - phi1) / phi1)
    )


def fit_gs_parameters(schedule, scale=1.0):
    """
    Fit OG-Core's Gouveia-Strauss form to a statutory bracket schedule by
    least squares on the effective and marginal rates over a log-spaced
    income grid.

    Args:
        schedule (list): (monthly upper bound or None, marginal rate) pairs
        scale (scalar): multiplies the bracket thresholds

    Returns:
        phi (list): the three parameters, floats
    """
    from scipy import optimize

    incomes = np.logspace(
        np.log10(TAX_FIT_INCOME_RANGE[0]),
        np.log10(TAX_FIT_INCOME_RANGE[1]),
        400,
    )
    etr, mtr = schedule_tax_rates(incomes, schedule, scale)
    top_rate = schedule[-1][1]

    def loss(theta):
        if np.any(np.asarray(theta) <= 0):
            return 1e6
        return np.mean((gs_rates(incomes, theta, "etr") - etr) ** 2) + np.mean(
            (gs_rates(incomes, theta, "mtr") - mtr) ** 2
        )

    best = None
    for phi1 in (0.5, 1.0, 2.0, 4.0):
        for phi2 in (1e-3, 1e-4, 1e-5, 1e-6, 1e-8):
            res = optimize.minimize(
                loss,
                [top_rate, phi1, phi2],
                method="Nelder-Mead",
                options={"xatol": 1e-10, "fatol": 1e-14, "maxiter": 20000},
            )
            if best is None or res.fun < best.fun:
                best = res
    return [float(v) for v in best.x]


def flat_gs_parameters(rate):
    """
    Gouveia-Strauss parameters that reproduce a flat rate.

    Args:
        rate (scalar): the flat tax rate

    Returns:
        phi (list): the three parameters
    """
    return [float(rate), 1.0, GS_FLAT_PHI2]


def mean_income_per_adult():
    """
    Rebased GDP per adult in FY2024/25 birr, the mean_income_data that
    converts the
    model's income units into the birr the tax schedule is written in.

    Returns:
        float: birr per year
    """
    adults = POPULATION_2024 * (1 + POPULATION_GROWTH / 2) * ADULT_SHARE_2024
    return NOMINAL_GDP_REBASED_BIRR_BN["FY2024/25"] * 1e9 / adults


def statutory_tax_params():
    """
    Income-tax function parameters from the statutory schedules: the
    FY2024/25 schedule in the first period and the 2025 schedule (deflated
    to FY2024/25 birr) thereafter for effective and labor marginal rates,
    a flat
    dividend rate on capital income, and the birr-per-model-unit anchor.

    Returns:
        dict: tax_func_type, etr_params, mtrx_params, mtry_params,
            mean_income_data
    """
    nominal_growth_per_head = (
        NOMINAL_GDP_REBASED_BIRR_BN["FY2025/26"]
        / NOMINAL_GDP_REBASED_BIRR_BN["FY2024/25"]
    ) / (1 + POPULATION_GROWTH)
    phi_2016 = fit_gs_parameters(PIT_SCHEDULE_2016)
    phi_2025 = fit_gs_parameters(
        PIT_SCHEDULE_2025, 1 / nominal_growth_per_head
    )
    labor = [[phi_2016], [phi_2025]]
    return {
        "tax_func_type": "GS",
        "etr_params": labor,
        "mtrx_params": [[list(p) for p in row] for row in labor],
        "mtry_params": [[flat_gs_parameters(CAPITAL_INCOME_TAX_RATE)]],
        "mean_income_data": float(mean_income_per_adult()),
    }


def defined_benefit_params():
    """
    OG-Core defined-benefit pension parameters for Ethiopia's schemes.

    Returns:
        dict: pension_system, retirement_age, yr_contrib,
            avg_earn_num_years, alpha_db
    """
    replacement = min(
        PENSION_BASE_REPLACEMENT
        + PENSION_REPLACEMENT_PER_YEAR
        * (PENSION_CAREER_YEARS - PENSION_MIN_YEARS),
        PENSION_MAX_REPLACEMENT,
    )
    return {
        "pension_system": "Defined Benefits",
        "retirement_age": [PENSION_RETIREMENT_AGE],
        "yr_contrib": PENSION_CAREER_YEARS,
        "avg_earn_num_years": PENSION_AVERAGING_YEARS,
        # OG-Core >= 0.21 takes alpha_db by year and lifetime-income group
        "alpha_db": [[replacement / PENSION_CAREER_YEARS]],
    }


def payroll_tax_params(payroll_coverage_scale=None):
    """
    Effective payroll tax by lifetime-income group: the statutory pension
    contribution rate on the covered groups times the contribution scale.

    Args:
        payroll_coverage_scale (scalar): defaults to PAYROLL_COVERAGE_SCALE

    Returns:
        dict: tau_payroll as a (1, J) nested list
    """
    if payroll_coverage_scale is None:
        payroll_coverage_scale = PAYROLL_COVERAGE_SCALE
    return {
        "tau_payroll": [
            [
                round(PAYROLL_STATUTORY_RATE * c * payroll_coverage_scale, 6)
                for c in PENSION_COVERAGE
            ]
        ]
    }


# Foreign share of net new government borrowing along the program. With debt
# falling, zeta_D is the share of the decline borne by external creditors; the
# IMF path has external debt falling from 31.8 to 16.7 percent of GDP while
# domestic debt falls from 18.7 to 11.9, i.e. amortization to external
# creditors carries most of the adjustment (CR 26/174, Table 1). The long-run
# value is the calibrated 0.15 (macro.md).
LONG_RUN_ZETA_D = 0.15

# Cash transfers by programme, percent of GDP, long run (see CASH_TRANSFERS):
# the Productive Safety Net Program goes to the poorest households, public
# pensions to retired formal-sector workers, the fertilizer subsidy to farming
# households. OG-Core's eta matrix allocates aggregate transfers across ages
# and lifetime-income groups; the default is population-proportional.
# published percent of old-base GDP, rebased with the FY2024/25 factor
PSNP_SHARE_OF_GDP = rebased([0.4])[0]
PENSIONS_SHARE_OF_GDP = rebased([0.5])[0]
FERTILIZER_SUBSIDY_SHARE_OF_GDP = rebased([0.6])[0]
PSNP_GROUPS = [0]  # poorest quarter of households
FARM_GROUPS = [0, 1, 2]  # bottom 70 percent: smallholder agriculture
PENSION_GROUPS = [5, 6]  # the formal groups, as in PENSION_COVERAGE


def program_zeta_D_path():
    """
    zeta_D path: the external creditors' share of each program year's change
    in the debt ratio, clipped to [0, 1], then LONG_RUN_ZETA_D.

    Returns:
        list: length 7 plus the long-run value (period 0 uses period 1's)
    """
    tot = np.array(IMF_PUBLIC_DEBT)
    # general-government external debt: the total less domestic debt (the
    # same in both perimeters)
    ext = tot - np.array(IMF_DOMESTIC_DEBT)
    share = np.clip(np.diff(ext) / np.diff(tot), 0.0, 1.0)
    return [float(share[0])] + [float(x) for x in share] + [LONG_RUN_ZETA_D]


def transfer_eta(omega_SS, lambdas, retire_age_index):
    """
    Allocation matrix eta distributing aggregate transfers across households,
    shaped (S, J): the safety net per capita within PSNP_GROUPS, the
    fertilizer subsidy per capita within FARM_GROUPS, and pensions per
    capita among the retired (age index >= retire_age_index) in
    PENSION_GROUPS, each programme weighted by its share of GDP.

    Returns:
        Numpy array: (S, J), sums to one
    """
    omega_SS = np.asarray(omega_SS, dtype=float)
    S, J = omega_SS.shape
    eta = np.zeros((S, J))

    def spread(groups, ages, weight):
        mask = np.zeros((S, J))
        mask[np.ix_(ages, groups)] = omega_SS[np.ix_(ages, groups)]
        return weight * mask / mask.sum()

    eta += spread(PSNP_GROUPS, range(S), PSNP_SHARE_OF_GDP)
    eta += spread(FARM_GROUPS, range(S), FERTILIZER_SUBSIDY_SHARE_OF_GDP)
    if not PENSIONS_ON:
        # pensions inside the cash-transfer ratio, to the retired formal
        # groups; with the pension system on they are paid as benefits
        eta += spread(
            PENSION_GROUPS, range(retire_age_index, S), PENSIONS_SHARE_OF_GDP
        )
    return eta / eta.sum()


def derived_transfer_eta(p):
    """The transfer allocation matrix for the demographics in ``p``."""
    retire_idx = int(np.asarray(p.retirement_age).flatten()[0]) - int(p.E)
    return {"eta": transfer_eta(p.omega_SS, p.lambdas, retire_idx).tolist()}


def implied_real_rate_on_debt(g_y, g_n):
    """
    Real effective interest rate on public debt that reproduces the IMF
    debt path given the program's primary balances and the model's growth.

    In the model's detrended units debt evolves as
    d_t = ((1 + r_t) d_{t-1} - pb_{t-1}) / (exp(g_y) (1 + g_n[t])), so the
    rate that carries the ratio from one program year to the next is
    r_t = (d_t growth_t + pb_{t-1}) / d_{t-1} - 1. The program's debt
    decline works through inflation and nominal growth eroding a stock that
    carries concessional and administered rates; in a real model that is a
    negative real effective rate on the legacy debt.

    Args:
        g_y (scalar): model-period productivity growth rate
        g_n (array_like): population growth path

    Returns:
        Numpy array: r_gov for periods 1..6 (period 0 has no predecessor)
    """
    d = np.array(IMF_PUBLIC_DEBT) / 100
    rev = np.array(IMF_REVENUE) / 100
    sp = program_spending_paths()

    def mkt(key):
        # spending paths are in model units; the identity is in data units
        return np.array(sp[key][:7]) / MODEL_PER_MARKET_GDP

    pb = (
        rev
        + mkt("alpha_FA")
        - mkt("alpha_G")
        - mkt("alpha_T")
        - mkt("alpha_I")
    )
    if PENSIONS_ON:
        # pension benefits are primary spending too, paid by the scheme
        pb = pb - PENSIONS_SHARE_OF_GDP / 100
    growth = np.exp(g_y) * (1 + np.asarray(g_n, dtype=float)[:7])
    return np.array(
        [(d[t] * growth[t] + pb[t - 1]) / d[t - 1] - 1 for t in range(1, 7)]
    )


def r_gov_shift_path(g_y, g_n, r_gov_scale, r_gov_DY2, debt_ratio_ss, r_ss):
    """
    Level-shift path for the sovereign rate, r_gov = r_gov_scale r - shift +
    premium, that puts the real effective rate on debt on the program-implied
    path, converges it linearly to LONG_RUN_R_GOV over
    R_GOV_CONVERGENCE_PERIODS, and keeps the debt-elastic premium centered on
    debt_ratio_ss (see macro.md). The market return r is approximated by its
    steady-state value; along the transition r moves by at most a percentage
    point, which the 0.24 scale turns into a few basis points of r_gov.

    Returns:
        list: r_gov_shift path, length 7 + R_GOV_CONVERGENCE_PERIODS + 1
    """
    # debt ratios in model units, the units of OG-Core's premium term
    d = np.array(to_model(np.array(IMF_PUBLIC_DEBT) / 100))
    r_prog = implied_real_rate_on_debt(g_y, g_n)
    targets = np.concatenate(
        [
            [r_prog[0]],  # period 0: no program-implied value; use period 1
            r_prog,
            np.linspace(
                r_prog[-1], LONG_RUN_R_GOV, R_GOV_CONVERGENCE_PERIODS + 2
            )[1:],
        ]
    )
    debt = np.concatenate(
        [d, np.full(R_GOV_CONVERGENCE_PERIODS + 1, debt_ratio_ss)]
    )
    # OG-Core adds r_gov_DY d + r_gov_DY2 d^2 with r_gov_DY = -2 r_gov_DY2 D,
    # which equals r_gov_DY2 (d - D)^2 - r_gov_DY2 D^2; the shift absorbs the
    # constant so the premium is exactly zero at the target.
    centering = r_gov_DY2 * debt_ratio_ss**2
    shift = (
        r_gov_scale * r_ss
        + r_gov_DY2 * (debt - debt_ratio_ss) ** 2
        - centering
        - targets
    )
    return [float(x) for x in shift]


def fiscal_program_params(p, r_ss=None):
    """
    All fiscal parameters that follow the IMF program path, derived from the
    Specifications object's growth and premium settings.

    Args:
        p (Specifications): parameters carrying g_y, g_n, r_gov_scale,
            r_gov_DY2, debt_ratio_ss, tau_c, adjustment_factor_for_cit_receipts
        r_ss (scalar): steady-state market return used in r_gov_shift_path;
            defaults to R_SS_FOR_R_GOV

    Returns:
        dict: ready for Specifications.update_specifications
    """
    if r_ss is None:
        r_ss = R_SS_FOR_R_GOV
    out = {}
    out.update(program_spending_paths())
    out.update(program_compliance_paths())
    out["zeta_D"] = program_zeta_D_path()
    out.update(derived_transfer_eta(p))
    out.update(
        program_revenue_paths(
            float(np.asarray(p.tau_c).flatten()[0]),
            float(
                np.asarray(p.adjustment_factor_for_cit_receipts).flatten()[0]
            ),
        )
    )
    out["r_gov_shift"] = r_gov_shift_path(
        p.g_y,
        p.g_n,
        float(np.asarray(p.r_gov_scale).flatten()[0]),
        float(p.r_gov_DY2),
        PROGRAM_DEBT_RATIO_SS,
        r_ss,
    )
    out["initial_debt_ratio"] = INITIAL_DEBT_RATIO
    out["initial_foreign_debt_ratio"] = GG_FOREIGN_DEBT_SHARE
    out["debt_ratio_ss"] = PROGRAM_DEBT_RATIO_SS
    out["r_gov_DY"] = -2 * float(p.r_gov_DY2) * PROGRAM_DEBT_RATIO_SS
    out["tG1"] = len(PROGRAM_YEARS)
    out.update(remittance_level_params(scenario="program"))
    out.update(common_params())
    return out


# ---------------------------------------------------------------------------
# Capital stocks, depreciation and initial household wealth
#
# Total capital: Penn World Table 11.0 (October 2025) capital stock at
# current PPPs over output, cn / cgdpo = 2.167 in 2023, the latest year (2.17
# to 2.26 over 2020-2023). Public capital: IMF Investment and Capital Stock
# Dataset (April 2025) general-government stock, 0.667 of GDP in 2019, its
# latest year. Both are measured against the old national accounts; the
# rebased accounts have not yet produced capital stocks, and the new
# expenditure accounts revise investment up by more than GDP (gross capital
# formation 35.3 against 20.1 percent of GDP in FY2024/25). We assume the
# stocks are revised in proportion to GDP, so the capital-output ratios carry
# over; this is the provisional element of the calibration and is reported
# as such (macro.md). The private stock is the total less public capital.
PWT_CAPITAL_OUTPUT_RATIO = 2.167
PUBLIC_CAPITAL_OUTPUT_RATIO = 0.667
PRIVATE_CAPITAL_OUTPUT_RATIO = round(
    PWT_CAPITAL_OUTPUT_RATIO - PUBLIC_CAPITAL_OUTPUT_RATIO, 3
)
# Depreciation of private capital: PWT 11.0's depreciation rate of the total
# stock, 0.0414 in 2023, less public capital's share depreciating at
# delta_g = 0.02 (OG-Core's default public-capital rate, kept), so that
# delta_p (K - K_g) + delta_g K_g = 0.0414 K.
PWT_DEPRECIATION_RATE = 0.0414
DELTA_G_ANNUAL = 0.02
DELTA_ANNUAL = round(
    (
        PWT_DEPRECIATION_RATE
        - PUBLIC_CAPITAL_OUTPUT_RATIO
        / PWT_CAPITAL_OUTPUT_RATIO
        * DELTA_G_ANNUAL
    )
    / (1 - PUBLIC_CAPITAL_OUTPUT_RATIO / PWT_CAPITAL_OUTPUT_RATIO),
    4,
)
# Foreign-owned capital: UNCTAD World Investment Report 2026 inward FDI
# stock, USD 42.5 billion at end-2024 and 46.3 billion at end-2025
# (estimates); the mid-year average over rebased FY2024/25 GDP of USD 201.4
# billion. Ethiopia publishes no international investment position, so the
# FDI stock is the foreign-owned capital measure.
FDI_STOCK_USD_BN = (42.528 + 46.324) / 2
FDI_STOCK_TO_GDP = round(FDI_STOCK_USD_BN / 201.42, 4)
# foreign-owned share of private capital in FY2024/25, the zeta_K target
FOREIGN_CAPITAL_SHARE = round(
    FDI_STOCK_TO_GDP / PRIVATE_CAPITAL_OUTPUT_RATIO, 4
)
# Domestically held general-government debt, FY2024/25
DOMESTIC_DEBT_TO_GDP = round(IMF_DOMESTIC_DEBT[0] / 100, 4)
# OG-Core (0.22 and later, PSLmodels/OG-Core#1254) anchors aggregate
# household wealth in the first period of the transition to a multiple of
# that period's GDP. Household wealth in the model is domestically owned
# private capital plus domestically held government debt, so the data
# counterpart is private K/Y less the foreign-owned stock plus domestic debt,
# converted to the model's output basis.
INITIAL_WEALTH_RATIO = round(
    to_model(
        PRIVATE_CAPITAL_OUTPUT_RATIO - FDI_STOCK_TO_GDP + DOMESTIC_DEBT_TO_GDP
    ),
    3,
)
INITIAL_KG_RATIO = round(to_model(PUBLIC_CAPITAL_OUTPUT_RATIO), 3)


# ---------------------------------------------------------------------------
# Baseline scenarios
#
# The packaged baseline is history-anchored: every fiscal and external input
# takes its measured FY2024/25 value or the enacted FY2025/26 budget and is
# held there, legislated tax changes included, and debt, growth and the
# external balance are model outcomes. The IMF program path is kept as a
# scenario (fiscal_program_params) that the example can overlay; the two are
# compared in macro.md.
# ---------------------------------------------------------------------------
SCENARIOS = ("history", "program")
DEFAULT_SCENARIO = "history"
# Fiscal years whose ratios are known when the baseline is built: the
# FY2024/25 outturn (model period 0) and the enacted FY2025/26 budget
# (period 1); the budget-year values are held for the long run.
HISTORY_KNOWN_YEARS = 2
# History-anchored long-run debt ratio: the measured FY2024/25 ratio, so the
# closure rule stabilizes debt where it starts rather than at a plan.
HISTORY_DEBT_RATIO_SS = INITIAL_DEBT_RATIO


def check_scenario(scenario):
    """
    Validate a scenario name, defaulting to DEFAULT_SCENARIO.

    Args:
        scenario (str or None): one of SCENARIOS

    Returns:
        str: the scenario
    """
    if scenario is None:
        return DEFAULT_SCENARIO
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}: {scenario}")
    return scenario


def _held(path, known=HISTORY_KNOWN_YEARS):
    """First ``known`` values of ``path``, then the last known value held."""
    path = list(path)
    return path[:known] + [path[known - 1]] * (len(path) - known)


def history_spending_paths():
    """
    Spending ratios of the history-anchored baseline: the FY2024/25 outturn
    and the enacted FY2025/26 budget (the first two program-table columns),
    the budget-year values held thereafter.

    Returns:
        dict: alpha_G, alpha_T, alpha_I, alpha_FA, same lengths as
            program_spending_paths
    """
    return {k: _held(v) for k, v in program_spending_paths().items()}


def history_revenue_paths(tau_c_0, cit_factor_0):
    """
    Effective consumption-tax rate and CIT collections factor held at their
    FY2024/25 values (no program revenue measures).

    Args:
        tau_c_0 (scalar): FY2024/25 effective consumption-tax rate
        cit_factor_0 (scalar): FY2024/25 CIT collections adjustment factor

    Returns:
        dict: tau_c and adjustment_factor_for_cit_receipts, same lengths as
            program_revenue_paths
    """
    n = len(PROGRAM_YEARS) + 1
    return {
        "tau_c": [[float(tau_c_0)]] * n,
        "adjustment_factor_for_cit_receipts": [float(cit_factor_0)] * n,
    }


def history_compliance_paths(
    compliance_scale=None, pension_coverage_scale=None
):
    """
    Income-tax non-compliance held at its FY2024/25 calibration (no
    formalization along the program); the pension-coverage matrix is the
    same as in the program scenario.

    Args:
        compliance_scale, pension_coverage_scale: see
            program_compliance_paths

    Returns:
        dict: see program_compliance_paths
    """
    d = program_compliance_paths(compliance_scale, pension_coverage_scale)
    n = len(d["labor_income_tax_noncompliance_rate"])
    start = list(d["labor_income_tax_noncompliance_rate"][0])
    d["labor_income_tax_noncompliance_rate"] = [list(start) for _ in range(n)]
    d["capital_income_tax_noncompliance_rate"] = [
        list(start) for _ in range(n)
    ]
    return d


def compliance_paths(
    scenario=None, compliance_scale=None, pension_coverage_scale=None
):
    """Compliance paths of a scenario (see program_compliance_paths)."""
    if check_scenario(scenario) == "program":
        return program_compliance_paths(
            compliance_scale, pension_coverage_scale
        )
    return history_compliance_paths(compliance_scale, pension_coverage_scale)


def history_zeta_D_path():
    """
    Foreign share of new government borrowing held at LONG_RUN_ZETA_D. The
    FY2024/25 realized flow is a restructuring-year outlier and the stock
    share (0.63) is a poor guide to new borrowing while external debt is
    being restructured, so the medium-term flow share the debt sustainability
    analysis projects is the one forward-looking input this baseline keeps
    (macro.md).

    Returns:
        list: same length as program_zeta_D_path
    """
    return [LONG_RUN_ZETA_D] * (len(PROGRAM_YEARS) + 1)


def history_real_rate_on_debt(g_y, g_n):
    """
    Real effective rate on public debt for the history-anchored baseline:
    the rate the FY2024/25 outturn and the FY2025/26 budget imply for the
    stock (the first program-implied value), held through the program
    horizon before converging to LONG_RUN_R_GOV.

    Args:
        g_y (scalar): model-period productivity growth rate
        g_n (array_like): population growth path

    Returns:
        float: real effective rate
    """
    return float(implied_real_rate_on_debt(g_y, g_n)[0])


def history_r_gov_shift_path(
    g_y, g_n, r_gov_scale, r_gov_DY2, debt_ratio_ss, r_ss
):
    """
    Level-shift path for the sovereign rate in the history-anchored
    baseline: the budget-implied real effective rate held for the program
    horizon, then a linear convergence to LONG_RUN_R_GOV over
    R_GOV_CONVERGENCE_PERIODS. The debt path is a model outcome here, so
    the shift is evaluated at the debt anchor (premium exactly zero there,
    as in r_gov_shift_path) and the premium prices deviations from it as
    they occur.

    Args:
        g_y (scalar): model-period productivity growth rate
        g_n (array_like): population growth path
        r_gov_scale (scalar): pass-through of the market return
        r_gov_DY2 (scalar): curvature of the debt-elastic premium
        debt_ratio_ss (scalar): debt anchor the premium is centered on
        r_ss (scalar): steady-state market return

    Returns:
        list: r_gov_shift path, same length as r_gov_shift_path
    """
    n = len(PROGRAM_YEARS)
    r0 = history_real_rate_on_debt(g_y, g_n)
    targets = np.concatenate(
        [
            np.full(n, r0),
            np.linspace(r0, LONG_RUN_R_GOV, R_GOV_CONVERGENCE_PERIODS + 2)[1:],
        ]
    )
    centering = r_gov_DY2 * debt_ratio_ss**2
    return [float(x) for x in r_gov_scale * r_ss - centering - targets]


def history_anchored_params(p, r_ss=None):
    """
    All fiscal and external parameters of the history-anchored baseline,
    derived from the Specifications object's growth and premium settings.

    Args:
        p (Specifications): parameters carrying g_y, g_n, r_gov_scale,
            r_gov_DY2, tau_c, adjustment_factor_for_cit_receipts
        r_ss (scalar): steady-state market return used in the shift path;
            defaults to R_SS_FOR_R_GOV

    Returns:
        dict: ready for Specifications.update_specifications
    """
    if r_ss is None:
        r_ss = R_SS_FOR_R_GOV
    out = {}
    out.update(history_spending_paths())
    out.update(history_compliance_paths())
    out["zeta_D"] = history_zeta_D_path()
    out.update(derived_transfer_eta(p))
    out.update(
        history_revenue_paths(
            float(np.asarray(p.tau_c).flatten()[0]),
            float(
                np.asarray(p.adjustment_factor_for_cit_receipts).flatten()[0]
            ),
        )
    )
    out["r_gov_shift"] = history_r_gov_shift_path(
        p.g_y,
        p.g_n,
        float(np.asarray(p.r_gov_scale).flatten()[0]),
        float(p.r_gov_DY2),
        HISTORY_DEBT_RATIO_SS,
        r_ss,
    )
    out["initial_debt_ratio"] = INITIAL_DEBT_RATIO
    out["initial_foreign_debt_ratio"] = GG_FOREIGN_DEBT_SHARE
    out["debt_ratio_ss"] = HISTORY_DEBT_RATIO_SS
    out["r_gov_DY"] = -2 * float(p.r_gov_DY2) * HISTORY_DEBT_RATIO_SS
    out["tG1"] = len(PROGRAM_YEARS)
    out.update(remittance_level_params(scenario="history"))
    out.update(common_params())
    return out


def common_params():
    """
    Parameters both scenarios share: the statutory income tax, the pension
    scheme and its contributions, capital, depreciation and the initial
    conditions.

    Returns:
        dict: ready for Specifications.update_specifications
    """
    out = {}
    out.update(statutory_tax_params())
    if PENSIONS_ON:
        out.update(defined_benefit_params())
        out.update(payroll_tax_params())
    out.update(
        {
            "delta_annual": DELTA_ANNUAL,
            "delta_g_annual": DELTA_G_ANNUAL,
            "initial_Kg_ratio": INITIAL_KG_RATIO,
            "initial_wealth_ratio": INITIAL_WEALTH_RATIO,
            "r_gov_floor": R_GOV_FLOOR,
            "nu": NU,
            "TPI_outer_method": "anderson",
            "TPI_anderson_m": TPI_ANDERSON_M,
            "TPI_anderson_beta": TPI_ANDERSON_BETA,
        }
    )
    return out


def scenario_params(p, scenario=None, r_ss=None):
    """
    The fiscal, external and remittance parameters of a baseline scenario.

    Args:
        p (Specifications): see history_anchored_params
        scenario (str): one of SCENARIOS; defaults to DEFAULT_SCENARIO
        r_ss (scalar): see history_anchored_params

    Returns:
        dict: ready for Specifications.update_specifications
    """
    scenario = check_scenario(scenario)
    if scenario == "program":
        out = fiscal_program_params(p, r_ss)
    else:
        out = history_anchored_params(p, r_ss)
    out.update(derived_remittance_params(p, scenario))
    return out

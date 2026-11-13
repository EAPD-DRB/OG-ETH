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
# Last year of UN data the demographics read. ogcore holds fertility,
# mortality and immigration at final_data_year forever after, so the window
# sets the long-run population growth rate: with start_year + 1 the model
# froze Ethiopia's current growth (2.6 percent a year) as its steady state.
# Reading the UN projection to its end lets growth fall as the projection
# says. get_pop reads final_data_year + 1, and the Population-Data archive
# (used when no UN API token is registered) ends in 2099, so 2098 is the
# last usable year; ogcore also caps it at start_year + 74.
DEMOG_FINAL_DATA_YEAR = 2098
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


# Discount-factor step used by examples/tune.py, which calibrates chi_n to
# hours by age and the relative discount factors to WID wealth shares in the
# steady state, and the remaining dials to first-year (FY2024/25) moments:
# a group's steady-state wealth is very elastic to its beta, so the update is
# damped and each step bounded.
BETA_DAMPING = 0.3
BETA_STEP = 1.03
BETA_BOUNDS = (0.5, 0.995)
# OG-USA's bequest weight, kept for every group
CHI_B_DEFAULT = 80.0


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
            final_data_year=DEMOG_FINAL_DATA_YEAR,
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

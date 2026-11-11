"""
Data targets for the OG-ETH calibration dashboard, and the functions that
compute the matching model moments from a solved ``SS_vars.pkl`` or
``TPI_vars.pkl``.

Every ratio is to Ethiopia's rebased GDP (base year FY2024/25, Ministry of
National Strategy, November 2026) at market prices. OG-Core's output Y is
GDP before consumption taxes, so model moments are divided by Y plus the
consumption tax (see ``ogeth.macro_params.MODEL_PER_MARKET_GDP``).

Two sets of targets:

* ``TRANSITION_TARGETS`` are moments of the first model period, FY2024/25,
  the year the data describe. The dials tuned to them are the tax rates and
  scales (revenue by instrument), the pension and payroll coverage scales,
  the level of the discount factors (first-year investment) and the
  foreign-capital fill share zeta_K (first-year foreign share of private
  capital). Ethiopia's population is far from stationary, so these are
  scored where the data are, not in the steady state.
* ``SS_TARGETS`` are long-run anchors and the survey distributions that the
  steady state is matched to (hours by age and wealth shares are scored by
  ``ogeth.calibrate``), plus moments reported as outcomes.
"""

import numpy as np

from ogeth import macro_params as mp

# moment: (target, dial, source)
TRANSITION_TARGETS = {
    "PIT/Y": (
        mp.PIT_REVENUE_SHARE,
        "compliance scale",
        "personal income tax 194.3 bn birr, FY2024/25 outturn (NBE Annual "
        "Report 2024/25, Table 6.3)",
    ),
    "CIT/Y": (
        mp.CIT_REVENUE_SHARE,
        "adjustment_factor_for_cit_receipts",
        "business profit tax 229.6 + other income taxes 52.9 + government "
        "investment income 20.0 bn birr (NBE AR 2024/25)",
    ),
    "cons tax/Y": (
        mp.CONS_TAX_SHARE,
        "tau_c",
        "indirect taxes 650.9 + charges and fees 39.4 + sales of goods and "
        "services 32.8 bn birr (NBE AR 2024/25)",
    ),
    "wealth tax/Y": (
        mp.WEALTH_TAX_SHARE,
        "p_wealth",
        "rural and urban land-use fees 44.1 bn birr (NBE AR 2024/25)",
    ),
    "payroll/Y": (
        mp.PAYROLL_REVENUE_SHARE,
        "payroll coverage scale",
        "pension contributions about 69 bn birr (POESSA ~29, PSSSA ~40, "
        "estimates)",
    ),
    "pensions/Y": (
        mp.PENSIONS_SHARE_OF_GDP / 100,
        "pension coverage scale",
        "public pension outlays 0.5 percent of old-base GDP (IMF CR 26/174), "
        "rebased",
    ),
    "(I+I_g)/Y": (
        mp.GROSS_CAPITAL_FORMATION_REBASED / 100,
        "discount factor level",
        "gross capital formation 35.3 percent of rebased GDP (rebased "
        "national accounts, FY2024/25)",
    ),
    "K_f/K": (
        mp.FOREIGN_CAPITAL_SHARE,
        "zeta_K",
        "inward FDI stock 0.221 of GDP (UNCTAD WIR 2026) over private K/Y "
        "1.50 (PWT 11.0 less IMF ICSD public capital)",
    ),
    "B/Y": (
        mp.INITIAL_WEALTH_RATIO / mp.MODEL_PER_MARKET_GDP,
        "initial_wealth_ratio (imposed)",
        "private K/Y less FDI stock plus domestic debt",
    ),
    "D/Y": (
        mp.IMF_PUBLIC_DEBT[0] / 100,
        "initial_debt_ratio (imposed)",
        "general-government debt 43.3 percent of old-base GDP (IMF WEO "
        "October 2026), rebased",
    ),
    # scored, not tuned
    "C/Y purch.": (
        mp.PRIVATE_CONSUMPTION_REBASED / 100,
        "check",
        "private consumption 64.4 percent of rebased GDP",
    ),
    "G/Y": (
        mp.GOVERNMENT_CONSUMPTION_REBASED / 100,
        "check",
        "government consumption, derived from the rebased accounts (about "
        "4.7); the fiscal-accounts mapping gives 2.8",
    ),
    "NX/Y": (
        mp.IMF_TRADE_BALANCE[0] / 100,
        "check",
        "goods and services balance USD -8.9 bn (IMF CR 26/174 Table 4a) "
        "over rebased GDP",
    ),
    "RM/Y": (
        mp.IMF_PRIVATE_TRANSFERS[0] / 100,
        "alpha_RM (imposed)",
        "net private transfers USD 7.04 bn (IMF CR 26/174)",
    ),
    "factor payments/Y": (
        752.0 / 201420.0,
        "check",
        "net primary income paid abroad USD 0.75 bn (IMF CR 26/174 Table 4a)",
    ),
    "total tax/Y": (
        (1172 + 39.4 + 32.8 + 20.0) / 24030 + mp.PAYROLL_REVENUE_SHARE,
        "check",
        "sum of the mapped instruments",
    ),
}

# Long-run anchors and outcomes, scored on the steady state
SS_TARGETS = {
    "D/Y": (mp.INITIAL_DEBT_RATIO / mp.MODEL_PER_MARKET_GDP, "debt_ratio_ss"),
    "r_gov": (mp.LONG_RUN_R_GOV, "r_gov_shift (long run)"),
    "K/Y": (mp.PRIVATE_CAPITAL_OUTPUT_RATIO, "outcome (provisional anchor)"),
}


def _market_y(y, cons_tax):
    return y + cons_tax


def tpi_moments(tpi, t=0):
    """
    Transition moments in period t as shares of GDP at market prices.

    Args:
        tpi (dict): a solved ``TPI_vars.pkl``
        t (int): model period, 0 for FY2024/25

    Returns:
        m (dict): moments keyed like ``TRANSITION_TARGETS``, plus extras
    """

    def at(key):
        x = np.asarray(tpi[key])
        x = x.reshape(x.shape[0], -1).sum(axis=1) if x.ndim > 1 else x
        return float(x[t])

    Ym = at("Y")
    Y = _market_y(Ym, at("cons_tax_revenue"))
    r_p = at("r_p")
    nx = Ym - at("C") - at("I_total") - at("I_g") - at("G")
    return {
        "PIT/Y": at("iit_revenue") / Y,
        "CIT/Y": at("business_tax_revenue") / Y,
        "cons tax/Y": at("cons_tax_revenue") / Y,
        "wealth tax/Y": at("wealth_tax_revenue") / Y,
        "payroll/Y": at("payroll_tax_revenue") / Y,
        "pensions/Y": at("agg_pension_outlays") / Y,
        "(I+I_g)/Y": (at("I_total") + at("I_g")) / Y,
        "K_f/K": at("K_f") / at("K"),
        "B/Y": at("B") / Y,
        "D/Y": at("D") / Y,
        "C/Y purch.": (at("C") + at("cons_tax_revenue")) / Y,
        "G/Y": at("G") / Y,
        "NX/Y": nx / Y,
        "RM/Y": at("RM") / Y,
        "factor payments/Y": r_p * (at("K_f") + at("D_f")) / Y,
        "total tax/Y": at("total_tax_revenue") / Y,
        "K/Y": at("K") / Y,
        "r": at("r"),
        "r_gov": at("r_gov"),
    }


def ss_moments(ss):
    """
    Steady-state moments as shares of GDP at market prices.

    Args:
        ss (dict): a solved ``SS_vars.pkl``

    Returns:
        m (dict): moments
    """

    def sc(key):
        return float(np.sum(ss[key]))

    Ym = float(np.squeeze(ss["Y"]))
    Y = _market_y(Ym, sc("cons_tax_revenue"))
    nx = Ym - sc("C") - sc("I_total") - sc("I_g") - sc("G")
    return {
        "PIT/Y": sc("iit_revenue") / Y,
        "CIT/Y": sc("business_tax_revenue") / Y,
        "cons tax/Y": sc("cons_tax_revenue") / Y,
        "wealth tax/Y": sc("wealth_tax_revenue") / Y,
        "payroll/Y": sc("payroll_tax_revenue") / Y,
        "pensions/Y": sc("agg_pension_outlays") / Y,
        "total tax/Y": sc("total_tax_revenue") / Y,
        "D/Y": sc("D") / Y,
        "D_f/D": sc("D_f") / sc("D") if sc("D") else np.nan,
        "G/Y": sc("G") / Y,
        "TR/Y": sc("TR") / Y,
        "I_g/Y": sc("I_g") / Y,
        "(I+I_g)/Y": (sc("I_total") + sc("I_g")) / Y,
        "K/Y": sc("K") / Y,
        "K_f/K": sc("K_f") / sc("K"),
        "B/Y": sc("B") / Y,
        "C/Y purch.": (sc("C") + sc("cons_tax_revenue")) / Y,
        "NX/Y": nx / Y,
        "RM/Y": sc("RM") / Y,
        "r": sc("r"),
        "r_gov": sc("r_gov"),
        "factor": sc("factor"),
    }

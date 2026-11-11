---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

(Chap_Tax)=
# Taxes in OG-ETH

```{code-cell} ipython3
:tags: ["remove-cell"]

from importlib.resources import files
import json
from myst_nb import glue

params = json.loads(
    files("ogeth")
    .joinpath("ogeth_default_parameters.json")
    .read_text(encoding="utf-8")
)

def pct(value):
    return f"{100 * value:.0f}%"

from ogeth import macro_params as mp

def pct1(value):
    return f"{100 * value:.1f}%"

def pct2(value):
    return f"{100 * value:.2f}%"

glue("payroll_top", pct1(params["tau_payroll"][0][-1]), display=False)
glue("payroll_g6", pct1(params["tau_payroll"][0][-2]), display=False)
glue("payroll_scale", f"{mp.PAYROLL_COVERAGE_SCALE:.2f}", display=False)
glue("cit_rate", pct(params["cit_rate"][0][0]), display=False)
glue("tau_c_rate", pct1(params["tau_c"][0][0]), display=False)
glue(
    "cit_adj_factor",
    f"{params['adjustment_factor_for_cit_receipts'][0]:.3f}",
    display=False,
)
glue("p_wealth", f"{params['p_wealth'][0]:.5f}", display=False)
glue("compliance_scale", f"{mp.COMPLIANCE_SCALE:.3f}", display=False)
glue("pension_scale", f"{mp.PENSION_COVERAGE_SCALE:.3f}", display=False)
glue("mean_income", f"{params['mean_income_data']:,.0f}", display=False)
glue("pit_target", pct2(mp.PIT_REVENUE_SHARE), display=False)
glue("cit_target", pct2(mp.CIT_REVENUE_SHARE), display=False)
glue("ctax_target", pct2(mp.CONS_TAX_SHARE), display=False)
glue("wealth_target", pct2(mp.WEALTH_TAX_SHARE), display=False)
glue("payroll_target", pct2(mp.PAYROLL_REVENUE_SHARE), display=False)
```

The government is not an optimizing agent in `OG-ETH`. The government levies taxes on household income, corporate income, and value added. With these resources, the government provides transfers to households, spends resources on public goods, and makes rule-based adjustments to stabilize the economy in the long-run. The government can run budget deficits or surpluses in a given year and must, therefore, be able to accumulate debt or savings.  The spending and debt parameters are discussed in Chapter {ref}`Chap_MacroCalib`.  Taxes are discussed in this chapter.


## Personal income taxes
The government sector influences households through two terms in the household budget constraint {eq}`EqHHBC`---government transfers $TR_{t}$ and through the total tax liability function $T_{s,t}$, which can be decomposed into the effective tax rate times total income. In this chapter, we detail the household tax component of government activity $T_{s,t}$ in `OG-ETH`.

```{math}
:label: EqHHBC
  c_{j,s,t} + b_{j,s+1,t+1} &= (1 + r_{hh,t})b_{j,s,t} + w_t e_{j,s} n_{j,s,t} + \\
  &\quad\quad\zeta_{j,s}\frac{BQ_t}{\lambda_j\omega_{s,t}} + \eta_{j,s,t}\frac{TR_{t}}{\lambda_j\omega_{s,t}} + ubi_{j,s,t} - T_{s,t}  \\
  &\quad\forall j,t\quad\text{and}\quad s\geq E+1 \quad\text{where}\quad b_{j,E+1,t}=0\quad\forall j,t
```

The total tax function, $T_{s,t}$, is a function of personal income taxes, taxes on bequests, and wealth taxes.  In the default calibration, wealth and bequest taxes are set to zero in `OG-ETH`.  Personal income taxes follow Ethiopia's **statutory schedule**, fitted with OG-Core's Gouveia–Strauss functional form (`tax_func_type = "GS"`), so that the effective and marginal rates rise with income the way the law says they do; the next subsection explains how informality is handled so that these rates fall only on the formal, tax-compliant minority.

### The statutory schedule as the tax function

Ethiopia taxes employment income (Schedule A) with monthly brackets.  Under Proclamation 979/2016, in force in FY2024/25, the first 600 birr a month were exempt and six brackets of 10, 15, 20, 25, 30 and 35 percent applied above 600, 1,650, 3,200, 5,250, 7,800 and 10,900 birr.  Proclamation 1395/2025, in force from July 2025 (FY2025/26), raised the exemption to 2,000 birr and set five brackets of 15, 20, 25, 30 and 35 percent above 2,000, 4,000, 7,000, 10,000 and 14,000 birr ([TaxDev](https://www.taxdev.org/news-events/ethiopias-revised-income-tax-explained)).  Capital income is taxed under Schedule D at flat rates, 10 percent on dividends and 5 percent on interest.

The model period is a year, and OG-Core evaluates its tax functions on annual income in currency units, converting the model's income units with `mean_income_data`, the average income of the households the functions describe.  The model's birr are FY2024/25 birr, the start year and the base year of the rebased national accounts ({ref}`Sec_Rebasing`).  We set `mean_income_data` to rebased GDP per adult in that year — 24,030 billion birr over about 66.7 million people aged 20 and over (the UN population the model's demographics use, World Bank age structure for 2024, grown half a year) — {glue:text}`mean_income` birr.  (An earlier version used the IMF's FY2026/27 GDP projection mislabeled as FY2025/26.)  For each schedule, `ogeth.macro_params.fit_gs_parameters` computes the statutory effective and marginal rates over a log-spaced grid of annual incomes from 12,000 to 5 million birr and fits the three Gouveia–Strauss parameters by least squares; the fit tracks the schedule to within about 1.5 (2016) and 2.5 (2025) percentage points of the effective rate, with the 35 percent top rate as the asymptote.  The first model period (FY2024/25) uses the 2016 schedule as written; every later period uses the 2025 schedule, its thresholds (written in FY2025/26 birr) deflated by the rebased growth of nominal GDP per head between the two years (about 29 percent) so that they bite at the same real incomes.  The same parameters serve as the marginal rate on labor income, and the marginal rate on capital income is the flat 10 percent dividend rate.  Brackets are fixed in birr by law and eroded by inflation; the model is real, so they are treated as indexed.

```{figure} ./images/statutory_tax_functions.png
---
height: 350px
name: FigStatutoryTax
---
The two statutory employment-income schedules (thin lines) and the Gouveia–Strauss functions fitted to them (dashed), as effective and marginal rates over monthly income; the vertical lines mark the mean income of the seven lifetime-income groups.
```

At the incomes of the model's seven lifetime-income groups the schedule's effective rate runs from a few percent at the bottom to the low 30s for the top decile.  That is why the compliance boundary below is the free parameter: the statutory schedule applied to the formal groups' incomes would collect many times what the treasury actually receives.

### Informality and tax noncompliance

Ethiopia's income tax reaches only a fraction of the population. About 78 percent of employment is informal — 77.65 percent in ILOSTAT's harmonised series from the 2021 Labour Force and Migration Survey (84.4 percent in agriculture, 65.9 outside it) — and the great majority of workers are self-employed in agriculture or small unregistered enterprises that never remit income tax. This is not a hole in the model's output: `OG-ETH`'s macro calibration rests on national-accounts data, which already imputes informal activity into GDP, so the model contains the informal economy's output, capital, and labour. What informality changes is the *tax boundary* — who actually remits the income tax that is owed. An earlier calibration missed this distinction, applying a single blended flat rate (a 3 percent effective and 20 percent marginal rate) to every household and thereby spreading Ethiopia's income-tax burden evenly across an economy where, in reality, a small formal minority pays close to statutory rates and the informal majority pays nothing. That both misstates who faces which incentives and imposes a spurious work-and-saving wedge on the roughly 90 percent of households the income tax does not reach.

We therefore model informality as graded tax *non-compliance* by lifetime-income group, using the `labor_income_tax_noncompliance_rate` and `capital_income_tax_noncompliance_rate` parameters (a value of 1 means none of the tax owed is remitted, 0 means full compliance).  Lifetime income serves as a proxy for formality: the seven lifetime-income groups carry population weights of 25, 25, 20, 10, 10, 9, and 1 percent, and the formal 22.35 percent of households are placed at the top of the lifetime-income distribution (`macro_params.formal_share_by_group`).  The *shape* of compliance is therefore [0, 0, 0, 0.235, 1, 1, 1]: the bottom three groups remit none of the income tax the schedule implies, the fourth group's formal quarter remits, and the top three groups, 20 percent of households, are formal.  Labour and capital noncompliance are set equal, and every group is still treated as a filer (`income_tax_filer` = 1): informality here is non-remittance, not non-filing.

With the statutory schedule as the tax function, the *level* of compliance is what the revenue data identify.  The compliance shape is multiplied by a scale, `COMPLIANCE_SCALE`, tuned (`examples/tune.py`) so that personal income tax collects {glue:text}`pit_target` of rebased GDP in the first model year, the FY2024/25 outturn of 194.3 billion birr (NBE Annual Report 2024/25, Table 6.3; the earlier anchor of 1.4 percent was a 2021–23 average on the old base).  It comes out at {glue:text}`compliance_scale`: the formal groups remit about a twentieth of what Schedule A would take from their total income.  That is not implausible: Schedule A reaches wage and salary income, while most income at the top of Ethiopia's distribution is business, professional and rental income taxed — or not — under other schedules, and WID's top shares include capital income.

Several of these choices are judgment calls, stated plainly: lifetime income is a proxy for formality, not sector of work, so high-income informality can only be represented as partial compliance; the sixth group's half-of-the-top compliance is a judgment, sensitivity-tested and macroeconomically minor; there is one economy-wide wage and no formal/informal choice margin, an OG-Core structural limit; and compliance is a proxy for the *fiscal* footprint of the formal sector, not a model of the choice to be formal.

In the history-anchored baseline compliance stays at this FY2024/25 calibration throughout, so personal income tax grows only with the tax base ({ref}`Sec_Scenarios`).  In the program scenario compliance moves along the transition, because the IMF program's revenue gains are direct-tax heavy: in the first nine months of FY2025/26 federal direct taxes grew 78 percent against 41 percent for domestic VAT and 5 percent for import taxes ({cite}`IMFCR26174:2026`, p. 15), the signature of a broadening tax base rather than of higher rates.  The scenario therefore lets the formal tax boundary move down the income distribution over the seven program years, FY2024/25–FY2030/31: the sixth group's compliance rises linearly to the top group's and the fifth group's from nothing to a fifth of it, and both then hold, so the compliance shape goes from [0, 0, 0, 0.235, 1, 1, 1] to [0, 0, 0, 0.885, 1, 1, 1], each date multiplied by the calibrated scale.  This adds personal income tax along the program; the rest of the program's revenue gain is carried by the consumption-tax rate and corporate-tax collections ({ref}`Sec_ProgramPath`).  The bottom three groups — 70 percent of households — stay entirely outside the income tax: the program formalizes the margin, not the mass of self-employed agriculture.  The paths are built by `ogeth.macro_params.program_compliance_paths` (the baseline's flat path by `history_compliance_paths`) and pinned by `tests/test_fiscal_program.py`.

Ethiopia's *statutory* pension contribution is 18 percent of covered salary (11 percent employer and 7 percent employee, Proclamations 1267/1268 of 2022), paid only by permanent employees of the formal public and private sectors covered by the two social-security agencies (PSSSA and POESSA).  OG-Core lets the payroll tax differ by lifetime-income group (from version 0.20.4), so the rate is the statutory 18 percent on the pension-covered groups (the same coverage shape as the pension, [0, 0, 0, 0, 0, 0.5, 1]) times a contribution scale, {glue:text}`payroll_scale`, and zero for everyone else: {glue:text}`payroll_top` for the top group and {glue:text}`payroll_g6` for the sixth.  The scale is tuned so that contributions collect {glue:text}`payroll_target` of rebased GDP, about 69 billion birr in FY2024/25 (POESSA about 29 billion; PSSSA about 40 billion, extrapolated from the 30.5 billion collected in 2023).  No official FY2024/25 scheme accounts were found, so this is the least certain fiscal anchor; the contributions sit inside the 117.8 billion "other" non-tax line of the budget outturn.  The model's formal groups earn about 40 percent of labour income, far more than the real covered wage bill, which is why the scale is well below one.  The previous calibration charged a flat 3 percent on every household, including the informal majority.

### Public pensions

The public pension is now in the model as a **defined-benefit scheme** with Ethiopia's rules.  Both schemes — the public servants' (Proclamation 1267/2022, administered by PSSSA) and the private organizations' employees' (Proclamation 1268/2022, POESSA) — retire workers at 60 after at least ten years of service and pay 30 percent of the average salary of the last three years plus 1.25 percent for every year of service beyond ten, up to 70 percent ([ISSA/SSA program descriptions](https://www.ssa.gov/policy/docs/progdesc/ssptw/2018-2019/africa/ethiopia.html)); a career from 20 to 60 earns 67.5 percent.  OG-Core's `Defined Benefits` system pays `yr_contrib × alpha_db` times average earnings over the last `avg_earn_num_years` years, so we set `retirement_age = 60`, `yr_contrib = 40`, `avg_earn_num_years = 3` and `alpha_db = 0.675 / 40`.

Coverage is the binding fact.  PSSSA had 1.67 million contributors in 2020 and POESSA 2.3 million registered members in 2023, but only about 58,000 POESSA pensioners and roughly 800,000 pensioners in all; the ILO puts participation at under two percent of the working-age population, and pension outlays are about half a percent of GDP ({cite}`IMFCR26174:2026`).  In the model the pension-covered groups are the sixth and seventh lifetime-income groups — 10 percent of households and 40 percent of labor income — so paying them the statutory replacement rate would cost several times what the schemes pay.  `replacement_rate_adjust` therefore keeps the coverage shape [0, 0, 0, 0, 0, 0.5, 1] and is scaled by `PENSION_COVERAGE_SCALE`, tuned (`examples/tune.py`) so that pension outlays in the first model year are 0.5 percent of old-base GDP, 0.31 percent of rebased GDP; it comes out at {glue:text}`pension_scale`; the scale stands for the fraction of each formal group that is actually enrolled.  Because the scheme now pays the pensions, the cash-transfer ratio $\alpha_T$ in {ref}`Chap_MacroCalib` is the pension outlays (0.31 points of rebased GDP) lower than the IMF's cash-transfer line along the program and the transfer allocation `eta` no longer carries a pension slice.  Contributions are charged to the covered groups only (the payroll tax above).

## Corporate income taxes

`OG-ETH` uses the statutory rate of {glue:text}`cit_rate` for the corporate income tax rate.  Because informal and exempt firms mean corporate collections fall well short of what the statutory rate applied to the whole capital stock would imply, the effective corporate tax is scaled by `adjustment_factor_for_cit_receipts` (together with `c_corp_share_of_assets`).  The factor carries every revenue line that taxes the return to capital: business profit tax (229.6 billion birr in FY2024/25), the other income taxes — rental, withholding on interest and imports, capital gains (52.9 billion) — and government investment income, the NBE's residual surplus and state-enterprise dividends (20.0 billion), in all {glue:text}`cit_target` of rebased GDP (NBE Annual Report 2024/25, Table 6.3).  It is tuned to that total in the first model year and comes out at {glue:text}`cit_adj_factor`.

## Taxes on wealth: land-use fees

Rural and urban land-use fees (44.1 billion birr, {glue:text}`wealth_target` of rebased GDP) are a recurrent charge on the use of land, the nearest margin in OG-Core being a flat tax on household wealth.  Setting `h_wealth` = 1 and a small `m_wealth` = 0.001 makes the wealth tax's effective rate equal to `p_wealth` for any household with wealth and zero at zero wealth; `p_wealth` is tuned to the fees in the first model year and comes out at {glue:text}`p_wealth`.  There is no inheritance tax in Ethiopia, so `tau_bq` stays at zero.

## Value-added taxes

An *effective* consumption-tax rate of {glue:text}`tau_c_rate` is applied with the `tau_c` parameter.  Ethiopia's statutory VAT rate is 15 percent (Proclamation 1341/2024), but the effective rate on aggregate consumption is far lower because of exemptions, a large informal and subsistence economy and incomplete compliance.  The rate carries every revenue line on spending: indirect taxes (domestic VAT and excises 298.2 billion birr, import duties and taxes 352.7 billion) plus charges and fees (39.4 billion) and sales of goods and services (32.8 billion), in all {glue:text}`ctax_target` of rebased GDP in FY2024/25 (NBE Annual Report 2024/25).  It is tuned to that total in the first model year.  On the rebased accounts private consumption is 64.4 percent of GDP, so the effective rate on measured consumption is about 4.7 percent.

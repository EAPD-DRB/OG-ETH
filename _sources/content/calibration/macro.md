(Chap_MacroCalib)=
# Calibration of Macroeconomic Parameters

## Economic Assumptions

As the default rate of labor augmenting technological change, $g_y$, we use a value of 6%.  The average annual growth rate in GDP per capita in Ethiopia between 2006 and 2024 is 6.0% per year, according to [data from the World Bank](https://data.worldbank.org/indicator/NY.GDP.PCAP.KD.ZG?locations=ET).

## Open Economy Parameters

### Foreign holding of government debt in the initial period

The path of foreign holding of domestic debt is endogenous, but the initial period stock of debt held by foreign investors is exogenous.  We set `initial_foreign_debt_ratio = 0.42` using [Ministry of Finance Public Sector Debt Statistical Bulletin No. 51](https://www.mofed.gov.et/media/filer_public/da/15/da150f60-a08c-440d-832c-111410cc1f85/public_sector_debt_statistical_bulletin_no_51-final12.pdf), Table 25: external debt of USD 28.89 billion against total public debt of USD 68.86 billion at end of FY2023/24 (42 percent).

### Foreign purchases of newly issued debt

We set $\zeta_D = 0.12$, the share of newly issued government debt held by foreign creditors.  This anchors on FY2023/24 flow data in the [Ministry of Finance Public Sector Debt Statistical Bulletin No. 51](https://www.mofed.gov.et/media/filer_public/da/15/da150f60-a08c-440d-832c-111410cc1f85/public_sector_debt_statistical_bulletin_no_51-final12.pdf): the change in external debt was about USD 0.64 billion against a change in total public debt of about USD 5.53 billion, a foreign share of net new issuance near 11.6 percent.

### Foreign holdings of excess capital

We set $\zeta_K = 0.20$.  Foreign direct investment inflows averaged 2 to 3 percent of GDP between 2018 and 2024 per the [UNCTAD World Investment Report](https://unctad.org/system/files/official-document/wir2025_en.pdf) against gross fixed capital formation of about 25 percent of GDP per the [World Bank gross fixed capital formation series](https://data.worldbank.org/indicator/NE.GDI.FTOT.ZS?locations=ET), implying foreign financing of new capital near 10 percent.  The [IMF Annual Report on Exchange Arrangements and Exchange Restrictions](https://www.imf.org/en/Publications/Annual-Report-on-Exchange-Arrangements-and-Exchange-Restrictions) documents binding controls by Ethiopia's central bank on foreign currency outflows and no resident access to international portfolio markets, with foreign banking access first opened under the 2024 financial-sector reform.

## Government Debt, Spending and Transfers

### Government Debt

The path of government debt is endogenous. But the initial value and the steady-state (long-run) value are exogenous. To avoid converting between model units and dollars, we calibrate the initial debt to GDP ratio, rather than the dollar value of the debt. This is the model parameter $\alpha_D$ and the parameter name in [`ogeth_default_parameters.json`](https://github.com/EAPD-DRB/OG-ETH/blob/main/ogeth/ogeth_default_parameters.json) is `initial_debt_ratio`.  We set `initial_debt_ratio = 0.327` from the [Ministry of Finance Public Sector Debt Statistical Bulletin No. 51](https://www.mofed.gov.et/media/filer_public/da/15/da150f60-a08c-440d-832c-111410cc1f85/public_sector_debt_statistical_bulletin_no_51-final12.pdf), reporting total public debt at 32.9 percent of GDP for FY2023/24.

The steady-state debt-to-GDP ratio is set as `debt_ratio_ss = 0.40`.  This anchors the long-run debt level to the [IMF Country Report 25/188](https://www.imf.org/en/publications/cr/issues/2025/07/15/the-federal-democratic-republic-of-ethiopia-2025-article-iv-consultation-third-review-under-568611) medium-term fiscal framework (Table 1), which projects Ethiopia's public-debt-to-GDP ratio declining from a 49.8 percent peak in FY2024/25 to 34.5 percent by FY2028/29.  The value sits well below the 55 percent threshold at which low-income countries are classified as at high risk of debt distress under the IMF/World Bank Debt Sustainability Framework.


#### Interest rates on government debt

We assume that there is a wedge between the real rate of return on private capital and the real interest rate on government debt.  We model this wedge a scale and level shift.  Specifically, we assume that the real interest rate on government debt, $r_{gov,t}$, is related to the real rate of return on private capital, $r_{t}$, by the following equation:

```{math}
:label: eqn:r_gov
    r_{gov,t} = (1-\tau_{d,t})r_t + \mu_d
```

where $\tau_d$ is the scale parameter and $\mu_d$ is the level shift parameter.  We set the values of these two parameters to 0.245 and -0.034, respectively.  These are found by using the estimated relationship between corporate and sovereign yields in {cite}`LMW2023` (Table 8, Column 2) and simulating a series of corporate yields given a series of sovereign yields between 2% and 12%.  We then estimate the scale and level shift parameters that best fit these simulated data using ordinary least squares.

### Aggregate transfers

We set $\alpha_T = 0.05$, combining about 3.4 percent of GDP for non-pension social benefits reported in the [IMF Government Finance Statistics](https://data.imf.org/en/Data-Explorer?datasetUrn=IMF.STA:GFS_SOO(12.0.0)&INDICATOR=G271_T) with an additional 1.6 percent of GDP for social benefits and subsidies to households (fuel, fertilizer, food, medicine, expanded safety net) documented in [IMF Country Report 25/188](https://www.imf.org/en/publications/cr/issues/2025/07/15/the-federal-democratic-republic-of-ethiopia-2025-article-iv-consultation-third-review-under-568611).

### Government expenditures

We set $\alpha_G = 0.055$, the most recent (2024) value of the [World Bank General government final consumption expenditure (% of GDP)](https://data.worldbank.org/indicator/NE.CON.GOVT.ZS?locations=ET) series (`NE.CON.GOVT.ZS`), which captures current spending on goods and services and excludes capital outlays.  Public infrastructure investment is calibrated separately via $\alpha_I$.


(SecLWI_footnotes)=
## Footnotes
The following are the footnotes for this section.

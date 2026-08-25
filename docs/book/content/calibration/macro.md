(Chap_MacroCalib)=
# Calibration of Macroeconomic Parameters

## Calibration vintage and refresh policy

The macroeconomic parameters below are calibrated to Ethiopian fiscal year **2024/25** (Ethiopian FY runs 8 July–7 July, so FY2024/25 ended 7 July 2025), which is the OG-ETH model start year of 2025.  This is the first full-year vintage that reflects the July 2024 exchange-rate float, and it materially changes the debt block relative to the pre-float FY2023/24 numbers used in earlier calibrations.

Following the approach used in the sibling models OG-PHL and OG-IDN, only parameters whose documented source is genuinely a live data feed are refreshed when `Calibration(update_from_api=True)` runs.  For OG-ETH that is `g_y_annual` (World Bank WDI) and `gamma` (UN ILOSTAT).  Every other parameter on this page is a documented, point-in-time value held in [`ogeth_default_parameters.json`](https://github.com/EAPD-DRB/OG-ETH/blob/main/ogeth/ogeth_default_parameters.json) so that a live update cannot silently overwrite a value sourced from a report table or a national statistical office.  In particular the World Bank Quarterly Public Sector Debt pull and the IMF Government Finance Statistics pull are switched off (the QPSD database has no Ethiopia coverage, and the IMF SDMX endpoint returns only 2002-vintage data for Ethiopia).

> **A note on GDP rebasing.**  All ratios on this page sit on Ethiopia's 2015/16-base national accounts.  The Ministry of Planning and Development and the IMF program both schedule a national-accounts rebasing for late 2026 (base year 2024/25 or 2025/26).  Because services are widely thought to be undermeasured, the rebasing is expected to raise the nominal-GDP level, which would mechanically shrink every ratio here (debt/GDP, transfers/GDP, government consumption/GDP, the effective consumption-tax rate).  The calibration should be revisited once the rebased accounts are published.

## Economic Assumptions

As the default rate of labor-augmenting technological change, $g_y$, we use a value of **4.7%**.  This is the average annual growth rate of GDP per capita in Ethiopia over **2016–2025**, according to [data from the World Bank](https://data.worldbank.org/indicator/NY.GDP.PCAP.KD.ZG?locations=ET) (series `NY.GDP.PCAP.KD`).

$g_y$ is the *permanent* balanced-growth-path rate of labor-augmenting technical change, so it should reflect Ethiopia's sustainable long-run growth rather than a historical episode.  We deliberately do not use the longer 2006–2024 window, whose ~6.0% average embeds the 2004–2015 state-led investment boom that the [IMF Country Report 26/20](https://www.imf.org/en/publications/cr/issues/2026/01/29/the-federal-democratic-republic-of-ethiopia-fourth-review-under-the-extended-573522) Debt Sustainability Analysis explicitly assumes will not repeat ("growth slower than historical rates of around 10 percent per annum over the two decades prior to 2019").  The post-2015 decade averages over the post-boom normalization, the 2020–2022 conflict-and-COVID dip, and the recent gold-export-driven recovery, giving a more defensible long-run anchor.  The IMF's own medium-term path (~8% real GDP growth) implies roughly 5.6% per-capita growth on UN population projections, which we treat as a program-optimistic upper bound rather than the balanced-growth rate.

## Open Economy Parameters

### Foreign holding of government debt in the initial period

The path of foreign holding of domestic debt is endogenous, but the initial-period stock of debt held by foreign investors is exogenous.  We set `initial_foreign_debt_ratio = 0.63` using the external share of public and publicly guaranteed (PPG) debt at end-June 2025 (FY2024/25).  The [Ministry of Finance Public Sector Debt Statistical Bulletin No. 56](https://www.mofed.gov.et/resources/bulletin/) (Feb 2026), Table 25, reports external debt of USD 34.09 billion against total public debt of USD 53.20 billion (64.1 percent), and the [joint World Bank–IMF Debt Sustainability Analysis](https://www.imf.org/en/publications/cr/issues/2026/01/29/the-federal-democratic-republic-of-ethiopia-fourth-review-under-the-extended-573522) for the fourth ECF review puts the external share at 62.9 percent of PPG debt.  The July 2024 float (the birr moved from about 57 to about 135 per US dollar) mechanically raised the birr value of external debt, so the foreign share jumped from about 45 percent (FY2023/24) to about 63 percent (FY2024/25).

### Foreign purchases of newly issued debt

We set $\zeta_D = 0.15$, the share of newly issued government debt held by foreign creditors.  The FY2024/25 realized flow is an outlier: net external borrowing of about 1.0 percent of GDP against net domestic financing of about 0.2 percent (a foreign share above 80 percent) reflected a one-off surge of IMF and World Bank budget support combined with a debt-service standstill during the restructuring, per the [World Bank Inclusive Growth DPO Program Document](https://documents.worldbank.org/curated/en/099060226161033684) (May 2026), Table 2.  Over the medium term the DSA projects net external financing falling back toward zero (and turning negative as amortization resumes) while net domestic financing shifts toward market-based instruments, so the foreign share of net new issuance settles well below the FY2024/25 outlier.  We set $\zeta_D = 0.15$ as a long-run value between that near-zero steady-state share and the concessional-external dependence that persists through the transition.

### Foreign holdings of excess capital

We set $\zeta_K = 0.16$, anchored on Ethiopia's **normalized Chinn-Ito capital-account-openness index**, which is 0.162 in the 2023 vintage and flat since the 1990s (the [Chinn-Ito KAOPEN dataset](https://web.pdx.edu/~ito/Chinn-Ito_website.htm)).  This places Ethiopia in the second-lowest openness bin, just above fully-closed economies and well below the investment-grade siblings OG-PHL (0.45) and OG-IDN (0.42).  It is cross-checked against the flow evidence: foreign direct investment of about USD 4.0 billion in FY2024/25 ([Ethiopian Investment Commission](https://unctad.org/publication/world-investment-report-2025)) against gross fixed capital formation of about 20 percent of a roughly USD 126 billion economy implies foreign financing of new capital in the low-teens percent (about 11–16 percent depending on the window), consistent with $\zeta_K$ near 0.16.  Ethiopia is a near-closed capital account: the [IMF Annual Report on Exchange Arrangements and Exchange Restrictions](https://www.imf.org/en/Publications/Annual-Report-on-Exchange-Arrangements-and-Exchange-Restrictions) documents binding foreign-exchange controls until the July 2024 reform, no resident access to international portfolio markets, and only nascent foreign participation via the Ethiopian Securities Exchange (launched January 2025) and the 2024 banking-sector opening.  The value is a modest reduction from the previous 0.20, moving the model's steady-state foreign-owned capital share toward the low level implied by Ethiopia's international investment position.

### World interest rate

We retain `world_int_rate_annual = 0.04`.  Ethiopia is a distressed sovereign (it defaulted on its single Eurobond and is still restructuring), so the clean "risk-free rate plus a small sovereign spread" logic used for the investment-grade siblings OG-PHL and OG-IDN does not apply.  Instead, Ethiopia's limited integration with world capital markets is captured through the low $\zeta_K$ above and the debt-elastic sovereign rate below, and the world rate is left at the standard 4 percent benchmark.

## Government Debt, Spending and Transfers

### Government Debt

The path of government debt is endogenous, but the initial value and the steady-state (long-run) value are exogenous.  To avoid converting between model units and birr, we calibrate the initial debt-to-GDP ratio rather than the birr value of the debt.  This is the model parameter $\alpha_D$; the parameter name in [`ogeth_default_parameters.json`](https://github.com/EAPD-DRB/OG-ETH/blob/main/ogeth/ogeth_default_parameters.json) is `initial_debt_ratio`.

We set `initial_debt_ratio = 0.50` from the [joint World Bank–IMF DSA](https://www.imf.org/en/publications/cr/issues/2026/01/29/the-federal-democratic-republic-of-ethiopia-fourth-review-under-the-extended-573522) for the fourth ECF review, which reports total public sector debt of 50.3 percent of GDP at end-June 2025 (FY2024/25).  This is a sharp increase from the 32.9 percent that Bulletin No. 51 reported for FY2023/24, and the increase is almost entirely valuation: the July 2024 float raised the birr value of external debt by about 170 percent, lifting external debt from about 15 percent to about 32 percent of GDP in one year while the domestic-debt ratio fell.  The 0.327 used in the previous calibration was the pre-float FY2023/24 ratio and is no longer the model-start debt stock.

The steady-state debt-to-GDP ratio is set as `debt_ratio_ss = 0.30`.  This anchors the long-run debt level to the IMF program's medium-term path: the [fifth ECF review](https://www.imf.org/en/news/articles/2026/07/01/pr26235-ethiopia-imf-completes-5th-review-under-ecf-arrangement) (completed July 2026) projects public debt declining from the FY2024/25 peak to about 34.5 percent of GDP by FY2028/29 and about 28.6 percent by FY2030/31, converging toward 20 percent thereafter.  The value sits below the 35 percent present-value benchmark used for weak debt-carrying-capacity countries under the IMF/World Bank Debt Sustainability Framework, consistent with the program's disinflation-and-consolidation objective.

#### Interest rates on government debt

We assume a wedge between the real rate of return on private capital and the real interest rate on government debt.  OG-Core models this as a scale term, a level shift, and (optionally) a debt-elastic premium:

```{math}
:label: eqn:r_gov
    r_{gov,t} = \max\left\{(1-\tau_{d})r_t - \mu_d + \beta_1\frac{D_t}{Y_t} + \beta_2\left(\frac{D_t}{Y_t}\right)^2,\; 0\right\}
```

where $\tau_d$ is the scale parameter (`r_gov_scale`), $\mu_d$ is the level shift (`r_gov_shift`), and $\beta_1$ (`r_gov_DY`), $\beta_2$ (`r_gov_DY2`) govern the debt-elastic premium.  The scale and base level shift are set to 0.245 and -0.034 by inverting the estimated relationship between corporate and sovereign yields in {cite}`LMW2023` (Table 8, Column 2): we simulate corporate yields for sovereign yields between 2 and 12 percent and estimate the scale and shift that best fit these simulated data by ordinary least squares.  The calculation is reproduced by `ogeth.macro_params.estimate_r_gov`.

Following OG-PHL and OG-IDN, we turn on a **debt-elastic sovereign premium** — the crowding-out-via-risk channel that a distressed sovereign like Ethiopia faces but that OG-Core leaves off by default.  We use the convex form of {cite}`SchmittGrohe:2003`, $\beta_2\left(D_t/Y_t - \bar{D}\right)^2$ with $\beta_2 = 0.04$, and **center it on the steady-state debt ratio** $\bar{D} =$ `debt_ratio_ss` $= 0.30$ so the premium is exactly zero at the target and does not move the steady state; it only prices the transition-path debt overshoot.  Expanding the square and folding the constant into the level shift (OG-Core subtracts `r_gov_shift`) gives

```{math}
:label: eqn:r_gov_center
    \beta_1 = -2\beta_2\bar{D} = -0.024, \qquad
    \mu_d = 0.03377 + \beta_2\bar{D}^2 = 0.03737.
```

At the initial debt ratio of 0.50 the premium adds about 16 basis points to the sovereign rate; it rises with the square of any debt overshoot along the transition.  Ethiopia's realized external borrowing is highly concessional (new central-government commitments in FY2024/25 carried an average interest rate of 0.77 percent with a 52 percent grant element, per [MoF Bulletin No. 56](https://www.mofed.gov.et/resources/bulletin/), Table 12), which is well below the modeled steady-state $r_{gov}$; the modeled wedge is therefore conservative with respect to Ethiopia's actual cost of external funds.

### Aggregate transfers

We set $\alpha_T = 0.04$.  Identifiable household transfers in FY2024/25 comprise explicit subsidies of about 1.0 percent of GDP (fuel, fertilizer, and a road-fund component, all being phased down toward an October 2026 fuel-subsidy exit), the expanded Productive Safety Net Program (about 10 million beneficiaries), and residual social benefits, per the [World Bank Inclusive Growth DPO Program Document](https://documents.worldbank.org/curated/en/099060226161033684) (May 2026) and [IMF Country Report 26/20](https://www.imf.org/en/publications/cr/issues/2026/01/29/the-federal-democratic-republic-of-ethiopia-fourth-review-under-the-extended-573522).  This is a reduction from the previous 0.05: total current spending in FY2024/25 was only about 7.1 percent of GDP, of which interest absorbed 0.8 and defense about 0.6, so a household-transfer share of 5 percent was difficult to reconcile.  The value should be confirmed against the general-government economic-classification table (GFS expense composition) in the IMF staff reports as those become available.

### Government expenditures

We set $\alpha_G = 0.058$, the most recent (2025, corresponding to FY2024/25) value of the [World Bank General government final consumption expenditure (% of GDP)](https://data.worldbank.org/indicator/NE.CON.GOVT.ZS?locations=ET) series (`NE.CON.GOVT.ZS`), which captures current spending on goods and services and excludes capital outlays.  The series bottomed at 5.5 percent in 2024 and has begun to recover as the FY2025/26 budget restores real public-sector wages; public infrastructure investment is calibrated separately via $\alpha_I$ (see {ref}`Chap_FirmCalib`).

> **A note on federal versus general government.**  Ethiopia is a federation, and the regional states execute much of the pro-poor spending and most of the education and health wage bill, financed largely by a federal block grant (about ETB 214 billion, ~1.8 percent of GDP, in FY2023/24 — an *intergovernmental* transfer, not a household transfer, and correctly excluded from $\alpha_T$).  The fiscal figures used here are the IMF/World Bank **general-government** aggregates, which consolidate federal and regional accounts.  Separately, much of Ethiopia's public investment historically ran *off-budget through state-owned enterprises*, so general-government spending (~12 percent of GDP) understates the broader public sector — which is why public-sector *debt* is ~50 percent of GDP while on-budget spending looks small.  $\alpha_I$ here is the on-budget general-government figure.

### Foreign aid

Ethiopia is one of the world's largest aid recipients, and on-budget grants to the government were about 1.7 percent of GDP in FY2024/25 (elevated by post-reform donor budget support), per the [World Bank Inclusive Growth DPO Program Document](https://documents.worldbank.org/curated/en/099060226161033684) (May 2026), Table 2; the IMF program projects grants declining over the medium term (toward about 0.9, then 0.5, then 0.3 percent of GDP).  OG-Core's `alpha_FA` parameter routes foreign aid to the domestic government as a share of GDP: it is a government resource (it funds spending and reduces the deficit) and an external inflow in the resource constraint.  We set $\alpha_{FA} = 0.01$, a modest long-run grant level between Ethiopia's currently elevated grants and the declining program path — a level a low-income country like Ethiopia is likely to keep receiving.  (OG-Core does not extend `alpha_FA` to a time-varying path the way it does `alpha_G`, `alpha_T`, and `alpha_I`, so it is held constant rather than following the declining path the data would suggest.)  Modeling aid at all is what allows the government to fund its spending without an implausible squeeze: Ethiopia's low domestic revenue (~9 percent of GDP) cannot on its own support positive government consumption alongside public investment and transfers on a debt-stable path — the aid- and concessional-borrowing-financed gap that is real in the data but cannot persist forever on a balanced-growth path.

### Remittances

Remittances are a defining feature of Ethiopian household income — the [IMF Country Report 26/20](https://www.imf.org/en/publications/cr/issues/2026/01/29/the-federal-democratic-republic-of-ethiopia-fourth-review-under-the-extended-573522) balance-of-payments data put net private transfers in the ~5 percent of GDP range (roughly USD 7 billion, larger than FDI; the realized FY2024/25 figure is nearer 4.7 percent and the program expects a return toward the historical ~5 percent). We set `alpha_RM_1 = alpha_RM_T = 0.056`, anchoring to that historical/program level, with remittances distributed across households by the `eta_RM` matrix.  (The World Bank WDI personal-remittances series is unreliable for Ethiopia and is not used.)  Turning remittances on is what lets the model reproduce Ethiopia's large goods-trade deficit: like aid, remittances are an external inflow that finances imports in excess of exports.

## Steady-state validation

Most of the parameters on this page are only weakly identified from the data on their own, so the real test of the calibration is whether the *steady state they jointly produce* resembles the Ethiopian economy.  The table below compares the OG-ETH baseline steady state (from `examples/run_og_eth.py`) with Ethiopian data targets (FY2024/25 unless noted).

| Steady-state moment | OG-ETH baseline | Ethiopia data | Data source |
|:---|:---:|:---:|:---|
| Government debt $D/Y$ | 0.30 | 0.30 (long-run target); 0.50 (FY2024/25) | IMF 5th ECF review |
| Foreign-held debt share $D_f/D$ | 0.15 (steady state) | 0.63 external (initial), 0 onshore-held | MoF Bulletin 56 / DSA |
| Foreign-owned capital share $K_f/K$ | 0.08 | low (near-closed account) | Chinn-Ito; BoP IIP |
| Foreign-owned capital $K_f/Y$ | 0.24 | ~0.24 (FDI stock) | UNCTAD / WB |
| Private consumption $C/Y$ | 0.64 | 0.81 (BGP ~0.65–0.70) | WDI `NE.CON.PRVT.ZS` |
| Total investment $(I+I_g)/Y$ | 0.41 | 0.20 (BGP ~0.30) | WDI `NE.GDI.FTOT.ZS` |
| Capital-output $K/Y$ | 3.1 | ~2.2 | Penn World Table |
| Public investment $I_g/Y$ | 0.05 | 0.045–0.05 | IMF CR 26/20 |
| Transfers $TR/Y$ | 0.04 | ~0.03–0.04 | WB DPO / IMF CR 26/20 |
| Trade balance $NX/Y$ | −0.065 | −0.069 (goods) | NBE / WDI |
| Remittances $RM/Y$ | 0.056 | 0.056 | IMF CR 26/20 BoP |
| Real return on capital $r$ | 0.044 | high (capital-scarce) | model-implied MPK |
| Personal income tax (PIT)/Y | 0.014 | 0.014 | IMF SIP 2025/108 |
| Corporate income tax (CIT)/Y | 0.017 | 0.017 | IMF SIP 2025/108 |
| Tax revenue $T/Y$ | 0.088 | 0.078 (tax); 0.092 (revenue excl. grants) | WB DPO Table 2 |

The debt block behaves as intended: the model starts at the FY2024/25 debt ratio of 0.50 and converges to the 0.30 long-run target, and the foreign-held share declines over the transition from the initial 0.63 toward the steady-state $\zeta_D = 0.15$, mirroring the IMF projection that external debt falls faster than total debt.  The **external sector now matches the data closely**: the foreign-owned capital share falls to 0.08 (a foreign-owned capital stock of about 0.24 times GDP, in line with Ethiopia's ~0.24 inward FDI stock), the trade balance is a deficit of about 6.5 percent of GDP (against an actual goods-trade deficit near 6.9 percent), and remittances sit at their measured 5.6 percent.  This is a large improvement over the earlier calibration, which — using the naive ILOSTAT capital share, no remittances, and no foreign aid — produced a foreign-owned capital stock of ~1.3 times GDP and a wrong-signed trade *surplus*.  On the **tax side**, drawing the informality boundary (see {ref}`Chap_Tax`) brings collections to the data instrument by instrument — personal income tax 1.4 percent of GDP, corporate income tax 1.7 percent, direct taxes 3.1 percent — with total tax revenue of 8.8 percent sitting between Ethiopia's ~7.8 percent tax take and ~9.2 percent revenue excluding grants; the earlier blended flat rate and 18 percent economy-wide payroll tax had pushed revenue to an implausible 13 percent.

Two tensions remain, both understood.  First, the model steady state is still somewhat **more investment-intensive than *current* Ethiopia**: total investment is about 41 percent of GDP and private consumption about 64 percent, against the FY2024/25 trough of ~20 percent investment and ~81 percent consumption.  But the current split is a war-and-FX-crisis-depressed trough, not a balanced-growth path — Ethiopia invested above 40 percent of GDP during the mid-2010s boom, and a catch-up BGP should sit between.  The residual gap reflects a model $K/Y \approx 3.1$ still above the Penn World Table's ~2.2; the self-employed-adjusted capital share of 0.30 ({ref}`Chap_FirmCalib`) closes most of the original gap, and the SAM-based per-industry capital shares planned for the multi-industry calibration are the way to close the rest.  Second, steady-state **government consumption (~1.9 percent of GDP) is below the measured ~5.8 percent**.  This is the honest consequence of fiscal sustainability: Ethiopia funds its larger current government via grants (declining) and concessional borrowing, which a self-financing balanced-growth path cannot carry indefinitely.  The declining foreign-aid path supports government spending in the near-term transition — where the model matches the data — while the steady state reflects the smaller government affordable once aid normalizes.

(SecLWI_footnotes)=
## Footnotes
The following are the footnotes for this section.

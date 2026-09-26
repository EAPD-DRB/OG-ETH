(Chap_FirmCalib)=
# Calibration of Firm Parameters

## Aggregate Production Function and Capital Accumulation

The [OG-Core firm theory documentation](https://pslmodels.github.io/OG-Core/content/theory/firms.html) outlines the constant returns to scale, constant elasticity of substitution production function of the representative firm.  This function has two parameters; the elasticity of substitution and capital's share of output.

The production function is given as:

```{math}
:label: EqFirmsCESprodfun
  \begin{split}
    Y_{m,t} &= F(K_{m,t}, K_{g,m,t}, L_{m,t}) \\
    &\equiv Z_{m,t}\biggl[(\gamma_m)^\frac{1}{\varepsilon_m}(K_{m,t})^\frac{\varepsilon_m-1}{\varepsilon_m} + (\gamma_{g,m})^\frac{1}{\varepsilon_m}(K_{g,m,t})^\frac{\varepsilon_m-1}{\varepsilon_m} + \\
    &\quad\quad\quad\quad\quad(1-\gamma_m-\gamma_{g,m})^\frac{1}{\varepsilon_m}(e^{g_y t}L_{m,t})^\frac{\varepsilon_m-1}{\varepsilon_m}\biggr]^\frac{\varepsilon_m}{\varepsilon_m-1} \quad\forall m,t
  \end{split}
```

  This production function has the following parameters:
  * $\varepsilon_m$ is the elasticity of substitution between capital, labor, and infrastructure in sector $m$.
  * $\gamma_m$ is the share of capital in sector $m$.
  * $\gamma_{g,m}$ is the share of government capital in sector $m$.
  * $Z_{m,t}$ is the total factor productivity in sector $m$ at time $t$.

### Elasticity of substitution

`OG-ETH`'s default parameterization has an elasticity of substitution of $\varepsilon=1.0$, which implies a Cobb-Douglas production function.

### Factor shares of output

We set the private capital share to $\gamma_m = 0.30$ and the public capital share to $\gamma_{g,m} = 0.10$ (the low-income-country value from {cite}`Buffie:2012`), for a total capital share of 0.40 and a labour share of 0.60.  Because this is the single most consequential — and most contestable — calibration choice, and because it departs from the headline official statistic, the reasoning is set out in full in the next subsection.

#### Calibrating the capital share

The measured labour share of output for Ethiopia is low. The [UN ILOSTAT labour income share](https://rshiny.ilo.org/dataexplorer41/?lang=en&segment=indicator&id=SDG_1041_NOC_RT_A) (SDG indicator 10.4.1, series `SDG_1041_NOC_RT_A`) is 0.385 (2025), which taken at face value implies a total capital share of 0.615.  That is implausibly high for an economy that is roughly two-thirds agrarian and informal, where most output is produced by self-employed smallholder farmers and own-account workers.  The reason is a well-known measurement problem: a self-employed farmer earns no wage, so national-accounts conventions record their entire income as gross operating surplus (mixed income) — the *capital* bucket — even though most of it is a return to their own labour. The measured labour share therefore captures mainly the small formal wage sector and misses the labour income embedded in self-employed mixed income, biasing the labour share down and the capital share up.

The ILOSTAT series already applies a self-employment imputation, so 0.385 is not a raw employee-compensation figure. Adjusting *below* it (i.e. to a higher labour share) rests on three lines of evidence, the first of which does not use the labour share at all.

1. **Ethiopia's capital–output ratio implies a capital share near 0.40, independent of any labour-share measurement.** Under the competitive first-order condition, the capital share, the capital–output ratio, and the net return are linked by $\gamma = (r + \delta)\,(K/Y)$. The Penn World Table puts Ethiopia's capital–output ratio at about 2.2. At $\delta = 0.05$, the ILOSTAT-implied total capital share of 0.615 would require a real return of $0.615/2.2 - 0.05 \approx 18$ percent — far above the 9–14 percent range plausible even for a capital-scarce frontier economy. A total capital share of 0.40 implies $0.40/2.2 - 0.05 \approx 13$ percent, and 0.30 implies about 9 percent. So the observed capital–output ratio, at any defensible return, backs out a total capital share of roughly 0.30–0.40 — with the ILOSTAT figure, not the adjusted one, as the outlier. This is a growth-accounting identity rather than a labour-share argument, so it is an independent check.

2. **The direction of the residual bias is known.** {cite}`Gollin:2002` shows that naive labour shares vary across countries largely because of how self-employment is treated, and that fuller self-employment adjustments raise labour shares for low-income agrarian economies to 0.65–0.80 regardless of the starting figure. ILOSTAT's imputation is comparatively conservative, so its 0.385 sits toward the low end of where a complete adjustment would land.

3. **Ethiopia's land tenure inflates measured capital income specifically.** All land in Ethiopia is constitutionally state-owned — farmers hold use rights, not marketable title. The imputed land rent embedded in agricultural operating surplus is therefore not a return to privately owned capital in the usual sense; economically it is closer to a usufruct return on the household's own labour and effort. National-accounts conventions nonetheless book it as operating surplus, inflating the measured capital share for Ethiopia in particular.

We adopt a labour share of **0.60**, giving a total capital share of 0.40 and, after carving out $\gamma_{g,m}=0.10$, a private share $\gamma_m = 0.30$. This is a deliberately *conservative* landing point: it is a compromise between the ILOSTAT figure (labour 0.615, $\gamma_m = 0.515$) and a full Gollin adjustment (labour ~0.70, $\gamma_m \approx 0.20$), and it coincides with the top of the range implied by the capital–output ratio. A sectoral decomposition corroborates it: weighting FY2024/25 value-added shares (agriculture 31, industry 30, services 40 percent) by typical sectoral labour intensities (agriculture ~0.75, services ~0.60, gold-mining-heavy industry ~0.45) gives $0.31\times0.75 + 0.30\times0.45 + 0.40\times0.60 \approx 0.60$.

Two honest caveats. First, this is a *triangulation, not an Ethiopian measurement*: the three lines above agree the capital share is well below the ILOSTAT-implied 0.615 and cluster it around 0.30–0.40, but the defensible range for $\gamma_m$ is roughly 0.25–0.35, with 0.30 the centre rather than a point estimate. Second, even at $\gamma_m = 0.30$ the model's steady-state $K/Y$ is about 3.0, still above the Penn World Table's ~2.2 — but that residual is a *return* gap, not a capital-share gap: the model's equilibrium return (~5 percent) is held down by the borrowed household discount factor ($\beta = 0.96$), and at a 13 percent return the same 0.40 capital share would deliver $K/Y \approx 2.2$. The SAM-based per-industry capital shares planned for the multi-industry calibration, which strip the self-employed mixed-income bias industry by industry, are the principled way to refine the share itself.

### Public-investment efficiency

OG-Core's law of motion for public capital is

```{math}
:label: EqPublicCapitalLOM
K_{g,m,t+1} = (1 - \delta_g)\,K_{g,m,t} + (1 - \phi_g)\,I_{g,m,t}
```

where $\delta_g$ is the depreciation rate of public capital (the `delta_g_annual` parameter) and $\phi_g$ (`infra_investment_leakage_rate`) is the fraction of public investment lost to leakage.  We set $\phi_g = 0.5$, meaning half of public investment is lost to inefficiency, matching the value used for the average low-income country in {cite}`Buffie:2012`.

Public investment flow is set as a share of GDP, $I_{g,t} = \alpha_{I,t}\,Y_t$.  We calibrate `alpha_I` as a five-year linear path from the most recent actual to a modest long-run value, then hold constant:

| $t$            | 0     | 1     | 2     | 3     | $\geq 4$ |
|:---------------|:-----:|:-----:|:-----:|:-----:|:--------:|
| $\alpha_{I,t}$ | 0.045 | 0.048 | 0.050 | 0.050 | 0.050    |

The values are anchored on Ethiopia's *actual* on-budget general government capital expenditure of about 4.5–5.0 percent of GDP in FY2024/25, per the [IMF Country Report 26/20](https://www.imf.org/en/publications/cr/issues/2026/01/29/the-federal-democratic-republic-of-ethiopia-fourth-review-under-the-extended-573522) fiscal table and the [World Bank Inclusive Growth DPO Program Document](https://documents.worldbank.org/curated/en/099060226161033684) (May 2026), Table 2.  We hold the long-run value at 0.050 rather than the higher recovery path the IMF projects (public investment rising toward 6–7 percent): with Ethiopia's low general-government revenue (~9 percent of GDP), a debt-stable steady state cannot fund both that higher investment and positive government consumption even with the foreign aid modeled in {ref}`Chap_MacroCalib` — the grants and concessional borrowing that support the actual budget cannot persist in full on a balanced-growth path.  Note also that much of Ethiopia's historical public investment ran *off-budget through state-owned enterprises*, so this on-budget general-government $\alpha_I$ understates total public-sector investment.

### Initial public capital to GDP ratio

The parameter `initial_Kg_ratio` sets the ratio of public capital stock to GDP in the model start year.  The steady-state public-capital-to-GDP ratio implied by the (stationarized) law of motion at our calibrated $\phi_g$, $\delta_g$, $g_y$, population growth $g_n$, and long-run $\alpha_I = 0.050$ is

```{math}
:label: EqInitialKgSS
\bar{K}_g / \bar{Y} = \frac{(1-\phi_g)\,\alpha_I}{e^{g_y}(1+g_n) - (1-\delta_g)} = \frac{0.5 \times 0.050}{e^{0.047}(1.020) - 0.98} \approx 0.28,
```

which matches the solved baseline steady state ($\bar{K}_g/\bar{Y} = 0.281$).  Ethiopia's *measured* public capital stock is much higher — about 0.67 of GDP in 2019 per the [IMF Investment and Capital Stock Dataset](https://data.imf.org/en/Data-Explorer?datasetUrn=IMF.FAD:ICSD(1.0.0)), the accumulated result of the state-led, largely SOE-financed infrastructure push of the 2010s (roads, rail, power, and the Grand Ethiopian Renaissance Dam, completed September 2025).

We set `initial_Kg_ratio = 0.67`, the measured stock, and let it depreciate toward the sustainable steady state over the transition.  This starts the model from the public capital Ethiopia actually has — the infrastructure is real and productive (it enters the production function through $\gamma_{g}$) — rather than pretending it away.  Because that stock was built by an investment rate (public-sector investment reached 15–18 percent of GDP in the boom, mostly off-budget through SOEs) that is not sustainable at Ethiopia's current revenue — the same over-accumulation that produced the debt distress and the 2023 default — the model's long-run $\bar{K}_g/\bar{Y}$ (0.28) sits well below it, and the transition traces the honest counterfactual: public capital falls from 0.67 toward 0.28 over roughly a generation.  The consequence for output is sizeable — starting at the measured stock lifts baseline GDP about 10 percent in the model start year relative to starting near the steady state, a premium that halves about every fifteen years as the capital normalizes.  (Some of the measured stock is low-return — stalled sugar complexes, underused industrial parks — so 0.67 is an upper bound on genuinely productive public capital; the model does not haircut it explicitly but depreciates the unsustainable portion away endogenously.)

### Total factor productivity

In the case of the single production sector, we can normalize $Z_{m,t}=1.0$.

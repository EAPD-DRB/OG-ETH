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

(Chap_Demog)=
# Demographics

Demographics are a key component of the macroeconomic model. {cite}`Nishiyama:2015` and {cite}`DeBackerEtAl:2019` have recently shown that demographic dynamics are likely the biggest influence on macroeconomic time series, exhibiting more influence than fiscal variables or household preference parameters.

In this chapter, we characterize the equations and parameters that govern the transition dynamics of the population distribution by age. In `OG-ETH`, we take the approach of taking mortality rates and fertility rates from outside estimates. But we estimate our immigration rates as residuals using the mortality rates, fertility rates, and at least two consecutive periods of population distribution data. This approach makes sense if one is modeling a country in which one is not confident in the immigration rate data. If the country has good immigration data, then the immigration residual approach we describe below can be skipped.

We define $\omega_{s,t}$ as the number of households of age $s$ alive at time $t$. A measure $\omega_{1,t}$ of households is born in each period $t$ and live for up to $E+S$ periods, with $S\geq 4$.[^calibage_note] Households are termed "youth", and do not participate in market activity during ages $1\leq s\leq E$. The households enter the workforce and economy in period $E+1$ and remain in the workforce until they unexpectedly die or live until age $s=E+S$. We model the population with households age $s\leq E$ outside of the workforce and economy in order most closely match the empirical population dynamics.

The population of agents of each age in each period $\omega_{s,t}$ evolves according to the following function,
```{math}
  :label: EqPopLawofmotion
    \omega_{1,t+1} &= (1 - \rho_{0,t})\sum_{s=1}^{E+S} f_{s,t}\omega_{s,t} + i_1\omega_{1,t}\quad\forall t \\
    \omega_{s+1,t+1} &= (1 - \rho_{s,t})\omega_{s,t} + i_{s+1,t}\omega_{s+1,t}\quad\forall t\quad\text{and}\quad 1\leq s \leq E+S-1
```

where $f_{s,t}\geq 0$ is an age-specific fertility rate, $i_{s,t}$ is an age-specific net immigration rate, $\rho_{s,t}$ is an age-specific mortality hazard rate, and $\rho_{0,t}$ is an infant mortality rate.[^houseprob_note] The total population in the economy $N_t$ at any period is simply the sum of households in the economy, the population growth rate in any period $t$ from the previous period $t-1$ is $g_{n,t}$, $\tilde{N}_t$ is the working age population, and $\tilde{g}_{n,t}$ is the working age population growth rate in any period $t$ from the previous period $t-1$.

```{math}
  :label: EqPopN
  N_t\equiv\sum_{s=1}^{E+S} \omega_{s,t} \quad\forall t
```

```{math}
  :label: EqPopGrowth
  g_{n,t+1} \equiv \frac{N_{t+1}}{N_t} - 1 \quad\forall t
```

```{math}
  :label: EqPopNtil
  \tilde{N}_t\equiv\sum_{s=E+1}^{E+S} \omega_{s,t} \quad\forall t
```

```{math}
  :label: EqPopGrowthTil
  \tilde{g}_{n,t+1} \equiv \frac{\tilde{N}_{t+1}}{\tilde{N}_t} - 1 \quad\forall t
```

We discuss the approach to estimating fertility rates $f_{s,t}$, mortality rates $\rho_{s,t}$, and immigration rates $i_{s,t}$ in Sections {ref}`SecDemogFert`, {ref}`SecDemogMort`, and {ref}`SecDemogImm`.

(SecDemogFert)=
## Fertility rates

   Our data for Ethiopia fertility rates by age come from United Nations fertility rate data for a country for some range of years (at least one year) and by age. The country_id=231 is for Ethiopia. These data come from the United Nations Data Portal API for UN population data (see https://population.un.org/dataportal/about/dataapi). The UN variable code for Population by 1-year age groups and sex is "47" and that for Fertility rates by age of mother (1-year) is "68".

  {numref}`Figure %s <FigFertRatesETH>` was created using the [`ogcore.demographics.get_fert()`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/demographics.py#L146) function, which downloaded the data from the United National Data Portal API and plotted it in Python.[^un_data_portal]

  ```{code-cell} ipython3
  :tags: ["hide-input", "remove-output"]
  import os
  import ogcore.demographics as demog
  plot_path = os.path.join(os.path.abspath(''), 'images')

  fert_rates, fig = demog.get_fert(
      totpers=100,
      min_age=0,
      max_age=99,
      country_id="231",
      start_year=YEAR_TO_PLOT,
      end_year=YEAR_TO_PLOT,
      graph=True,
      plot_path=None,
      download_path=None,
  )
  plt.savefig(os.path.join(plot_path, "fert_rates.png"), dpi=300)
  plt.show()
  ```

  ```{figure} ./images/fert_rates.png
  ---
  height: 400px
  name: FigFertRatesETH
  ---
  Ethiopia fertility rates by age $\left(f_s\right)$ for $E+S=100$: year 2023
  ```

  The fertility rates in the UN data are births per 1,000 women of age-$s$. We adjust the units of those rates to represent the number of births per total population of both men and women of age-$s$.


(SecDemogMort)=
## Mortality rates

  The mortality rates in our model $\rho_{s,t}$ are a one-period hazard rate and represent the probability of dying within one year, given that an household is alive at the beginning of the period in which they are age-$s$. These data come from the United Nations Population Data Portal API for UN population data (see https://population.un.org/dataportal/about/dataapi). The model uses neonatal mortality rates (deaths per 1,000 live births, divided by 1,000) for the infant mortality rate from World Bank World Development Indicators, available at https://data.worldbank.org/indicator/SH.DYN.NMRT

  The mortality rates are a population-weighted average of the male and female mortality rates by one-year age increments reported by United Nations. The maximum age in years in our model is truncated to 100-years old. In addition, we constrain the mortality rate to be 1.0 or 100 percent at the maximum age of 100.

  ```{code-cell} ipython3
  :tags: ["hide-input", "remove-output"]

  import matplotlib.pyplot as plt
  import os
  import ogcore.demographics as demog

  plot_path = os.path.join(os.path.abspath(''), 'images')
  mort_rates, _, fig = demog.get_mort(
      totpers=100,
      min_age=0,
      max_age=99,
      country_id="231",
      start_year=YEAR_TO_PLOT,
      end_year=YEAR_TO_PLOT,
      graph=True,
      plot_path=None,
      download_path=None,
  )
  plt.xlabel(r"Age ($s$)")
  plt.ylabel(r"Mortality rate ($\rho_s$)")
  plt.savefig(os.path.join(plot_path, "mort_rates.png"), dpi=300)
  plt.show()
  ```

  ```{figure} ./images/mort_rates.png
  ---
  height: 400px
  name: FigMortRatesETH
  ---
  Ethiopia mortality rates by age $\left(\rho_{s,t}\right)$ for $E+S=100$: year 2023
  ```


(SecDemogImm)=
## Immigration rates

  Because of the difficulty in getting accurate immigration rate data by age, we estimate the immigration rates by age in our model $i_s$ as the average residual that reconciles the current-period population distribution with next period's population distribution given fertility rates $f_s$ and mortality rates $\rho_{s,t}$. Solving equations {eq}`EqPopLawofmotion` for the immigration rate $i_s$ gives the following characterization of the immigration rates in given population levels in any two consecutive periods $\omega_{s,t}$ and $\omega_{s,t+1}$ and the fertility rates $f_s$ and mortality rates $\rho_{s,t}$.

  ```{math}
  :label: EqPopImmRates
      i_{1,t} &= \frac{\omega_{1,t+1} - (1 - \rho_{0,t})\sum_{s=1}^{E+S}f_{s,t}\omega_{s,t}}{\omega_{1,t}}\quad\forall t \\
      i_{s+1,t+1} &= \frac{\omega_{s+1,t+1} - (1 - \rho_{s,t})\omega_{s,t}}{\omega_{s+1,t}}\qquad\qquad\forall t\quad\text{and}\quad 1\leq s \leq E+S-1
  ```

  ```{code-cell} ipython3
  :tags: ["hide-input", "remove-output"]
  import os
  import matplotlib.pyplot as plt
  import ogcore.demographics as demog
  plot_path = os.path.join(os.path.abspath(''), 'images')

  imm_rates, fig = demog.get_imm_rates(
      totpers=100,
      min_age=0,
      max_age=99,
      fert_rates=None,
      mort_rates=None,
      infmort_rates=None,
      pop_dist=None,
      country_id="231",
      start_year=YEAR_TO_PLOT,
      end_year=YEAR_TO_PLOT + 50,
      graph=True,
      plot_path=None,
      download_path=None,
  )
  plt.savefig(os.path.join(plot_path, "imm_rates.png"), dpi=300)
  plt.show()
  ```

  ```{figure} ./images/imm_rates.png
  ---
  height: 400px
  name: FigImmRatesETH
  ---
  Ethiopia immigration rates by age $\left(i_s\right)$ for $E+S=100$: year 2023
  ```

  We calculate our immigration rates for the consecutive-year-periods of population distribution data 2022 and 2023. The immigration rates $i_{s,t}$ that we use in our model are the the residuals described in {eq}`EqPopImmRates` implied by these two consecutive periods. {numref}`Figure %s <FigImmRatesETH>` shows the estimated immigration rates for $E+S=100$ and given the fertility rates from Section {ref}`SecDemogFert` and the mortality rates from Section {ref}`SecDemogMort`.

  At the end of Section {ref}`SecDemogPopSSTP`, we describe a small adjustment that we make to the immigration rates after a certain number of periods in order to make computation of the transition path equilibrium of the model compute more robustly.

(SecDemogIncome)=
## Differences by lifetime-income group

Since OG-Core 0.18 the fertility, mortality and immigration rates, and therefore the population distribution, can differ across the $J$ lifetime-income groups; the $\lambda_j$ then give the share of each cohort *born* into a group rather than its share of the population at every age. OG-Core takes an income *gradient* for each rate — the slope of the log-odds of the rate per percentile of the lifetime-income distribution — and re-solves the level of each rate at every age so that the UN aggregate rate is preserved exactly. The `OG-ZAF`, `OG-PHL` and `OG-IDN` migrations to that version pass no gradient, so their groups share one demographic profile. `OG-ETH` sets the gradients from Ethiopian measurements.

The measurements come from the [EAPD-DRB/Demographic-Gradients](https://github.com/EAPD-DRB/Demographic-Gradients) library, which collects wealth gradients in demographic rates for the OG-Core country models; its Ethiopian rows ship with this package in `ogeth/data/demographic_gradients_ETH.csv` and are read by `ogeth.calibrate.demographic_gradients`. A gradient in the library is the OLS slope of the log rate on wealth rank from 0 to 1, so it is the change in the log rate from the poorest to the richest household; OG-Core's gradient is per centered percentile point, so the library value is divided by 100. Negative means the poor have the higher rate.

- **Fertility.** From the 2024 Ethiopia Demographic and Health Survey, the total fertility rate by wealth quintile is 5.7, 4.4, 4.2, 3.9 and 2.9 children, a tilt of −0.74: the poorest quintile bears almost twice as many children as the richest. The same tilt is applied at every age of the fertility schedule.
- **Infant mortality.** From the same survey, 48, 36, 51, 33 and 26 deaths per thousand births by quintile, a tilt of −0.66 (the library's under-five tilt, −0.70, is used for ages 1–4).
- **Adult mortality.** Ethiopia has its own census measurement — the household deaths module of the 2007 census, with households ranked by an asset index. The gradient is steep among the young, −0.87 at ages 15–29, and flat at 30–44 (+0.08). At 45 and above the census measures *higher* mortality in wealthier households (+0.58 at 45–59, +0.44 at 60–74); the library flags this reversal, common to the poorest countries in its set, as at least partly a reporting artefact — a frail elderly relative moves into a better-off household before dying — and Ethiopia's summary tilt for ages 15–59 is essentially flat (+0.09). We therefore apply the measured tilts through age 44 and none from 45 on at the census year; ages 5–14, for which there is no measurement, also carry none.
- **The adult gradient steepens over time.** The census is from 2007, when Ethiopia's GNI per head was $210; it is $1,100 today, and the library finds that the adult-mortality gradient tracks national income closely across its 17 censuses (r = −0.88): $\text{tilt}(45q15) = 1.291 - 0.244\,\ln(\text{GNI per capita})$, so doubling income per head steepens the gradient by about 0.17. Ethiopia's flat 2007 measurement sits on that line. We therefore shift the measured tilts at ages 15–59 by the rule's change since 2007 — about −0.41 in 2025 — and let them keep steepening along the model's own 4.7 percent per-capita growth, stopping at $10,000 per head (about 2070), where the rule's fit ends. OG-Core accepts the gradient as a path over the full transition, so no change to the model was needed. The poorest quarter's mortality at age 30 is 1.35 times the richest percent's in 2025, 1.8 times by 2055 and 2.1 times in the long run; the probability of surviving from 20 to 65 is 70 percent for the poorest and 77 percent for the richest today, and 67 against 80 percent in the long run.

Two properties of the mechanics are worth keeping in mind. Because OG-Core preserves the UN aggregate at every age, the gradients redistribute births and deaths across groups without changing the total population path, so $g_n$ and the aggregate age distribution are unchanged; what changes is the joint distribution $\omega_{s,j}$ and the survival probabilities each group faces. And because the model's groups are defined by *lifetime income* while the surveys rank households by current *wealth*, the gradients are a proxy: a household's wealth rank and its lifetime-income rank are correlated but not the same thing.

```{figure} ./images/demographics_by_income.png
---
height: 500px
name: FigDemogIncome
---
Top: the measurements behind the gradients — DHS 2024 fertility and infant mortality by wealth quintile, and the 2007 census death rates by asset group and age band (dashed: the older bands that are not applied). Bottom: the tilts passed to OG-Core by age, and the survival curves by lifetime-income group they produce in the packaged steady state, with each group's share of the adult population against its share of births.
```

The effects on the packaged demographics are modest, for two reasons. The fertility gradient does not change how many households are born into each group — that is fixed by $\lambda_j$, and OG-Core's households have no children to raise — so its footprint is confined to the ages at which each group's births occur. And the adult-mortality gradient is applied only through age 44, where Ethiopia's census measures a gradient of the expected sign, while the deaths that shape the age distribution happen later. In the steady state the poorest quarter of births make up 24.5 percent of the adult population and the richest percent 1.02, against 25 and 1 without gradients; the probability of surviving from 20 to 65 is 73.1 percent in the poorest group and 74.2 in the richest. The remittance and transfer allocation matrices, which are per capita within groups, are rebuilt on the new distribution (`python -m ogeth.update_baseline --demographics-only` regenerates all of it from the UN data, without touching the rest of the file).

(SecDemogPopSSTP)=
## Population steady-state and transition path

  This model requires information about mortality rates $\rho_{s,t}$ in order to solve for the household's problem each period. It also requires the steady-state stationary population distribution $\bar{\omega}_{s}$ and population growth rate $\bar{g}_n$ as well as the full transition path of the stationary population distribution $\hat{\omega}_{s,t}$ and population grow rate $\tilde{g}_{n,t}$ from the current state to the steady-state. To solve for the steady-state and the transition path of the stationary population distribution, we write the stationary population dynamic equations {eq}`EqPopLawofmotionStat` and their matrix representation {eq}`EqPopLOMstatmat`.

  ```{math}
  :label: EqPopLawofmotionStat
      \hat{\omega}_{1,t+1} &= \frac{(1-\rho_{0,t})\sum_{s=1}^{E+S} f_{s,t}\hat{\omega}_{s,t} + i_{1,t}\hat{\omega}_{1,t}}{1+\tilde{g}_{n,t+1}}\quad\forall t \\
      \hat{\omega}_{s+1,t+1} &= \frac{(1 - \rho_{s,t})\hat{\omega}_{s,t} + i_{s+1,t}\hat{\omega}_{s+1,t}}{1+\tilde{g}_{n,t+1}}\qquad\quad\:\forall t\quad\text{and}\quad 1\leq s \leq E+S-1
  ```

  ```{math}
  :label: EqPopLOMstatmat
      & \begin{bmatrix}
        \hat{\omega}_{1,t+1} \\ \hat{\omega}_{2,t+1} \\ \hat{\omega}_{2,t+1} \\ \vdots \\ \hat{\omega}_{E+S-1,t+1} \\ \hat{\omega}_{E+S,t+1}
      \end{bmatrix}= \frac{1}{1 + g_{n,t+1}} \times ... \\
      & \begin{bmatrix}
        (1-\rho_0)f_1+i_1 & (1-\rho_0)f_2 & (1-\rho_0)f_3 & \cdots & (1-\rho_0)f_{E+S-1} & (1-\rho_0)f_{E+S} \\
        1-\rho_1 & i_2 & 0 & \cdots & 0 & 0 \\
        0 & 1-\rho_2 & i_3 & \cdots & 0 & 0 \\
        \vdots & \vdots & \vdots & \ddots & \vdots & \vdots \\
        0 & 0 & 0 & \cdots & i_{E+S-1} & 0 \\
        0 & 0 & 0 & \cdots & 1-\rho_{E+S-1} & i_{E+S}
      \end{bmatrix}
      \begin{bmatrix}
        \hat{\omega}_{1,t} \\ \hat{\omega}_{2,t} \\ \hat{\omega}_{2,t} \\ \vdots \\ \hat{\omega}_{E+S-1,t} \\ \hat{\omega}_{E+S,t}
      \end{bmatrix}
  ```

  We can write system {eq}`EqPopLOMstatmat` more simply in the following way.

  ```{math}
  :label: EqPopLOMstatmat2
    \boldsymbol{\hat{\omega}}_{t+1} = \frac{1}{1+g_{n,t+1}}\boldsymbol{\Omega}\boldsymbol{\hat{\omega}}_t \quad\forall t
 ```

  The stationary steady-state population distribution $\boldsymbol{\bar{\omega}}$ is the eigenvector $\boldsymbol{\omega}$ with eigenvalue $(1+\bar{g}_n)$ of the matrix $\boldsymbol{\Omega}$ that satisfies the following version of {eq}`EqPopLOMstatmat2`.

  ```{math}
  :label: EqPopLOMss
    (1+\bar{g}_n)\boldsymbol{\bar{\omega}} = \boldsymbol{\Omega}\boldsymbol{\bar{\omega}}
  ```

  ```{admonition} Proposition
  :class: tip
  If the age $s=1$ immigration rate is $i_1>-(1-\rho_0)f_1$ and the other immigration rates are strictly positive $i_s>0$ for all $s\geq 2$ such that all elements of $\boldsymbol{\Omega}$ are nonnegative, then there exists a unique positive real eigenvector $\boldsymbol{\bar{\omega}}$ of the matrix $\boldsymbol{\Omega}$, and it is a stable equilibrium.

  **Proof:**
  First, note that the matrix $\boldsymbol{\Omega}$ is square and non-negative.  This is enough for a general version of the Perron-Frobenius Theorem to state that a positive real eigenvector exists with a positive real eigenvalue. This is not yet enough for uniqueness. For it to be unique by a version of the Perron-Fobenius Theorem, we need to know that the matrix is irreducible. This can be easily shown. The matrix is of the form

  $$
  \boldsymbol{\Omega} =
    \begin{bmatrix}
      * & *  & * & \cdots & * & * & *\\
      * & * & 0 & \cdots & 0 & 0 & 0 \\
      0 & * & * & \cdots & 0 & 0 & 0 \\
      \vdots & \vdots & \vdots & \ddots & \vdots & \vdots & \vdots \\
      0 & 0 & 0 & \cdots & *  & * & 0 \\
      0 & 0 & 0 & \cdots & 0 & * & *
    \end{bmatrix}
  $$

  Where each * is strictly positive. It is clear to see that taking powers of the matrix causes the sub-diagonal positive elements to be moved down a row and another row of positive entries is added at the top. None of these go to zero since the elements were all non-negative to begin with.

  $$
  \boldsymbol{\Omega}^2 =
    \begin{bmatrix}
      * & *  & * & \cdots & * & * & *\\
      * & * & * & \cdots & * & * & * \\
      0 & * & * & \cdots & 0 & 0 & 0 \\
      \vdots & \vdots & \vdots & \ddots & \vdots & \vdots & \vdots \\
      0 & 0 & 0 & \cdots & *  & * & 0 \\
      0 & 0 & 0 & \cdots & 0 & * & *
    \end{bmatrix}; ~~~
    \boldsymbol{\Omega}^{S+E-1} =
    \begin{bmatrix}
      * & *  & * & \cdots & * & * & *\\
      * & * & * & \cdots & * & * & * \\
      * & * & * & \cdots & * & * & * \\
      \vdots & \vdots & \vdots & \ddots & \vdots & \vdots & \vdots \\
      * & * & * & \cdots & *  & * & * \\
      0 & 0 & 0 & \cdots & 0 & * & *
    \end{bmatrix}
    $$

  $$
  \boldsymbol{\Omega}^{S+E} =
      \begin{bmatrix}
      * & *  & * & \cdots & * & * & *\\
      * & * & * & \cdots & * & * & * \\
      * & * & * & \cdots & * & * & * \\
      \vdots & \vdots & \vdots & \ddots & \vdots & \vdots & \vdots \\
      * & * & * & \cdots & * & * & * \\
      * & * & * & \cdots & * & * & *
    \end{bmatrix}
  $$

  Existence of an $m \in \mathbb{N}$ such that $\left(\bf\Omega^m\right)_{ij} \neq 0 ~~ ( > 0)$ is one of the definitions of an irreducible (primitive) matrix. It is equivalent to saying that the directed graph associated with the matrix is strongly connected. Now the Perron-Frobenius Theorem for irreducible matrices gives us that the equilibrium vector is unique.

  We also know from that theorem that the eigenvalue associated with the positive real eigenvector will be real and positive. This eigenvalue, $p$, is the Perron eigenvalue and it is the steady state population growth rate of the model. By the PF Theorem for irreducible matrices, $| \lambda_i | \leq p$ for all eigenvalues $\lambda_i$ and there will be exactly $h$ eigenvalues that are equal, where $h$ is the period of the matrix. Since our matrix $\bf\Omega$ is aperiodic, the steady state growth rate is the unique largest eigenvalue in magnitude. This implies that almost all initial vectors will converge to this eigenvector under iteration.
  ```

  For a full treatment and proof of the Perron-Frobenius Theorem, see {cite}`Suzumura:1983`. Because the population growth process is exogenous to the model, we calibrate it to annual age data for age years $s=1$ to $s=100$.

  {numref}`Figure %s <FigOrigVsFixSSpop>` shows the steady-state population distribution $\boldsymbol{\bar{\omega}}$ and the population distribution after 120 periods $\boldsymbol{\hat{\omega}}_{120}$. Although the two distributions look very close to each other, they are not exactly the same.

  ```{figure} ./images/OrigVsFixSSpop.png
  ---
  height: 500px
  name: FigOrigVsFixSSpop
  ---
  Theoretical steady-state population distribution vs. population distribution at period $t=120$
  ```

  Further, we find that the maximum absolute difference between the population levels $\hat{\omega}_{s,t}$ and $\hat{\omega}_{s,t+1}$ was less than $1\times 10^{-4}$ after 160 periods. That is to say, that after 160 periods, given the estimated mortality, fertility, and immigration rates, the population has not achieved its steady state. For convergence in our solution method over a reasonable time horizon, we want the population to reach a stationary distribution after $T$ periods. To do this, we artificially impose that the population distribution in period $t=120$ is the steady-state. As can be seen from {numref}`Figure %s <FigOrigVsFixSSpop>`, this assumption is not very restrictive. {numref}`Figure %s <FigImmRateChg>` shows the change in immigration rates that would make the period $t=120$ population distribution equal be the steady-state. The maximum absolute difference between any two corresponding immigration rates in {numref}`Figure %s <FigImmRateChg>` is very small.

  ```{figure} ./images/OrigVsAdjImm.png
  ---
  height: 500px
  name: FigImmRateChg
  ---
  Original immigration rates vs. adjusted immigration rates to make fixed steady-state population distribution
  ```

  We begin with 2023 population data and use the population transition matrix {eq}`EqPopLOMstatmat2` to age it to the start year of the model (e.g., 2024 or 2025). We then use {eq}`EqPopLOMstatmat2` to generate the transition path of the population distribution over the time period of the model. {numref}`Figure %s <FigPopDistPath>` shows the progression from the 2023 population data to the fixed steady-state at period $t=120$. The time path of the growth rate of the economically active population $\tilde{g}_{n,t}$ is shown in {numref}`Figure %s <FigPopDistPath>`.

  ```{figure} ./images/pop_distribution.png
  ---
  height: 500px
  name: FigPopDistPath
  ---
  Exogenous stationary population distribution at periods along transition path
  ```

  ```{code-cell} ipython3
  :tags: ["hide-input", "remove-output"]
  import os
  import ogcore.demographics as demog
  import matplotlib.pyplot as plt
  YEAR_TO_PLOT = 2023
  plot_path = os.path.join(os.path.abspath(''), 'images')
  fig = pp.plot_pop_growth(
      p,
      start_year=YEAR_TO_PLOT,
      num_years_to_plot=150,
      include_title=False,
      path=None,
  )
  # Add average growth rate with this
  plt.plot(
      np.arange(YEAR_TO_PLOT, YEAR_TO_PLOT + 150),
      np.ones(150) * np.mean(p.g_n[:150]),
      linestyle="-",
      linewidth=1,
      color="red",
  )
  plt.xlabel(r"Model Period ($t$)")
  plt.ylabel(r"Population Growth Rate ($g_{n,t}$)")
  plt.savefig(os.path.join(plot_path, "population_growth_rates.png"), dpi=300)
  plt.show()
  ```

  ```{figure} ./images/population_growth_rates.png
  ---
  height: 500px
  name: FigGrowthPath
  ---
  Time path of the population growth rate $\tilde{g}_{n,t}$
  ```


[^calibage_note]: Theoretically, the model works without loss of generality for $S\geq 3$. However, because we are calibrating the ages outside of the economy to be one-fourth of $S$ (e.g., ages 21 to 100 in the economy, and ages 1 to 20 outside of the economy), it is convenient for $S$ to be at least 4.
[^houseprob_note]: The parameter $\rho_s$ is the probability that a household of age $s$ dies before age $s+1$.
[^un_data_portal]: Note that you might need a UN Data Portal API token to download the data directly from the United Nations Data Portal site. But the [`demographics.py`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/demographics.py) module will take the data from a pre-downloaded site if the API token is missing or fails.

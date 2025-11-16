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

Demographics are a key component of the macroeconmic model. {cite}`Nishiyama:2015` and {cite}`DeBackerEtAl:2019` have recently shown that demographic dynamics are likely the biggest influence on macroeconomic time series, exhibiting more influence than fiscal variables or household preference parameters.

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

   Our data for Ethiopia fertility rates by age come from United Nations fertility rate data for a country for some range of years (at least one year) and by age. The country_id=710 is for Ethiopia. These data come from the United Nations Data Portal API for UN population data (see https://population.un.org/dataportal/about/dataapi). The UN variable code for Population by 1-year age groups and sex is "47" and that for Fertility rates by age of mother (1-year) is "68".

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
      country_id="710",
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
      country_id="710",
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
      country_id="710",
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

  We calculate our immigration rates for the consecutive-year-periods of population distribution data 2022 and 2023. The immigration rates $i_{s,t}$ that we use in our model are the the residuals described in {eq}`EqPopImmRates` implied by these two consecutive periods. {numref}`Figure %s <FigImmRatesETH>` shows the estimated immigration rates for $E+S=100$ and given the fertility rates from Section {ref}`SecDemogFert` and the mortality rates from Section {ref}`SecDemogMort`. These immigration rates show large out-migration from Ethiopia.[^out_migration]

  At the end of Section {ref}`SecDemogPopSSTP`, we describe a small adjustment that we make to the immigration rates after a certain number of periods in order to make computation of the transition path equilibrium of the model compute more robustly.

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
[^out_migration]: Out migration in Ethiopia is clearly a significant trend. {cite}`BusinessTech:2024` reports that "since 2000, around 413,000 Ethiopians have emigrated to other countries - and in 2022, just under 28,000 made their way back."

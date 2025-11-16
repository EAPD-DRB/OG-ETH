---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.8'
    jupytext_version: '1.4.1'
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

(Chap_Exog)=
# Exogenous Parameters


  The JSON file [`ogeth_default_parameters.json`](https://github.com/EAPD-DRB/OG-ETH/blob/master/ogeth/ogeth_default_parameters.json) provides values for all the model parameters used as defaults for `OG-ETH`. Below, we provide a table highlighting some of the parameters describing the scale of the model (number of periods, aged, productivity types) and some parameters of the solution method (dampening parameter for TPI). The table below provides a list of the exogenous parameters and their baseline calibration values.

  <!-- +++
  ```{code-cell} ogeth-dev
  :tags: [hide-cell]
  from myst_nb import glue
  import ogcore.parameter_tables as pt
  from ogcore import Specifications
  import ogeth
  import importlib
  import json
  p = Specifications()
  with importlib.resources.open_text(
      "ogeth", "ogeth_default_parameters.json"
      ) as file:
          defaults = json.load(file)
  table = pt.param_table(p, table_format="md", path=None)
  glue("param_table", table, display=False)
  ```
  -->

 | Symbol                           | Description                                                             | Value                                                 |
|:---------------------------------|:------------------------------------------------------------------------|:------------------------------------------------------|
| $\texttt{start_year}$           | Initial year                                                            | 2025                                                  |
| $\omega_{s,t}$                   | Population by age over time                                             | Too large to report here, see default parameters JSON |
| $i_{s,t}$                        | Immigration rates by age                                                | Too large to report here, see default parameters JSON |
| $\rho_{s,t}$                     | Mortality rates by age                                                  | Too large to report here, see default parameters JSON |
| $e_{j,s,t}$                      | Deterministic ability process                                           | Too large to report here, see default parameters JSON |
| $\lambda_{j}$                    | Lifetime income group percentages                                       | Too large to report here, see default parameters JSON |
| $J$                              | Number of lifetime income groups                                        | 7                                                     |
| $S$                              | Maximum periods in economically active individual life                  | 80                                                    |
| $E$                              | Number of periods of youth economically outside the model               | 20                                                    |
| $T$                              | Number of periods to steady-state                                       | 320                                                   |
| $R$                              | Retirement age                                                          | [65.000...65.000]                                     |
| $\tilde{l}$                      | Maximum hours of labor supply                                           | 1.000                                                 |
| $\beta$                          | Discount factor                                                         | [0.960...0.960]                                       |
| $\sigma$                         | Coefficient of constant relative risk aversion                          | 1.500                                                 |
| $\nu$                            | Frisch elasticity of labor supply                                       | 0.400                                                 |
| $b$                              | Scale parameter in utility of leisure                                   | 0.573                                                 |
| $\upsilon$                       | Shape parameter in utility of leisure                                   | 2.856                                                 |
| $\chi^{n}_{s}$                   | Disutility of labor level parameters                                    | Too large to report here, see default parameters JSON |
| $\chi^{b}_{j}$                   | Utility of bequests level parameters                                    | [80.000...80.000]                                     |
| $\texttt{use_zeta}$             | Whether to distribute bequests between lifetime income groups           | 0.00E+00                                              |
| $\zeta$                          | Distribution of bequests                                                | Too large to report here, see default parameters JSON |
| $Z_{t}$                          | Total factor productivity                                               | Too large to report here, see default parameters JSON |
| $\gamma$                         | Capital share of income                                                 | [0.401...0.401]                                       |
| $\varepsilon$                    | Elasticity of substitution between capital and labor                    | [1.000...1.000]                                       |
| $\delta$                         | Capital depreciation rate                                               | 0.050                                                 |
| $g_{y}$                          | Growth rate of labor augmenting technological progress                  | 0.00E+00                                              |
| $\texttt{tax_func_type}$       | Functional form used for income tax functions                           | linear                                                |
| $\texttt{analytical_mtrs}$      | Whether use analytical MTRs or estimate MTRs                            | 0.00E+00                                              |
| $\texttt{age_specific}$         | Whether use age-specific tax functions                                  | 0.00E+00                                              |
| $\tau^{p}_{t}$                   | Payroll tax rate                                                        | [0.000...0.000]                                       |
| $\tau^{BQ}_{t}$                  | Bequest (estate) tax rate                                               | [0.200...0.200]                                       |
| $\tau^{b}_{t}$                   | Entity-level business income tax rate                                   | Too large to report here, see default parameters JSON |
| $\delta^{\tau}_{t}$              | Rate of depreciation for tax purposes                                   | Too large to report here, see default parameters JSON |
| $\tau^{c}_{t,s,j}$               | Consumption tax rates                                                   | Too large to report here, see default parameters JSON |
| $H$                              | Coefficient on linear term in wealth tax function                       | [0.100...0.100]                                       |
| $M$                              | Constant in wealth tax function                                         | [1.000...1.000]                                       |
| $P$                              | Coefficient on level term in wealth tax function                        | [0.000...0.000]                                       |
| $\texttt{budget_balance}$       | Whether have a balanced budget in each period                           | 0.00E+00                                              |
| $\texttt{baseline_spending}$    | Whether level of spending constant between the baseline and reform runs | 0.00E+00                                              |
| $\alpha^{T}_{t}$                 | Transfers as a share of GDP                                             | [0.041...0.041]                                       |
| $\eta_{j,s,t}$                   | Distribution of transfers                                               | Too large to report here, see default parameters JSON |
| $\alpha^{G}_{t}$                 | Government spending as a share of GDP                                   | [0.267...0.267]                                       |
| $t_{G1}$                         | Model period in which budget closure rule starts                        | 20                                                    |
| $t_{G2}$                         | Model period in which budget closure rule ends                          | 256                                                   |
| $\rho_{G}$                       | Budget closure rule smoothing parameter                                 | 0.100                                                 |
| $\bar{\alpha}_{D}$               | Steady-state Debt-to-GDP ratio                                          | 1.200                                                 |
| $\alpha_{D,0}$                   | Initial period Debt-to-GDP ratio                                        | 0.740                                                 |
| $\tau_{d,t}$                     | Scale parameter in government interest rate wedge                       | [0.245...0.245]                                       |
| $\mu_{d,t}$                      | Shift parameter in government interest rate wedge                       | [-0.034...-0.034]                                     |
| $\texttt{avg_earn_num_years}$ | Number of years over which compute average earnings for pension benefit | 35                                                    |
| $\texttt{AIME_bkt_1}$          | First AIME bracket threshold                                            | 749.000                                               |
| $\texttt{AIME_bkt_2}$          | Second AIME bracket threshold                                           | 4517.000                                              |
| $\texttt{PIA_rate_bkt_1}$     | First AIME bracket PIA rate                                             | 0.00E+00                                              |
| $\texttt{PIA_rate_bkt_2}$     | Second AIME bracket PIA rate                                            | 0.00E+00                                              |
| $\texttt{PIA_rate_bkt_3}$     | Third AIME bracket PIA rate                                             | 0.00E+00                                              |
| $\texttt{PIA_maxpayment}$       | Maximum PIA payment                                                     | 0.00E+00                                              |
| $\texttt{PIA_minpayment}$       | Minimum PIA payment                                                     | 0.00E+00                                              |
| $\theta_{adj,t}$                 | Adjustment to replacement rate                                          | [1.000...1.000]                                       |
| $r^{*}_{t}$                      | World interest rate                                                     | [0.040...0.040]                                       |
| $D_{f,0}$                        | Share of government debt held by foreigners in initial period           | 0.237                                                 |
| $\zeta_{D, t}$                   | Share of new debt issues purchased by foreigners                        | [0.237...0.237]                                       |
| $\zeta_{K, t}$                   | Share of excess capital demand satisfied by foreigners                  | [0.900...0.900]                                       |
| $\xi$                            | Dampening parameter for TPI                                             | 0.400                                                 |
| $\texttt{maxiter}$               | Maximum number of iterations for TPI                                    | 250                                                   |
| $\texttt{mindist_SS}$           | SS solution tolerance                                                   | 1.00E-09                                              |
| $\texttt{mindist_TPI}$          | TPI solution tolerance                                                  | 1.00E-05                                              |

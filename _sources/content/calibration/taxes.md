(Chap_Tax)=
# Taxes in OG-ETH

The government is not an optimizing agent in `OG-ETH`. The government levies taxes on household income, corporate income, and value added. With these resources, the government provides transfers to households, spends resources on public goods, and makes rule-based adjustments to stabilize the economy in the long-run. The government can run budget deficits or surpluses in a given year and must, therefore, be able to accumulate debt or savings.  The spending and debt parameters are discussed in Chapter {ref}`Chap_MacroCalib`.  Taxes are discussed in this chapter.


## Personal income taxes
The government sector influences households through two terms in the household budget constraint {eq}`EqHHBC`---government transfers $TR_{t}$ and through the total tax liability function $T_{s,t}$, which can be decomposed into the effective tax rate times total income. In this chapter, we detail the household tax component of government activity $T_{s,t}$ in `OG-ETH`.

```{math}
:label: EqHHBC
  c_{j,s,t} + b_{j,s+1,t+1} &= (1 + r_{hh,t})b_{j,s,t} + w_t e_{j,s} n_{j,s,t} + \\
  &\quad\quad\zeta_{j,s}\frac{BQ_t}{\lambda_j\omega_{s,t}} + \eta_{j,s,t}\frac{TR_{t}}{\lambda_j\omega_{s,t}} + ubi_{j,s,t} - T_{s,t}  \\
  &\quad\forall j,t\quad\text{and}\quad s\geq E+1 \quad\text{where}\quad b_{j,E+1,t}=0\quad\forall j,t
```

The total tax function, $T_{s,t}$, is a function of personal income taxes, taxes on bequests, and wealth taxes.  In the default calibration, wealth and bequest taxes are set to zero in `OG-ETH`. Personal income taxes are modeled as linear taxes and set to average effective and marginal tax rates.  The [OG-Core documentation](https://pslmodels.github.io/OG-Core/content/theory/government.html#taxes) details more detailed ways to match the progressivity of the tax system.  But given limited data for Ethiopia, we start with simple linear tax rates of 22% for effective tax rates on personal income, a 25% marginal tax rate on capital income, and a 31\% marginal tax rate on labor income.

## Corporate income taxes

`OG-ETH` uses the top statutory rate of 27% for the corporate income tax rate.

## Value-added taxes

A value-added tax rate of 15% is applied with the `tau_c` parameter.

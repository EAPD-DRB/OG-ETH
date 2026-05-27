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

glue("etr_rate", pct(params["etr_params"][0][0][0]), display=False)
glue("mtrx_rate", pct(params["mtrx_params"][0][0][0]), display=False)
glue("mtry_rate", pct(params["mtry_params"][0][0][0]), display=False)
glue("payroll_rate", pct(params["tau_payroll"][0]), display=False)
glue("cit_rate", pct(params["cit_rate"][0][0]), display=False)
glue("tau_c_rate", pct(params["tau_c"][0][0]), display=False)
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

The total tax function, $T_{s,t}$, is a function of personal income taxes, taxes on bequests, and wealth taxes.  In the default calibration, wealth and bequest taxes are set to zero in `OG-ETH`. Personal income taxes are modeled as linear taxes and set to average effective and marginal tax rates.  The [OG-Core documentation](https://pslmodels.github.io/OG-Core/content/theory/government.html#taxes) details more detailed ways to match the progressivity of the tax system.  But given limited data for Ethiopia, we start with simple linear tax rates of {glue:text}`etr_rate` for effective tax rates on personal income, a {glue:text}`mtrx_rate` marginal tax rate on capital income, and a {glue:text}`mtry_rate` marginal tax rate on labor income.

We model payroll taxes as a flat {glue:text}`payroll_rate` rate, consistent with [this PWC report on taxation in Ethiopia](https://taxsummaries.pwc.com/ethiopia/individual/other-taxes#:~:text=Employers%20are%20required%20to%20contribute,employee's%20contribution%20is%20at%207%25).

## Corporate income taxes

`OG-ETH` uses the statutory rate of {glue:text}`cit_rate` for the corporate income tax rate.

## Value-added taxes

A value-added tax rate of {glue:text}`tau_c_rate` is applied with the `tau_c` parameter.

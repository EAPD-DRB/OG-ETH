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

(Chap_UNtutor_3perOG)=
# A "Simple" 3-period-lived agent OG model


(SecUNtutorial_3perOGwhysimp)=
## Why this "simple" theory?

  Almost every module of the OG-Core model is straightforward on its own in terms of theory, mathematics, and intuition. Most undergraduate students with basic economics and mathematical training are able to understand them quickly. Examples include:

  - The [`household.py`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/household.py) module that has all the functions that come from the theory of household decision making in the "[Households](https://pslmodels.github.io/OG-Core/content/theory/households.html)" chapter of the OG-Core documentation,
  - The [`firm.py`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/firm.py) module that has all the functions that come from the theory of firms' decisions about how much capital to rent and how much labor to hire as described in the "[Firms](https://pslmodels.github.io/OG-Core/content/theory/firms.html)" chapter of the OG-Core documentation, and
  - The [`demographics.py`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/demographics.py) module that has the functions that generate the population distribution and how it changes over time as described in the "[Demographics](https://pslmodels.github.io/OG-Core/content/theory/demographics.html)" chapter  of the OG-Core documentation.

  In contrast, users of the country calibrations of the OG-Core macroeconomic model often struggle to understand the difference and relationship between the steady-state equilibrium solution and the transition path equilibrium solution and why those algorithms in [`SS.py`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/SS.py) and [`TPI.py`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/TPI.py) are so complex. Indeed, understanding the transition path solution algorithm often requires more in-depth theoretical and mathematical training.

  The text of this chapter is almost exactly Chapter 2 of {cite}`DeBackerEvans:2024`.[^OGtextbook] The model presented in this chapter is nearly the simplest version of the OG model. It is "nearly" the simplest because we start with overlapping generations of agents who live for three periods. The simplest overlapping generations model is a two-period-lived agent model as described in Chapter 1 of {cite}`DeBackerEvans:2024`. Although the two-period-lived agent model seems like the natural starting place, that model is fundamentally different from any OG model in which agents live for three periods or more.[^2perSimp] We start with the three-period-lived agent model because its solution method and results are similar for all life spans $S\geq 3$.

  The model presented here is a perfect foresight, three-period-lived agent OG model. The model in this chapter has trivial demographics in that a unit measure of agents are born each period, and each generation of agents lives for three periods. There is no population growth because the population in each period equals 3 (young, middle-aged, and old), and the mortality rate is zero in every period except the last period in which it is one. And the agents inelastically supply labor. We also characterize "nearly" the simplest production sector with a unit measure of infinitely lived, perfectly competitive firms that rent capital and hire labor from households.[^SimpProd] There is no government sector in that agents and firms in the model pay no taxes nor receive any transfers.


(SecUNtutorial_3perOGhh)=
## Households

  A unit measure of identical individuals are born each period and live for three periods. Let the age of an individual be indexed by $s = \{1,2,3\}$. In general, an age-$s$ individual faces a budget constraint each period that looks like the following,
  ```{math}
  :label: EqUNtut_HHbc
    c_{s,t} + b_{s+1,t+1} = w_t n_{s,t} + (1 + r_{t})b_{s,t} \quad\forall s,t
  ```
  where $c_{s,t}$ is consumption and $n_{s,t}$ is labor supply by age-$s$ individuals in period $t$. The variable $b_{s+1,t+1}$ is savings by age-$s$ individuals in period $t$ to be returned to them with interest in the next period, and $b_{s,t}$ is the savings with which the age-$s$ agent entered period $t$ that was chosen in the previous period. The current period wage $w_t$ and interest rate $r_t$ are the same for all agents (no age $s$ subscript).

  We assume the individuals supply a unit of labor inelastically in the first two periods of life and are retired in the last period of life.
  ```{math}
  :label: EqUNtut_HHlab
    n_{s,t} =
      \begin{cases}
        1\quad\:\:\:\,\text{if}\quad s = 1,2 \\
        0.2\quad\text{if}\quad s = 3
      \end{cases} \quad\forall t
  ```
  We also assume that individuals are born with no savings $b_{1,t} = 0$ and that they save no income in the last period of their lives $b_{4,t}=0$ for all periods $t$.

  These assumptions give rise to the three age-specific budget constraints derived from the general version Equation {eq}`EqUNtut_HHbc`.[^3perGenToS]
  ```{math}
  :label: EqUNtut_HHbc1
    c_{1,t} + b_{2,t+1} = w_t \quad\forall t
  ```
  ```{math}
  :label: EqUNtut_HHbc2
    c_{2,t+1} + b_{3,t+2} = w_{t+1} + (1 + r_{t+1})b_{2,t+1} \quad\forall t
  ```
  ```{math}
  :label: EqUNtut_HHbc3
    c_{3,t+2} = 0.2w_{t+2} + (1 + r_{t+2})b_{3,t+2} \quad\forall t
  ```

  We assume that consumption must be nonnegative $c_{s,t}\geq 0$ for all $s$ and $t$.[^Cnonneg] And we assume that $b_{2,t} + b_{3,t}>0$ because the aggregate capital stock must be strictly positive.

  Let the utility of consumption in each period be defined by a function $u(c_{s,t})$, such that $u'>0$, $u''<0$, and $\lim_{c\rightarrow 0}u(c) = -\infty$. We will use the constant relative risk aversion (CRRA) utility function that takes the following form,
  ```{math}
  :label: EqUNtut_HHutil
    u(c_{s,t}) = \frac{(c_{s,t})^{1-\sigma}- 1}{1-\sigma} \quad\forall s,t \quad\text{and}\quad c_{s,t}>0
  ```
  where the parameter $\sigma\geq 1$ represents the coefficient of relative risk aversion.

  Individuals choose lifetime consumption $\{c_{s,t+s-1}\}_{s=1}^3$, savings $\{b_{s+1,t+s}\}_{s=1}^2$ to maximize lifetime utility, subject to the budget constraints and non negativity constraints.
  ```{math}
  :label: EqUNtut_HHmaxprob
    &\max_{\{c_{s,t+s-1}\}_{s=1}^3,\{b_{s+1,t+s}\}_{s=1}^2}\:u(c_{1,t}) + \beta u(c_{2,t+1}) + \beta^2 u(c_{3,t+2}) \\
    &\quad\quad c_{1,t} = w_t - b_{2,t+1} \\
    &\quad\quad c_{2,t+1} = w_{t+1} + (1 + r_{t+1})b_{2,t+1} - b_{3,t+2} \\
    &\quad\quad c_{3,t+2} = 0.2w_{t+2}+(1 + r_{t+2})b_{3,t+2}
  ```
  The number of variables to choose in the household's optimization problem can be reduced by substituting the budget constraints into the optimization problem Equation {eq}`EqUNtut_HHmaxprob` and assuming that the non-negativity constraints on the two capital stocks do not bind.[^ReduceProb]
  ```{math}
  :label: EqUNtut_HHlagrang
    \max_{b_{2,t+1},b_{3,t+2}}\:\mathcal{L} = &u\Bigl(w_t - b_{2,t+1}\Bigr) + \beta u\Bigl(w_{t+1} + [1 + r_{t+1}]b_{2,t+1} - b_{3,t+2}\Bigr) ... \\
    &\quad\quad + \beta^2 u\Bigl([1 + r_{t+2}]b_{3,t+2} + 0.2w_{t+2}\Bigr)
  ```

  The optimal choice of how much to save in the second period of life $b_{3,t+2}$ is given by taking the derivative of the Lagrangian Equation {eq}`EqUNtut_HHlagrang` with respect to $b_{3,t+2}$ and setting it equal to zero.
  ```{math}
  :label: EqUNtut_HHfock3
    \frac{\partial\mathcal{L}}{\partial b_{3,t+2}} = 0 \quad\Rightarrow\quad &u'\bigl(c_{2,t+1}\bigr) = \beta(1 + r_{t+2})u'\bigl(c_{3,t+2}\bigr) \\
    \Rightarrow\quad &u'\Bigl(w_{t+1} + [1 + r_{t+1}]b_{2,t+1} - b_{3,t+2}\Bigr) = ... \\
    &\quad\quad \beta(1 + r_{t+2})u'\Bigl([1 + r_{t+2}]b_{3,t+2} + 0.2w_{t+2}\Bigr)
  ```
  Equation {eq}`EqUNtut_HHfock3` implies that the optimal savings for age-2 individuals is a function $\psi_{2,t+1}$ of the wage and interest rate in that period, the interest rate in the next period, and how much capital the individual saved in the previous period.
  ```{math}
  :label: EqUNtut_HHk3funcpe
    b_{3,t+2} = \psi_{2,t+1}\Bigl(b_{2,t+1},w_{t+1},r_{t+1},r_{t+2},w_{t+2}\Bigr)
  ```

  The optimal choice of how much to save in the first period of life $b_{2,t+1}$ is a little more involved. The first order condition of the Lagrangian includes derivatives of $b_{3,t+2}$ with respect to $b_{2,t+1}$ because Equations {eq}`EqUNtut_HHfock3` and {eq}`EqUNtut_HHk3funcpe` show that optimal middle-aged savings $b_{3,t+2}$ is a function of savings when young $b_{2,t+1}$.
  ```{math}
  :label: EqUNtut_HHfock2a
    \frac{\partial\mathcal{L}}{\partial b_{2,t+1}} = 0 \quad\Rightarrow\quad &-u'\bigl(c_{1,t}\bigr)  + \beta(1+r_{t+1})u'\bigl(c_{2,t+1}\bigr) ... \\
    &\quad - \beta u'\bigl(c_{2,t+1}\bigr)\frac{\partial\psi_{2,t+1}}{\partial b_{2,t+1}} + \beta^2(1+r_{t+2})u'\bigl(c_{3,t+2}\bigr)\frac{\partial\psi_{2,t+1}}{\partial b_{2,t+1}} = 0 \\
    \Rightarrow\quad &u'\Bigl(w_{t} - b_{2,t+1}\Bigr) = \\
    &\quad\beta(1 + r_{t+1})u'\Bigl([1 + r_{t+1}]b_{2,t+1} + w_{t+1} - b_{3,t+2}\Bigr) ... \\
    &\quad - \beta\frac{\partial \psi_{2,t+1}}{\partial b_{2,t+1}}\biggl[u'(c_{2,t+1}) - \beta(1+r_{t+2})u'(c_{3,t+2})\biggr]
  ```

  Notice that the term in the brackets on the third line of Equation {eq}`EqUNtut_HHfock2a` equals zero because of the optimality condition Equation {eq}`EqUNtut_HHfock3` for $b_{3,t+1}$. This is the envelope condition or the principle of optimality. The intuition is that I don't need to worry about the effect of my choice today on my choice tomorrow because I will optimize tomorrow given today. So the first order condition for optimal savings when young $b_{2,t+1}$ simplifies to the following expression.

  ```{math}
  :label: EqUNtut_HHfock2b
    \frac{\partial\mathcal{L}}{\partial b_{2,t+1}} = 0 \quad\Rightarrow\quad &u'\bigl(c_{1,t}\bigr) = \beta(1 + r_{t+1})u'\bigl(c_{2,t+1}\bigr) \\
    \Rightarrow\quad &u'\Bigl(w_{t} - b_{2,t+1}\Bigr) = ... \\
    &\quad \beta(1 + r_{t+1})u'\Bigl(w_{t+1} + [1 + r_{t+1}]b_{2,t+1} - \psi_{2,t+1}\Bigr)
  ```

  Equation {eq}`EqUNtut_HHfock2b` implies that the optimal savings for age-1 individuals is a function of the wages in that period and the next period and the interest rate in the next period and in the period after that.[^EnvelopeCond]
  ```{math}
  :label: EqUNtut_HHk2funcpe
    b_{2,t+1} = \psi_{1,t}\Bigl(w_t,w_{t+1},r_{t+1},r_{t+2},w_{t+2}\Bigr)
  ```

  Instead of looking at the age-1 and age-2 savings decisions of a particular individual, which happen in consecutive periods, we could look at the age-1 savings decisions of the young in period $t$ as characterized in Equation {eq}`EqUNtut_HHfock2b` and the age-2 savings decisions of the middle-aged in period $t$. This savings $b_{3,t+1}$ is characterized by the following first order condition, which is simply Equation {eq}`EqUNtut_HHfock3` iterated backward in time one period,
  ```{math}
  :label: EqUNtut_HHfock3b
    u'\bigl(c_{2,t}\bigr) &= \beta(1+r_{t+1})u'\bigl(c_{3,t+1}\bigr) \\
    u'\Bigl(w_t + [1 + r_t]b_{2,t} - b_{3,t+1}\Bigr) &= \beta(1 + r_{t+1})u'\Bigl(0.2w_{t+1} + [1 + r_{t+1}]b_{3,t+1}\Bigr)
  ```
  which implies that the period-$t$ savings decision of the middle aged is a function of the wage and interest rate in period-$t$, the interest rate in the period $t+1$, and how much capital the individual saved in the previous period.
  ```{math}
  :label: EqUNtut_HHk3funcpeb
    b_{3,t+1} = \psi_{2,t}\Bigl(b_{2,t},w_{t},r_{t},r_{t+1},w_{t+1}\Bigr)
  ```

  Define $\Gamma_t$ as the distribution of household savings across households at time $t$.
  ```{math}
  :label: EqUNtut_HHSaveDist
    \Gamma_t \equiv \bigl\{b_{2,t},b_{3,t}\bigr\} \quad\forall t
  ```
  As will be shown in Section {ref}`SecUNtutorial_3perOGeqlb`, the state as defined in {prf:ref}`DefUNtut_StateSpace` in every period $t$ for the entire equilibrium system described in the non-steady-state equilibrium characterized in {prf:ref}`DefUNtut_3perSimpNSSEql` is the current distribution of individual savings $\Gamma_t$ from Equation {eq}`EqUNtut_HHSaveDist`. Because individuals must forecast wages and interest rates in every period in order to solve their optimal lifetime decisions and because each of those future variables depends on the entire distribution of savings in the future, we must assume some individual beliefs about how the entire distribution will evolve over time. Let general beliefs about the future distribution of capital in period $t+u$ be characterized by the operator $\Omega(\cdot)$ such that:
  ```{math}
  :label: EqUNtut_Beliefs
    \Gamma^e_{t+u} = \Omega^u\left(\Gamma_t\right) \quad \forall t, \quad u\geq 1
  ```
  where the $e$ superscript signifies that $\Gamma^e_{t+u}$ is the expected distribution of wealth at time $t+u$ based on general beliefs $\Omega(\cdot)$ that are not constrained to be correct.[^beliefs]


(SecUNtutorial_3perOGfirms)=
## Firms

  The economy also includes a unit measure of identical, perfectly competitive firms that rent investment capital from individuals for real return $r_t$ and hire labor for real wage $w_t$. Firms use their total capital $K_t$ and labor $L_t$ to produce output $Y_t$ every period according to a Cobb-Douglas production technology.
  ```{math}
  :label: EqUNtut_FirmProdFunc
    Y_t = F(K_t,L_t) \equiv AK_t^\alpha L_t^{1-\alpha}\quad\text{where}\quad \alpha\in(0,1) \quad\text{and}\quad A>0
  ```
  We assume that the price of the output in every period $P_t=1$.[^PriceAssumpt] The representative firm chooses how much capital to rent and how much labor to hire to maximize profits,
  ```{math}
  :label: EqUNtut_FirmProfMax
    \max_{K_t,L_t}\: AK_t^\alpha L_t^{1-\alpha} - (r_t + \delta)K_t - w_t L_t
  ```
  where $\delta\in[0,1]$ is the rate of capital depreciation.[^depreciation] The two first order conditions that characterize firm optimization are the following.
  ```{math}
  :label: EqUNtut_FirmFOCK
    r_t = \alpha A\left(\frac{L_t}{K_t}\right)^{1-\alpha} - \delta \quad\forall t
  ```
  ```{math}
  :label: EqUNtut_FirmFOCL
    w_t = (1-\alpha)A\left(\frac{K_t}{L_t}\right)^\alpha
  ```


(SecUNtutorial_3perOGmc)=
## Market clearing

  Three markets must clear in this model: the labor market, the capital market, and the goods market. Each of these equations amounts to a statement of supply equals demand.
  ```{math}
  :label: EqUNtut_MCn
    L_t = \sum_{s=1}^3 n_{s,t} = 2.2 \quad\forall t
  ```
  ```{math}
  :label: EqUNtut_MCk
    K_t = \sum_{s=2}^3 b_{s,t} = b_{2,t} + b_{3,t} \quad\forall t
  ```
  ```{math}
  :label: EqUNtut_MCy
    &Y_t = C_t + I_t \quad\forall t \\
    &\qquad\text{where}\quad I_t \equiv K_{t+1} - (1-\delta)K_t
  ```
  The goods market clearing equation {eq}`EqUNtut_MCy` is redundant by Walras' Law.


(SecUNtutorial_3perOGeqlb)=
## Equilibrium

  Before providing exact definitions of the functional equilibrium concepts, we give a rough sketch of the equilibrium, so you can see what the functions look like and understand the exact equilibrium definition more clearly. A rough description of the equilibrium solution to the problem above is the following three points.
  - Households optimize according to Equations {eq}`EqUNtut_HHfock2b` and {eq}`EqUNtut_HHfock3b`.
  - Firms optimize according to Equations {eq}`EqUNtut_FirmFOCK` and {eq}`EqUNtut_FirmFOCL`.
  - Markets clear according to Equations {eq}`EqUNtut_MCn` and {eq}`EqUNtut_MCk`.
  These equations characterize the equilibrium and constitute a system of nonlinear difference equations.

  The easiest way to understand the equilibrium solution is to substitute the market clearing conditions {eq}`EqUNtut_MCn` and {eq}`EqUNtut_MCk` into the firm's optimal conditions {eq}`EqUNtut_FirmFOCK` and {eq}`EqUNtut_FirmFOCL` and solve for the equilibrium wage and interest rate as functions of the distribution of capital.
  ```{math}
  :label: EqUNtut_Eqlwt
    w_t\bigl(b_{2,t},b_{3,t}\bigr):\quad w_t = (1-\alpha)A\left(\frac{b_{2,t}+b_{3,t}}{2.2}\right)^\alpha
  ```
  ```{math}
  :label: EqUNtut_Eqlrt
    r_t\bigl(b_{2,t},b_{3,t}\bigr):\:\quad r_t = \alpha A\left(\frac{2.2}{b_{2,t}+b_{3,t}}\right)^{1-\alpha} - \delta
  ```
  Now Equations {eq}`EqUNtut_Eqlwt` and {eq}`EqUNtut_Eqlrt` can be substituted into household Euler equations {eq}`EqUNtut_HHfock2b` and {eq}`EqUNtut_HHfock3b` to get the following two-equation system that completely characterizes the equilibrium.
  ```{math}
  :label: EqUNtut_Eqlfock2
    &u'\Bigl(w_t(b_{2,t},b_{3,t}) - b_{2,t+1}\Bigr) = \beta\Bigl(1 + r_{t+1}(b_{2,t+1},b_{3,t+1})\Bigr) \times... \\
    &\quad u'\Bigl(w_{t+1}(b_{2,t+1},b_{3,t+1}) + [1 + r_{t+1}(b_{2,t+1},b_{3,t+1})]b_{2,t+1} - b_{3,t+2}\Bigr)
  ```
  ```{math}
  :label: EqUNtut_Eqlfock3
    &u'\Bigl(w_t(b_{2,t},b_{3,t}) + [1 + r_t(b_{2,t},b_{3,t})]b_{2,t} - b_{3,t+1}\Bigr) = ... \\
    &\quad \beta\Bigl(1 + r_{t+1}(b_{2,t+1},b_{3,t+1})\Bigr)u'\Bigl([1 + r_{t+1}(b_{2,t+1},b_{3,t+1})]b_{3,t+1} + 0.2w_{t+1}(b_{2,t+1},b_{3,t+1})\Bigr)
  ```

  The system of two dynamic equations {eq}`EqUNtut_Eqlfock2` and {eq}`EqUNtut_Eqlfock3` characterizing the decisions for $b_{2,t+1}$ and $b_{3,t+1}$ in every period $t$ is not identified. These households know the current distribution of capital $b_{2,t}$ and $b_{3,t}$. However, we need to solve for policy functions for $b_{2,t+1}$, $b_{3,t+1}$, and $b_{3,t+2}$ from these two equations. It looks like this system is unidentified. But the solution is a fixed point of stationary functions.

  We first define the steady-state equilibrium, which is exactly identified. Let the steady state of endogenous variable $x_t$ be characterized by $x_{t+1}=x_t=\bar{x}$ in which the endogenous variables are constant over time. Then we can define the steady-state equilibrium as follows.

  ```{prf:definition} Steady-state equilibrium
  :label: DefUNtut_3perSimpSSeql

  A non-autarkic steady-state equilibrium in the perfect foresight overlapping generations model with $3$-period lived agents is defined as constant allocations of consumption $\{\bar{c}_s\}_{s=1}^3$, capital $\{\bar{b}_s\}_{s=2}^3$, and prices $\bar{w}$ and $\bar{r}$ such that:
  1. households optimize according to Equations {eq}`EqUNtut_HHfock2b` and {eq}`EqUNtut_HHfock3b`,
  2. firms optimize according to Equations {eq}`EqUNtut_FirmFOCK` and {eq}`EqUNtut_FirmFOCL`,
  3. markets clear according to Equations {eq}`EqUNtut_MCn` and {eq}`EqUNtut_MCk`.
  ```

  As we saw earlier in this section, the characterizing equations in {prf:ref}`DefUNtut_3perSimpSSeql` reduce to {eq}`EqUNtut_Eqlfock2` and {eq}`EqUNtut_Eqlfock3` in every period. These two equations are exactly identified in the steady state. That is, they are two equations and two unknowns ($\bar{b}_2,\bar{b}_3$).
  ```{math}
  :label: EqUNtut_Eqlfock2SS
    u'\Bigl(w(\bar{b}_2,\bar{b}_3) - \bar{b}_2\Bigr) = \beta\Bigl(1 + r(\bar{b}_2,\bar{b}_3)\Bigr)u'\Bigl(w(\bar{b}_2,\bar{b}_3) + [1 + r(\bar{b}_2,\bar{b}_3)]\bar{b}_2 - \bar{b}_3\Bigr)
  ```
  ```{math}
  :label: EqUNtut_Eqlfock3SS
    &u'\Bigl(w(\bar{b}_2,\bar{b}_3) + [1 + r(\bar{b}_2,\bar{b}_3)]\bar{b}_2 - \bar{b}_3\Bigr) = ... \\
    &\quad\quad \beta\Bigl(1 + r(\bar{b}_2,\bar{b}_3)\Bigr)u'\Bigl([1 + r(\bar{b}_2,\bar{b}_3)]\bar{b}_3 + 0.2w(\bar{b}_2,\bar{b}_3)\Bigr)
  ```
  We can solve for steady-state $\bar{b}_2$ and $\bar{b}_3$ by using a unconstrained optimization solver. Then we solve for $\bar{w}$, $\bar{r}$, $\bar{c}_1$, $\bar{c}_2$, and $\bar{c}_3$ by substituting $\bar{b}_2$ and $\bar{b}_3$ into the equilibrium firm first order conditions and into the household budget constraints.

  Now we can get ready to define the non-steady-state equilibrium. To do this, we need to define two other important concepts.

  ```{prf:definition} State of a dynamical system
  :label: DefUNtut_StateSpace

  The state of a dynamical system---sometimes called the state vector---is the smallest set of variables that completely summarizes all the information necessary for determining the future of the system at a given point in time.
  ```

  In the 3-period-lived agent, perfect foresight, OG model described in this section, the state vector can be seen in equations {eq}`EqUNtut_Eqlfock2` and {eq}`EqUNtut_Eqlfock3`. What is the smallest set of variables that completely summarize all the information necessary for the three generations of all three generations living at time $t$ to make their consumption and saving decisions? What information do they have at time $t$ that will allow them to make their savings decisions? The state vector of this model in each period is the distribution of capital $(b_{2,t},b_{3,t})$.

  ```{prf:definition} Stationary function
  :label: DefUNtut_StatnFunc

  We define a stationary function to be a function that only depends upon its arguments and does not depend upon time.
  ```

  The relevant examples of stationary functions in this model are the policy functions for saving and investment. We defined the functions $\psi_{1,t}$ and $\psi_{2,t}$ generally in equations {eq}`EqUNtut_HHk2funcpe` and {eq}`EqUNtut_HHk3funcpeb`. But they were indexed by time as evidenced by the $t$ in $\psi_{1,t}$ and $\psi_{2,t}$. The stationary versions of those functions would be $\psi_{1}$ and $\psi_2$, which do not depend upon time. The arguments of the functions (the state) may change overtime causing the savings levels to change over time, but the function of the arguments is constant across time.

  With the concept of the state of a dynamical system and a stationary function, we are ready to define a functional non-steady-state equilibrium of the model.

  ```{prf:definition} Non-steady-state functional equilibrium
  :label: DefUNtut_3perSimpNSSEql

  A non-steady-state functional equilibrium in the perfect foresight overlapping generations model with $3$-period lived agents is defined as stationary allocation functions of the state $\psi_{1}\bigl(b_{2,t},b_{3,t}\bigr)$ and $\psi_{2}\bigl(b_{2,t},b_{3,t}\bigr)$ and stationary price functions $w(b_{2,t},b_{3,t})$ and $r(b_{2,t},b_{3,t})$ such that:

  1. households have symmetric beliefs $\Omega(\cdot)$ about the evolution of the distribution of savings as characterized in Equation {eq}`EqUNtut_Beliefs`, and those beliefs about the future distribution of savings equal the realized outcome (rational expectations): $\Gamma_{t+u} = \Gamma^e_{t+u} = \Omega^u\left(\Gamma_t\right) \quad\forall t,\quad u\geq 1$
  2. households optimize according to Equations {eq}`EqUNtut_HHfock2b` and {eq}`EqUNtut_HHfock3b`,
  3. firms optimize according to Equations {eq}`EqUNtut_FirmFOCK` and {eq}`EqUNtut_FirmFOCL`,
  4. markets clear according to {eq}`EqUNtut_MCn` and {eq}`EqUNtut_MCk`.
  ```

  We have already shown how to boil down the characterizing equations in {prf:ref}`DefUNtut_3perSimpNSSEql` to two equations {eq}`EqUNtut_Eqlfock2` and {eq}`EqUNtut_Eqlfock3`. But we have also seen that those two equations are not identified. So how do we solve for these equilibrium functions? The solution to the non-steady-state equilibrium in {prf:ref}`DefUNtut_3perSimpNSSEql` is a fixed point in function space. Choose two functions $\psi_1$ and $\psi_2$ and verify that they satisfy the Euler equations for all points in the state space (all possible values of the state).


(SecUNtutorial_3perOGtpi)=
## Solution method: time path iteration (TPI)

  The benchmark conventional solution method for the non-steady-state rational expectations equilibrium transition path in OG models was originally outlined in a series of papers between 1981 and 1985,[^AuerbackKotlikoff] in chapter 4 of the seminal book {cite}`AuerbachKotlikoff:1987` for the perfect foresight case, and in Appendix II of {cite}`NishiyamaSmetters:2007` and Section 3.1 of {cite}`EvansPhillips:2014` for the stochastic case. We call this method time path iteration (TPI). The idea is that the economy is infinitely lived, even though the agents that make up the economy are not. Rather than recursively solving for equilibrium policy functions by iterating on individual value functions, one must recursively solve for the policy functions by iterating on the entire transition path of the endogenous objects in the economy (see Chapter 17 of {cite}`StokeyLucas1989`). {cite}`EvansPhillips:2014` give a good description of how to implement this method.

  The key assumption is that the economy will reach the steady-state equilibrium $(\bar{b}_2,\bar{b}_3)$ described in {prf:ref}`DefUNtut_3perSimpSSeql` in a finite number of periods $T<\infty$ regardless of the initial state $(b_{2,1},b_{3,1})$. The first step is to assume a transition path for aggregate capital $K^i = \left\{K_1^i,K_2^i,...K_T^i\right\}$ such that $T$ is sufficiently large to ensure that $(b_{2,T},b_{3,T}) = (\bar{b}_2,\bar{b}_3)$. The superscript $i$ is an index for the iteration number. The transition path for aggregate capital determines the transition path for both the real wage $w^i = \left\{w_1^i,w_2^i,...w_T^i\right\}$ and the real return on investment $r^i = \left\{r_1^i,r_2^i,...r_T^i\right\}$. The exact initial distribution of capital in the first period $(b_{2,1},b_{3,1})$ can be arbitrarily chosen as long as it satisfies $K_1^i = b_{2,1} + b_{3,1}$ according to market clearing condition {eq}`EqUNtut_MCk`. One could also first choose the initial distribution of capital $(b_{2,1},b_{3,1})$ and then choose an initial aggregate capital stock $K_1^i$ that corresponds to that distribution. As mentioned earlier, the only other restriction on the initial transition path for aggregate capital is that it equal the steady-state level $K_T^i = \bar{K} = \bar{b}_2 + \bar{b}_3$ by period $T$. But the aggregate capital stocks $K_t^j$ for periods $1<t<T$ can be any level.

  Given the initial capital distribution $(b_{2,1},b_{3,1})$ and the transition paths of aggregate capital $K^i = \left\{K_1^i,K_2^i,...K_T^i\right\}$, the real wage $w^i = \left\{w_1^i,w_2^i,...w_T^i\right\}$, and the real return to investment $r^i = \left\{r_1^i,r_2^i,...r_T^i\right\}$, one can solve for the optimal savings decision for the initial middle-aged $s=2$ individual for the last period of his life $b_{3,2}$ using his intertemporal Euler equation {eq}`EqUNtut_Eqlfock3`.
  ```{math}
  :label: EqUNtut_Eqlfock3tpi1
    u'\Bigl(w_1^i + [1 + r_1^i]b_{2,1} - b_{3,2}\Bigr) = \beta\Bigl(1 + r_2^i\Bigr)u'\Bigl([1 + r_2^i]b_{3,2} + 0.2w_2^i\Bigr)
  ```
  Notice that everything in equation {eq}`EqUNtut_Eqlfock3tpi1` is known except for the savings decision $b_{3,2}$. This is one equation and one unknown.

  The next step is to solve for $b_{2,2}$ and $b_{3,3}$ for the initial young $s=1$ agent at period $1$ using the appropriately timed versions of Equations {eq}`EqUNtut_HHfock2b` and {eq}`EqUNtut_HHfock3` with the conjectured interest rates and real wages.
  ```{math}
  :label: EqUNtut_HHfock3tpi1
    u'\Bigl(w_1^i - b_{2,2}\Bigr) = \beta(1 + r_2^i)u'\Bigl(w_2^i + [1 + r_2^i]b_{2,2} - b_{3,3}\Bigr)
  ```
  ```{math}
  :label: EqUNtut_HHfock3tpi2
    u'\Bigl(w_2^i + [1 + r_2^i]b_{2,2} - b_{3,3}\Bigr) = \beta(1 + r_3^i)u'\Bigl([1 + r_3^i]b_{3,3} + 0.2w_3^i\Bigr)
  ```
  Everything is known in these two equations except for $b_{2,2}$ and $b_{3,3}$. So we can solve for those with a standard unconstrained solver. We next solve for $b_{2,t}$ and $b_{3,t+1}$ for the remaining $t\in\{3,4,...T+m\}$, where $T$ represents the period in the future at which the economy should have converged to the steady-state and $m$ represents some number of periods past that.[^timepastT]

  At this point, we have solved for the distribution of capital $(b_{2,t},b_{3,t})$ over the entire time period $t\in\{1,2,...T\}$. In each period $t$, the distribution of capital implies an aggregate capital stock $K_t^{i'} = b_{2,t} + b_{3,t}$. We put a ``$\, ' \,$'' on this aggregate capital stock because, in general, $K_t^{i'}\neq K_t^i$. That is, the conjectured path of the aggregate capital stock is not equal to the optimally chosen path of the aggregate capital stock given $K^i$.[^Tbigenough]

  Let $\left\lVert\cdot\right\rVert$ be a norm on the space of time paths for the aggregate capital stock. Common norms to use are the $L^2$ and the $L^\infty$ norms. Then the fixed point necessary for the equilibrium transition path from {prf:ref}`DefUNtut_3perSimpNSSEql` has been found when the distance between $K^{i'}$ and $K^{i}$ is arbitrarily close to zero.
  ```{math}
  :label: EqUNtut_EqlTPIdist
    \left\lVert K^{i'} - K^{i}\right\rVert < \varepsilon \quad\text{for}\quad \varepsilon>0
  ```
  If the fixed point has not been found $\left\lVert K^{i'} - K^{i}\right\rVert > \varepsilon$, then a new transition path for the aggregate capital stock is generated as a convex combination of $K^{i'}$ and $K^{i}$.
  ```{math}
  :label: EqUNtut_EqlTPInewpath
    K^{i+1} = \xi K^{i'} + (1-\xi) K^{i} \quad\text{for}\quad \xi\in(0,1)
  ```
  This process is repeated until the initial transition path for the aggregate capital stock is consistent with the transition path implied by those beliefs and household and firm optimization. TPI solves for the equilibrium transition path from {prf:ref}`DefUNtut_3perSimpNSSEql` by finding a fixed point in the time path of the economy.


(SecUNtutorial_3perOGcalib)=
## Calibration

  Use the following parameterization of the model for the problems below. Because agents live for only three periods, assume that each period of life is 20 years. If the annual discount factor is estimated to be 0.96, then the 20-year discount factor is $\beta = 0.96^{20} = 0.442$. Let the annual depreciation rate of capital be 0.05. Then the 20-year depreciation rate is $\delta = 1-(1-0.05)^{20} = 0.6415$. Let the coefficient of relative risk aversion be $\sigma = 3$, let the productivity scale parameter of firms be $A=1$, and let the capital share of income be $\alpha = 0.35$.


(SecUNtutorial_3perOGex)=
## Exercises

  ```{exercise-start} Checking feasibility of guesses for b_vec
  :label: ExerUNtut_3perOGfeas
  :class: green
  ```
  Using the calibration from Section {ref}`SecUNtutorial_3perOGcalib` of this chapter, write a Python function named `feasible()` that has the following form,

  ```{code} python
  b_cnstr, c_cnstr, K_cnstr = feasible(f_params, bvec_guess)
  ```
  where the inputs are a tuple `f_params = (nvec, A, alpha, delta)`, and a guess for the steady-state savings vector `bvec_guess = np.array([scalar, scalar])`. The outputs should be Boolean (`True` or `False`, `1` or `0`) vectors of lengths 2, 3, and 1, respectively. `K_cnstr` should be a singleton Boolean that equals `True` if $K\leq 0$ for the given `f_params` and `bvec_guess`. The object `c_cnstr` should be a length-3 Boolean vector in which the $s$th element equals `True` if $c_s\leq 0$ given `f_params` and `bvec_guess`. And `b_cnstr` is a length-2 Boolean vector that denotes which element of `bvec_guess` is likely responsible for any of the consumption nonnegativity constraint violations identified in `c_cnstr`. If the first element of `c_cnstr` is `True`, then the first element of `b_cnstr` is `True`. If the second element of `c_cnstr` is `True`, then both elements of `b_cnstr` are `True`. And if the last element of `c_cnstr` is `True`, then the last element of `b_cnstr` is `True`.

  1. Which, if any, of the constraints is violated if you choose an initial guess for steady-state savings of `bvec_guess = np.array([1.0, 1.2])`?
  2. Which, if any, of the constraints is violated if you choose an initial guess for steady-state savings of `bvec_guess = np.array([0.06, -0.001])`?
  3. Which, if any, of the constraints is violated if you choose an initial guess for steady-state savings of `bvec_guess = np.array([0.1, 0.1])`?
  ```{exercise-end}
  ```

  ```{exercise-start} Computing the steady-state equilibrium
  :label: ExerUNtut_3perOGSS
  :class: green
  ```
  Use the calibration from Section {ref}`SecUNtutorial_3perOGcalib` and the steady-state equilibrium {prf:ref}`DefUNtut_3perSimpSSeql`. Write a function named `get_SS()` that has the following form,

  ```{code} python
  ss_output = get_SS(params, bvec_guess, SS_graphs)
  ```
  where the inputs are a tuple of the parameters for the model `params = (beta, sigma, nvec, L, A, alpha, delta, SS_tol)`, an initial guess of the steady-state savings `bvec_guess`, and a Boolean `SS_graphs` that generates a figure of the steady-state distribution of consumption and savings if it is set to `True`. The output object `ss_output` is a Python dictionary with the steady-state solution values for the following endogenous objects.

  ```{code} python
  ss_output = {
      'b_ss': b_ss, 'c_ss': c_ss, 'w_ss': w_ss, 'r_ss': r_ss,
      'K_ss': K_ss, 'I_ss': I_ss, 'Y_ss': Y_ss, 'C_ss': C_ss,
      'EulErr_ss': EulErr_ss, 'RCerr_ss': RCerr_ss,
      'ss_time': ss_time
  }
  ```
  Let `ss_time` be the number of seconds it takes to run your steady-state program. You can time your program by importing the `time` library.

  ```{code} python
  import time
  ...
  start_time = time.time()  # Place at beginning of get_SS()
  ...
  ss_time = time.time() - start_time  # Place at end of get_SS()
  ```
  And let the object `EulErr_ss` be a length-2 vector of the two Euler errors from the resulting steady-state solution given in difference form $\beta(1+\bar{r})u'(\bar{c}_{s+1}) - u'(\bar{c}_s)$. The object `RCerr_ss` is a resource constraint error which should be close to zero. It is given by $\bar{Y}-\bar{C} - \delta\bar{K}$.
  1. Solve numerically for the steady-state equilibrium values of $\{\bar{c}_s\}_{s=1}^3$, $\{\bar{b}_s\}_{s=2}^3$, $\bar{w}$, $\bar{r}$, $\bar{K}$, $\bar{Y}$, $\bar{C}$, the two Euler errors and the resource constraint error. List those values. Time your function. How long did it take to compute the steady-state?
  2. Generate a figure that shows the steady-state distribution of consumption and savings by age $\{\bar{c}_s\}_{s=1}^3$ and $\{\bar{b}_s\}_{s=2}^3$.
  3. What happens to each of these steady-state values if all households become more patient $\beta\uparrow$ (an example would be $\beta = 0.55$)? That is, in what direction does $\beta\uparrow$ move each steady-state value $\{\bar{c}_s\}_{s=1}^3$, $\{\bar{b}_s\}_{s=2}^3$, $\bar{w}$, and $\bar{r}$? What is the intuition?
  ```{exercise-end}
  ```

  ```{exercise-start} Computing the transition path equilibrium
  :label: ExerUNtut_3perOGTPI
  :class: green
  ```
  Use the calibration from Section {ref}`SecUNtutorial_3perOGcalib` and the steady-state solution from part 1 of {numref}`ExerUNtut_3perOGSS`. Use time path iteration (TPI) to solve for the non-steady state equilibrium transition path of the economy from $(b_{2,1},b_{3,1})=(0.8\bar{b}_2,1.1\bar{b}_3)$ to the steady-state $(\bar{b}_2,\bar{b}_3)$. You'll have to choose a guess for $T$ and a time path updating parameter $\xi\in(0,1)$, but you can know that $T<50$. Use an $L^2$ norm for your distance measure (sum of squared percent deviations), and use a convergence parameter of $\varepsilon = 10^{-9}$. Use a linear initial guess for the time path of the aggregate capital stock from the initial state $K_1^1$ to the steady state $K_T^1$ at time $T$.

  1. Report the maximum of the absolute values of all the Euler errors across the entire time path. Also report the maximum of the absolute value of all the aggregate resource constraint errors $Y_t - C_t - K_{t+1} + (1 - \delta)K_t$ across the entire time path.
  2. Plot the equilibrium time paths of the aggregate capital stock $\{K_t\}_{t=1}^{T+5}$, wage $\{w_t\}_{t=1}^{T+5}$, and interest rate $\{r_t\}_{t=1}^{T+5}$.
  3. How many periods did it take for the economy to get within 0.00001 of the steady-state aggregate capital stock $\bar{K}$? What is the period after which the aggregate capital stock never is again farther than 0.00001 away from the steady-state?
  ```{exercise-end}
  ```


(SecUNtutorial_3perOGfootnotes)=
## Footnotes

  This section contains the footnotes for this chapter.

  [^OGtextbook]: The {cite}`DeBackerEvans:2024` textbook, *Overlapping Generations Models for Policy Analysis: Theory and Computation*, is currently unpublished. However, the authors have posted selected chapters in [this GitHub repository](https://github.com/OpenRG/OGprimer) along with the [table of contents](https://github.com/OpenRG/OGprimer/blob/master/Chapters/OGtext_toc.pdf) and the [references](https://github.com/OpenRG/OGprimer/blob/master/Chapters/OGtext_bib.pdf). The authors can make other selected chapters available upon request.
  [^2perSimp]: The main reason for this difference is that, in the two-period-lived agent OG model, young agents completely determine the supply of capital in the next period due to the fact that old people will not be around. This greatly simplifies the two-period-lived agent model and makes its solution method much easier than OG models with agents that live for three or more periods. However, two-period-lived OG models have been productively used in the literature to show many qualitatively interesting results.
  [^SimpProd]: This production sector is "nearly" the simplest because many simple 2-period-lived OG models assume a type of yeoman farmer that works and produces himself---a type of home production.
  [^3perGenToS]: Note that the 3-period-lived agent OG model generalizes to the $S$-period-lived agent model. The more periods an agent lives, the more period budget constraints there are that look like Equation {eq}`EqUNtut_HHbc2`.
  [^Cnonneg]: In equilibrium, consumption will be strictly positive $c_{s,t}>0$ for all $s$ and $t$ for two reasons. First, the utility function we use is not defined for $c\leq 0$. Second, the utility function we use has an Inada condition $\lim_{c\rightarrow 0}u'(c)=\infty$, which ensures that the solution to the household problem is always strictly positive consumption $c_{s,t}>0$ in equilibrium (interior solution). But because these conditions are equilibrium conditions, we state the general inequality constraint here $c_{s,t}\geq 0$.
  [^ReduceProb]: Notice that the individual's problem can be reduced from 5 choice variables to 2 choice variables because the choice in the first two periods between consumption and savings is really just one choice. And the choice of how much to consume in the last period is trivial, because an individual just consumes all their income in the last period.
  [^EnvelopeCond]: The presence of $r_{t+2}$ and $w_{t+2}$ in Equation {eq}`EqUNtut_HHk2funcpe` comes from the fact that optimal $b_{2,t+1}$ depends on the optimal $b_{3,t+2}$ from Equation {eq}`EqUNtut_HHk3funcpe`.
  [^beliefs]: In Section {ref}`SecUNtutorial_3perOGeqlb` we assume that beliefs are correct (rational expectations) for the non-steady-state equilibrium in {prf:ref}`DefUNtut_3perSimpNSSEql`.
  [^PriceAssumpt]: This is just a cheap way to assume no monetary policy. Relaxing this assumption is important in many applications for which price fluctuation is important.
  [^depreciation]: Note that it is equivalent whether we put depreciation on the firms' side as in equation {eq}`EqUNtut_FirmProfMax` or on the household side making the return on capital savings $1+r_t-\delta$. Depreciation must be in one place or the other, not both. We choose to put depreciation on the firm's side here because the tax model we are building up to includes taxes and subsidies to firms for depreciation expenses.
  [^AuerbackKotlikoff]: See {cite}`AuerbachEtAl:1981`, {cite}`AuerbachEtAl:1983`, {cite}`AuerbachKotlikoff:1983a`, {cite}`AuerbachKotlikoff:1983b`, {cite}`AuerbachKotlikoff:1983c`, and {cite}`AuerbachKotlikoff:1985`.
  [^timepastT]: For models in which agents live for $S$ periods, $m\geq S$ so that the full distribution of capital at time $T$ can be solved for. In the 3-period-lived agent model described here, $m\geq 3$.
  [^Tbigenough]: A check here for whether $T$ is large enough is if $K_T^{i'}=\bar{K}$ as well as $K_{T+1}^{i'}$ and $K_{T+2}^{i'}$. If not, then $T$ needs to be larger.
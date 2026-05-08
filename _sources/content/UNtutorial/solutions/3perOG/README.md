# Solutions to the exercises in the 3-period-lived OG model chapter in the UN Tutorial section
This folder contains the python scripts that compute the solutions to [Exercise 1](https://eapd-drb.github.io/OG-IDN/content/UNtutorial/3perOG.html#ExerUNtut_3perOGfeas), [Exercise 2](https://eapd-drb.github.io/OG-IDN/content/UNtutorial/3perOG.html#ExerUNtut_3perOGSS), and [Exercise 3](https://eapd-drb.github.io/OG-IDN/content/UNtutorial/3perOG.html#ExerUNtut_3perOGTPI) in the "[A 'Simple' 3-period-lived agent OG model](https://eapd-drb.github.io/OG-IDN/content/UNtutorial/3perOG.html)". In addition to this `README.md` file, this folder contains the following three Python scripts.
- [`execute.py`](https://github.com/EAPD-DRB/OG-IDN/blob/main/docs/book/content/UNtutorial/solutions/3perOG/execute.py). This script runs everything and delivers the solutions to the exercises. It calls the following two modules [`SS.py`](https://github.com/EAPD-DRB/OG-IDN/blob/main/docs/book/content/UNtutorial/solutions/3perOG/SS.py) and [`TPI.py`](https://github.com/EAPD-DRB/OG-IDN/blob/main/docs/book/content/UNtutorial/solutions/3perOG/TPI.py).
- [`SS.py`](https://github.com/EAPD-DRB/OG-IDN/blob/main/docs/book/content/UNtutorial/solutions/3perOG/SS.py). Python module that has the functions for solving the feasibility questions of [Exercise 1](https://eapd-drb.github.io/OG-IDN/content/UNtutorial/3perOG.html#ExerUNtut_3perOGfeas) and the steady-state equilibrium questions of [Exercise 2](https://eapd-drb.github.io/OG-IDN/content/UNtutorial/3perOG.html#ExerUNtut_3perOGSS).
- [`TPI.py`](https://github.com/EAPD-DRB/OG-IDN/blob/main/docs/book/content/UNtutorial/solutions/3perOG/TPI.py). Python module that has the functions for solving the transition path equilibrium questions of [Exercise 3](https://eapd-drb.github.io/OG-IDN/content/UNtutorial/3perOG.html#ExerUNtut_3perOGTPI).

You can run these computations that solve for the solutions to the three exercises by doing the following steps.
1. Open your terminal windown (Mac or Linux) or Anaconda prompt (Windows).
2. Activate your `ogidn-dev` conda environment: `conda activate ogidn-dev`
3. Navigate to your `OG-IDN` repository directory.
4. Navigate to the `/docs/book/content/UNtutorial/solutions/3perOG/` subfolder of this repository.
5. Run the `execute.py` script: `python execute.py`.

Running the `execute.py` script will print all the answers to the exercises in the output of the terminal. It will also create an `images` folder in this directory that has some of the images from the steady state and transition path equilibrium solutions.

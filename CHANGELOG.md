# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
* Made **informality the baseline tax calibration**, modeling it as graded income-tax *non-compliance* by lifetime-income group rather than a flat blended rate. Ethiopia's ~85% informal employment (ILO 2021) was previously approximated by a single low effective rate on everyone, which imposed a spurious work-and-saving wedge on the ~90% of households that in fact remit no income tax. Using OG-Core's by-`(t,j)` noncompliance dials, the bottom five of seven lifetime-income groups (90% of households by population weight) are set fully non-compliant, group 6 half, and the top group fully compliant. Five parameters change in `ogeth_default_parameters.json`: `etr_params` 0.03 → **0.1313** (the compliant-group effective rate, solved from a revenue identity to hit the PIT anchor), `mtrx_params` 0.20 → **0.35** (Ethiopia's statutory top PIT rate), `labor_income_tax_noncompliance_rate` and `capital_income_tax_noncompliance_rate` both `[0,…,0]` → **`[1,1,1,1,1,0.5,0]`**, and `adjustment_factor_for_cit_receipts` 0.2 → **0.327** (re-anchored to actual corporate-tax collections); `income_tax_filer` stays all 1.0 (non-compliance, not non-filing). Steady-state revenue now matches the data instrument by instrument — PIT 1.39% of GDP (target 1.4), CIT 1.71% (1.7), direct taxes 3.10% (3.1); sources IMF SIP 2025/108 ¶9 and CR 26/20 Table 2b — with the correct incidence (average income-tax rate by group `[0,0,0,0,0,0.066,0.131]`). Removing the flat-rate wedge lifts steady-state output ~7% (a recalibration effect, not a welfare claim). Documented in `calibration/taxes.md`; refs #71. Lifetime income is a proxy for formality (high-income informality is not representable), and time-varying formalization *reforms* are a separate exercise.
* Recalibrated the real and fiscal blocks to bring the steady state substantially closer to the actual Ethiopian economy. (1) **Capital share**: `gamma` 0.515 → 0.30, replacing the naive ILOSTAT labour share (0.385, biased down by Ethiopia's pervasive self-employment) with a Gollin-adjusted / sectorally-weighted labour share of 0.60; this cuts the model capital-output ratio from ~3.5 toward the Penn World Table's ~2.2 and the foreign-owned capital stock from ~1.3× to ~0.29× GDP (against a ~0.24× FDI stock). (2) **Remittances turned on**: `alpha_RM` 0 → 0.056 (IMF CR 26/20 balance-of-payments net private transfers, ~5.6% of GDP), which flips the steady-state trade balance from a wrong-signed +5.7% surplus to a −6.8% deficit, matching Ethiopia's actual −6.9% goods-trade deficit. (3) **Foreign aid turned on**: `alpha_FA` 0 → 0.01 (a modest long-run grant level; World Bank DPO on-budget grants were ~1.7% of GDP in FY2024/25, declining per the IMF program — held constant here because OG-Core does not extend `alpha_FA` to a time path), routing grants to the government so it can fund its spending — Ethiopia's low domestic revenue (~9% of GDP) cannot otherwise support positive government consumption on a debt-stable path. (4) **Payroll tax**: `tau_payroll` 0.18 → 0.03, the coverage-weighted *effective* pension-contribution rate (the 18% statutory rate covers only the small formal sector), correcting tax/GDP from an implausible 13% to ~9.2% (matching general-government revenue excluding grants). (5) `alpha_I` set to Ethiopia's actual on-budget public investment (~0.05, from the aspirational 0.065 recovery path). (6) `initial_Kg_ratio` 0.50 → **0.67**, Ethiopia's measured public-capital stock (IMF ICSD, 2019), so the model starts from the real state/SOE-built infrastructure and lets it depreciate toward the sustainable steady state (~0.28) over the transition — the honest counterfactual for an over-built stock that current revenue cannot maintain. This lifts baseline GDP ~10% in the start year (fading over a generation) versus starting near the steady state; the steady state itself is unchanged (initial_Kg_ratio is an initial condition only). `initial_guess_r_SS` retuned to 0.052. Fiscal aggregates are the IMF/World Bank general-government figures (federal + regional consolidated); the federal-to-regional block grant is excluded from `alpha_T`.
* Refreshed the single-industry baseline calibration to Ethiopian FY2024/25 (model start 2025), the first full-year vintage after the July 2024 exchange-rate float. Macro and open-economy block: `initial_debt_ratio` 0.327 → 0.50 and `initial_foreign_debt_ratio` 0.42 → 0.63 (the float revalued external debt; IMF fourth-ECF-review DSA / MoF Debt Bulletin No. 56, end-June 2025), `debt_ratio_ss` 0.40 → 0.30 (IMF fifth-review medium-term path to ~28.6% by FY2030/31), `zeta_D` 0.12 → 0.15, `zeta_K` 0.20 → 0.16 (Ethiopia's normalized Chinn-Ito index, 0.162, cross-checked against FDI/GFCF), `alpha_G` 0.055 → 0.058 (WDI `NE.CON.GOVT.ZS`, 2025), `alpha_T` 0.05 → 0.04, `alpha_I` path raised to 0.05 → 0.065 and `initial_Kg_ratio` 0.40 → 0.50 (IMF public-investment path), `tau_c` 0.07 → 0.06 (effective consumption-tax rate, FY2024/25 indirect taxes over private consumption). `world_int_rate_annual` stays 0.04 (Ethiopia is a distressed, near-closed sovereign; its integration is captured through low `zeta_K` and the debt-elastic rate).
* Moved the `g_y_annual` growth window from 2006-2024 to **2016-2025** (`G_Y_START_YEAR`/`G_Y_END_YEAR`), refreshing `g_y_annual` 0.0595 → 0.0470. The longer window embedded the unrepeatable 2004-2015 investment boom; the post-2015 decade is a more defensible balanced-growth-path rate. `gamma` refreshed 0.5169 → 0.51475 (latest ILOSTAT labour-share vintage, 2025).
* Turned on a **centered debt-elastic sovereign premium** (`r_gov_DY = -0.024`, `r_gov_DY2 = 0.04`), following OG-PHL/OG-IDN. The premium `r_gov_DY2·(D/Y − debt_ratio_ss)²` is re-centered on the steady-state debt ratio (0.30) so it is exactly zero at target — the steady state is unchanged — and only prices the transition-path debt overshoot. `r_gov_shift` is re-centered accordingly (-0.03377 → -0.03737).
* Froze the `r_gov_*` parameters in the live `update_from_api` path (they are no longer returned by `get_macro_params`): the committed `r_gov_shift` is the re-centered value, and returning the raw Li-Magud-Werner shift would silently un-center the premium and move the steady state. The Li-Magud-Werner derivation plus the re-centering arithmetic is preserved as the reproducible `macro_params.estimate_r_gov` helper.
* Retuned `initial_guess_r_SS` (0.0648 → 0.093) to the refreshed steady state.
* Raised the Python floor to `>=3.12` (matching CI and ogcore's own `>=3.12` requirement; classifiers and the ruff target follow) and relocked to a single `ogcore 0.16.3`, matching OG-ZAF and OG-IDN. This removes the stale Python 3.11 resolution branch that pinned an older ogcore.
* Regenerated the baseline demographics in `ogeth_default_parameters.json` under ogcore 0.16.3, which reworks the pre-time-path population distribution (PSLmodels/OG-Core#1073): the transition-path arrays (`omega`, `g_n`, `imm_rates`, `rho`) shift by one period and three period-0 seeds (`g_n_preTP`, `imm_rates_preTP`, `rho_preTP`) are added.
* Limited the `update_from_api` macro calibration to the sources that are authoritative for Ethiopia: `g_y_annual` (World Bank WDI) and `gamma` (UN ILOSTAT) still update, while the World Bank QPSD debt pull and the IMF `alpha_T`/`alpha_G` pull are switched off (QPSD has no Ethiopia data; the IMF series returns only 2002 values). Debt ratios, `alpha_G`, `alpha_T`, and `r_gov_*` stay at the documented values in `calibration/macro.md`. This refreshes `g_y_annual` (0.060 → 0.0595) and `gamma` (0.518 → 0.517).

### Fixed
* Fixed the demographic `country_id` in `calibrate.py`, which pulled South Africa (UN code 710) data instead of Ethiopia (231), and regenerated the baseline demographics in `ogeth_default_parameters.json`. Steady-state population growth corrects from 0.4% to 2.0%; macro parameters are unchanged.
* Brought all installation instructions in line with the uv workflow the project migrated to in 0.1.0, matching the same fix in OG-PHL and OG-ZAF. The README now documents two supported paths, each as per-platform copy-paste blocks verified end to end: the OG family's universal installer (`install.sh --repo og-eth`, from PSLmodels/OG-Core) and a manual install (install uv, clone, `uv run python examples/run_og_eth.py`). The PyPI install section is dropped: `pip install ogeth` fails outright on the Python that ships with macOS (3.9), silently installs an ogcore older than the tested one on Python 3.11, and does not pin the tested ogcore even on a supported Python. The contributor guide and the UN tutorial no longer instruct readers to build the deleted `ogeth-dev` conda environment (`environment.yml` was removed in 0.1.0, so those steps failed at the first command); both now use `uv sync --extra dev` and `uv run`, the contributor guide's test command matches CI (`pytest -m "not local"` instead of OG-USA's `needs_puf` suite), stale `master`-branch references now say `main`, and the 3-period-model solutions page points at OG-ETH instead of OG-IDN.

## [0.1.0] - 2026-05-20 12:00:00

### Changed
* Migrated the project from conda to uv. Install with `uv sync --extra dev`; `pyproject.toml` is the single source of truth for dependencies and `uv.lock` pins exact versions.
* CI uses `astral-sh/setup-uv`, and ruff replaces black for formatting and linting (`check_format.yml` -> `check_ruff.yml`).
* Updated README, AGENTS.md, and the Makefile to the uv workflow.

### Removed
* `setup.py`, `environment.yml`, and `pytest.ini` (their settings moved into `pyproject.toml`).

## [0.0.8] - 2026-05-18 23:00:00

### Added
* Reads the SAM file from `ogeth/data/` instead of fetching it from GitHub at runtime, so offline runs work
* Adds a `pip-import-smoke` CI job that installs the package and imports it from a temp directory, catching packaging issues invisible from the source tree

### Fixed
* Fixes `alpha_c` to sum only the ten household columns of the SAM (instead of total - row, which included government, investment, and intermediate use), matching OG-IDN and OG-PHL

## [0.0.7] - 2026-05-12 00:50:00

### Fixed

- Fixed bug in `calibrate.py` where the `income.get_e_interp` function was not being called with the correct parameters. This was causing an error when running the `calibrate.py` script.

## [0.0.6] - 2026-04-15 15:50:00

### Added

- Updates connections to API calls to the World Bank, IMF, and UN in `macro_params.py` and `calibrate.py` to allow for updating the exogenous parameters from the APIs. This is currently set to `False` by default, but can be set to `True` to update the parameters from the APIs when running the `calibrate.py` script. The documentation in `exogenous_parameters.md` has also been updated to reflect this change.
- Updates how the SAM file is loaded in `input_output.py`
- Adds an `update_baseline.py` script that updates the default parameters in `ogeth_default_parameters.json` based on the output of the `calibrate.py` script. This allows us to easily update the default parameters in the JSON file when we run the calibration script.

## [0.0.5] - 2025-11-17 23:40:00

### Added

- Updates average household income `mean_income_data` to ETB 157,845 and the corresponding documentation in `matching_lwi.md`
- Updates initial debt-to-GDP and the corresponding documentation in `macro.md`

## [0.0.4] - 2025-11-17 18:30:00

### Added

- Updates the TPI resource constraint `RC_TPI=0.01`

## [0.0.3] - 2025-11-17 13:00:00

### Added

- Updates default parameters

## [0.0.2] - 2025-11-16 13:00:00

### Added

- Fixes black formatting in `income.py` and `input_output.py`
- Fixes a typo in `constants.py`
- Fixes an error in the `deploy_docs.yml` and `docs_check.yml` files
- Adds Jason as a core maintainer in `intro.md`. This also allows us to see if the documentation GH Actions work.
- Removed `test_income.py` and `test_input_output.py` tests

## [0.0.1] - 2025-11-16 12:30:00

### Added

- Adds 3 logo files to the `./docs/` directory: `OG-ETH_logo_gitfig.png`, `OG-ETH_logo_long.png`, and `OG-ETH_logo.png`.
- Updates a `.gitignore` file.
- Fixes references in `./docs/book/content/OGETH_references.md`, `./docs/create_doc_figures.py`, `PSL_catalog.json,` and `./docs/README.md`
- Fixes badges in `README.md` and `intro.md`
- Pins the `environment.yml` package `jupyter-book<2.0.0` so that the book can build with `jb build ...` command.
- Updates the functions in `input_output.rst` and `utils.rst`
- Updates the Jupyter metadata in `earnings.md` and `exogenous_parameters.md`. This is what was stopping the Jupyter Book from compiling (once we pinned `jupyter-book<2.0.0`).
- Adds GH Action files `build_and_tes.yml`, `check_format.yml`, `deploy_docs.yml`, `docs_check.yml`, `publish_to_pypi.yml`, `ISSUE_TEMPLATE.md`, and `PULL_REQUEST_TEMPLATE.md`. These files required me to add OG-ETH to Codecov.io, add a repository secret for Codecov, create the gh-pages branch with the files for the Jupyter Book and publish it as a GitHub pages site, create and upload the first version of the `ogeth` package to PyPI.org, and add a repository secret for PYPI.

## [0.0.0] - 2025-10-06 12:00:00

### Added

- This version is a pre-release alpha. The example run script OG-ETH/examples/run_og_eth.py runs, but the model is not currently calibrated to represent the Ethiopian economy and population.


[0.1.0]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.8...v0.1.0
[0.0.8]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/EAPD-DRB/OG-ETH/compare/v0.0.0...v0.0.1

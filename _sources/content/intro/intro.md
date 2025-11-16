(Chap_Intro)=
# OG-ETH

| | |
| --- | --- |
| Org | [![United Nations DESA](https://img.shields.io/badge/United%20Nations%20DESA-blue)](https://www.un.org/en/desa) [![PSL cataloged](https://img.shields.io/badge/PSL-cataloged-a0a0a0.svg)](https://www.PSLmodels.org) [![OS License: CC0-1.0](https://img.shields.io/badge/OS%20License-CC0%201.0-yellow)](https://github.com/EAPD-DRB/OG-ETH/blob/main/LICENSE) [![Jupyter Book Badge](https://raw.githubusercontent.com/jupyter-book/jupyter-book/next/docs/media/images/badge.svg)](https://eapd-drb.github.io/OG-ETH) |
| Package | [![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3129/) [![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3137/) [![PyPI Latest Release](https://img.shields.io/pypi/v/ogeth.svg)](https://pypi.org/project/ogeth/) [![PyPI Downloads](https://img.shields.io/pypi/dm/ogeth.svg?label=PyPI%20downloads)](https://pypi.org/project/ogeth/) |
| Testing | ![example event parameter](https://github.com/EAPD-DRB/OG-ETH/actions/workflows/build_and_test.yml/badge.svg?branch=main) ![example event parameter](https://github.com/EAPD-DRB/OG-ETH/actions/workflows/deploy_docs.yml/badge.svg?branch=main) ![example event parameter](https://github.com/EAPD-DRB/OG-ETH/actions/workflows/check_format.yml/badge.svg?branch=main) [![Codecov](https://codecov.io/gh/EAPD-DRB/OG-ETH/branch/main/graph/badge.svg)](https://codecov.io/gh/EAPD-DRB/OG-ETH) |

[`OG-ETH`](https://github.com/EAPD-DRB/OG-ETH) is a package that provides code and data to calibrate an overlapping-generations (OG) model to the economy of Ethiopia (ETH), the code of which is hosted on GitHub at https://github.com/EAPD-DRB/OG-ETH. `OG-ETH` uses as a dependency the [`OG-Core`](https://pslmodels.github.io/OG-Core/) package, which contains the core theory and logic of a general OG model. The `OG-ETH` calibration package and the `OG-Core` theory and logic make the model that allows for dynamic general equilibrium analysis of federal fiscal policy in Ethiopia. The model output focuses on changes in macroeconomic aggregates (GDP, investment, consumption), wages, interest rates, and the stream of tax revenues over time. This documentation of the `OG-ETH` package contains the following major sections, which are regularly updated.

* Contributing to `OG-ETH`
* `OG-ETH` API
* Calibration
* References
* Citations of `OG-ETH`


(Sec_CoreMaintainers)=
## Core Maintainers

Marcelo LaFleur (GitHub handle [@SeaCelo](https://github.com/SeaCelo)), [Richard W. Evans](https://sites.google.com/site/rickecon/) (GitHub handle [@rickecon](https://github.com/rickecon)), and [Jason DeBacker](https://jasondebacker.com/)(GitHub handle [@jdebacker](https://github.com/jdebacker)) are the core maintainers of `OG-ETH`. If you have questions about or contributions to the model or repository, please submit a GitHub "Issue" described in the {ref}`Sec_GitHubIssue` subsection or "Pull Request" as described in the {ref}`Sec_GitHubPR` subsection of the {ref}`Sec_Workflow` section of the `OG-ETH` {ref}`Chap_ContribGuide`.


(Sec_Disclaimer)=
## Disclaimer

The model is continuously under development. Users will be notified through [closed PR threads](https://github.com/EAPD-DRB/OG-ETH/pulls?q=is%3Apr+is%3Aclosed) and through the [release notes](https://github.com/EAPD-DRB/OG-ETH/releases) what changes have been implemented. The package will have released versions, which will be checked against existing code prior to release. Stay tuned for an upcoming release!


(Sec_CitingOGETH)=
## Citing OG-ETH

`OG-ETH` (Version #.#.#)[Source code], https://github.com/EAPD-DRB/OG-ETH

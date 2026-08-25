"""
Tests of macro_params.py module
"""

import sys
import types

import requests
import pytest

from ogeth import macro_params


class MockResponse:
    """
    Minimal mock response for requests.get().
    """

    def __init__(self, *, json_data=None, text="", status_code=200):
        self._json_data = json_data
        self.text = text
        self.status_code = status_code

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code} returned from mocked request"
            )


def _wb_payload(observations):
    return [
        {
            "page": 1,
            "pages": 1,
            "per_page": "10000",
            "total": len(observations),
        },
        [
            {
                "date": date,
                "value": value,
                "indicator": {"id": "mock-indicator"},
            }
            for date, value in observations
        ],
    ]


def _imf_payload(indicator_year_values):
    years = sorted(
        {
            int(year)
            for observations in indicator_year_values.values()
            for year in observations.keys()
        }
    )
    indicators = list(indicator_year_values.keys())
    return {
        "meta": {},
        "data": {
            "dataSets": [
                {
                    "structure": 0,
                    "action": "Replace",
                    "series": {
                        f"0:0:0:{indicator_idx}:0:0": {
                            "attributes": [0, None, None],
                            "observations": {
                                str(years.index(int(year))): [str(value)]
                                for year, value in observations.items()
                            },
                        }
                        for indicator_idx, observations in enumerate(
                            indicator_year_values.values()
                        )
                    },
                }
            ],
            "structures": [
                {
                    "dimensions": {
                        "series": [
                            {"id": "COUNTRY", "values": [{"id": "ETH"}]},
                            {"id": "SECTOR", "values": [{"id": "S1311"}]},
                            {"id": "GFS_GRP", "values": [{"id": "G2M"}]},
                            {
                                "id": "INDICATOR",
                                "values": [
                                    {"id": indicator}
                                    for indicator in indicators
                                ],
                            },
                            {
                                "id": "TYPE_OF_TRANSFORMATION",
                                "values": [{"id": "POGDP_PT"}],
                            },
                            {"id": "FREQUENCY", "values": [{"id": "A"}]},
                        ],
                        "observation": [
                            {
                                "id": "TIME_PERIOD",
                                "values": [
                                    {"value": str(year)} for year in years
                                ],
                            }
                        ],
                    },
                    "measures": {
                        "observation": [{"id": "OBS_VALUE", "roles": []}]
                    },
                    "attributes": {
                        "dimensionGroup": [],
                        "series": [],
                        "observation": [],
                    },
                    "annotations": [],
                }
            ],
        },
    }


def _mock_requests_get(monkeypatch, wb_payloads, ilo_text=None, imf_json=None):
    def fake_get(url, params=None, headers=None, timeout=None):
        if "worldbank.org" in url:
            indicator_code = url.rstrip("/").split("/")[-1]
            return MockResponse(json_data=wb_payloads[indicator_code])
        if "rplumber.ilo.org" in url:
            return MockResponse(
                text=ilo_text or "time,obs_value\n2024,40\n2023,39\n"
            )
        if "api.imf.org" in url:
            return MockResponse(
                json_data=imf_json
                or _imf_payload(
                    {
                        "G2_T": {2023: 31.8, 2024: 32.4},
                        "G24_T": {2023: 4.1, 2024: 4.7},
                        "G27_T": {2023: 3.9, 2024: 3.6},
                        "G271_T": {2023: 0.0, 2024: 0.0},
                    }
                )
            )
        raise AssertionError(f"Unexpected URL requested in test: {url}")

    monkeypatch.setattr(macro_params.requests, "get", fake_get)


def _mock_statsmodels(monkeypatch, params=None):
    fake_statsmodels = types.ModuleType("statsmodels")
    fake_api = types.ModuleType("statsmodels.api")

    def add_constant(values):
        return values

    class OLS:
        def __init__(self, endog, exog):
            self.endog = endog
            self.exog = exog

        def fit(self):
            result = types.SimpleNamespace()
            result.params = params or [1.0, 0.5]
            return result

    fake_api.add_constant = add_constant
    fake_api.OLS = OLS
    fake_statsmodels.api = fake_api
    monkeypatch.setitem(sys.modules, "statsmodels", fake_statsmodels)
    monkeypatch.setitem(sys.modules, "statsmodels.api", fake_api)


def test_fetch_wb_data_annual_success(monkeypatch):
    _mock_requests_get(
        monkeypatch,
        {
            "NY.GDP.PCAP.KD": _wb_payload(
                [("2022", 64.0), ("2024", 100.0), ("2023", 80.0)]
            )
        },
    )

    data = macro_params._fetch_wb_data(
        {"GDP per capita (constant 2015 US$)": "NY.GDP.PCAP.KD"},
        "ETH",
        2022,
        2024,
        source=2,
    )

    assert list(data.index) == ["2024", "2023", "2022"]
    assert list(data.columns) == ["GDP per capita (constant 2015 US$)"]
    assert data.loc["2024", "GDP per capita (constant 2015 US$)"] == 100.0


def test_fetch_wb_data_quarterly_success(monkeypatch):
    _mock_requests_get(
        monkeypatch,
        {
            "DP.DOD.DECT.CR.GG.Z1": _wb_payload(
                [("2024Q2", 48.0), ("2024Q4", 50.0), ("2024Q3", 49.0)]
            )
        },
    )

    data = macro_params._fetch_wb_data(
        {"Gross PSD Gen Gov - percentage of GDP": "DP.DOD.DECT.CR.GG.Z1"},
        "ETH",
        2024,
        2024,
        source=20,
    )

    assert list(data.index) == ["2024Q4", "2024Q3", "2024Q2"]
    assert list(data.columns) == ["Gross PSD Gen Gov - percentage of GDP"]
    assert data.loc["2024Q4", "Gross PSD Gen Gov - percentage of GDP"] == 50.0


def test_fetch_wb_data_empty_payload_raises_value_error(monkeypatch):
    _mock_requests_get(
        monkeypatch,
        {"NY.GDP.PCAP.KD": [{"page": 1, "pages": 1, "total": 0}, []]},
    )

    with pytest.raises(ValueError, match="Empty or malformed World Bank"):
        macro_params._fetch_wb_data(
            {"GDP per capita (constant 2015 US$)": "NY.GDP.PCAP.KD"},
            "ETH",
            2022,
            2024,
            source=2,
        )


def test_get_macro_params_update_from_api_false_returns_empty_dict():
    test_dict = macro_params.get_macro_params(update_from_api=False)

    assert isinstance(test_dict, dict)
    assert test_dict == {}


def test_get_macro_params_update_from_api_true(monkeypatch):
    _mock_statsmodels(monkeypatch)
    _mock_requests_get(
        monkeypatch,
        {
            "NY.GDP.PCAP.KD": _wb_payload(
                [("2022", 64.0), ("2024", 100.0), ("2023", 80.0)]
            ),
            "NY.GDP.MKTP.KD": _wb_payload(
                [("2022", 640.0), ("2024", 1000.0), ("2023", 800.0)]
            ),
            "NY.GDP.MKTP.CD": _wb_payload(
                [("2022", 700.0), ("2024", 1100.0), ("2023", 900.0)]
            ),
            "NE.CON.GOVT.CD": _wb_payload(
                [("2022", 200.0), ("2024", 250.0), ("2023", 225.0)]
            ),
            "DP.DOD.DECD.CR.PS.CD": _wb_payload(
                [("2024Q4", 60.0), ("2024Q3", 58.0), ("2024Q2", 57.0)]
            ),
            "DP.DOD.DECX.CR.PS.CD": _wb_payload(
                [("2024Q4", 40.0), ("2024Q3", 42.0), ("2024Q2", 43.0)]
            ),
            "DP.DOD.DECT.CR.GG.Z1": _wb_payload(
                [("2024Q4", 50.0), ("2024Q3", 49.0), ("2024Q2", 48.0)]
            ),
        },
        ilo_text="time,obs_value\n2025,40\n2024,39\n2023,38\n",
    )

    test_dict = macro_params.get_macro_params(update_from_api=True)

    assert isinstance(test_dict, dict)
    # Only g_y_annual (WB WDI) and gamma (ILOSTAT) are pulled for OG-ETH.
    # Debt (initial_debt_ratio, initial_foreign_debt_ratio, zeta_D),
    # IMF-sourced alpha_T/alpha_G, and the r_gov_* parameters are frozen at
    # the documented values in ogeth_default_parameters.json (see
    # macro_params.py / macro.md). r_gov is frozen because the committed
    # r_gov_shift is re-centered for the debt-elastic premium, and returning
    # the raw Li-Magud-Werner shift here would silently un-center it.
    assert sorted(test_dict.keys()) == sorted(
        [
            "g_y_annual",
            "gamma",
        ]
    )
    assert test_dict["g_y_annual"] == pytest.approx(0.25)
    assert test_dict["gamma"] == [pytest.approx(0.50)]


def test_get_imf_macro_params_overwrites_saved_file(monkeypatch, tmp_path):
    _mock_requests_get(
        monkeypatch,
        {},
        imf_json=_imf_payload(
            {
                "G2_T": {2023: 31.8, 2024: 32.4},
                "G24_T": {2023: 4.1, 2024: 4.7},
                "G27_T": {2023: 3.9, 2024: 3.6},
                "G271_T": {2023: 0.0, 2024: 0.0},
            }
        ),
    )

    data_file = tmp_path / "imf_gfs_soo_eth_s1311_g2m_pogdp_pt_a.csv"
    result = macro_params._get_imf_macro_params(
        "ETH", 2024, data_path=data_file
    )

    assert result["alpha_T"] == [pytest.approx(0.036)]
    assert result["alpha_G"] == [pytest.approx(0.241)]
    assert data_file.exists()

    _mock_requests_get(
        monkeypatch,
        {},
        imf_json=_imf_payload(
            {
                "G2_T": {2023: 31.8, 2024: 32.8},
                "G24_T": {2023: 4.1, 2024: 4.8},
                "G27_T": {2023: 3.9, 2024: 3.7},
                "G271_T": {2023: 0.0, 2024: 0.1},
            }
        ),
    )

    refreshed = macro_params._get_imf_macro_params(
        "ETH", 2024, data_path=data_file
    )

    assert refreshed != result
    saved_data = macro_params.pd.read_csv(data_file)
    saved_2024 = saved_data[saved_data["year"] == 2024].set_index("indicator")
    assert saved_2024.loc["G27_T", "value"] == pytest.approx(3.7)
    assert saved_2024.loc["G271_T", "value"] == pytest.approx(0.1)


def test_estimate_r_gov_reproduces_frozen_values():
    """
    estimate_r_gov reproduces the committed r_gov_* defaults and the
    debt-elastic premium is exactly zero at debt_ratio_ss (so the steady
    state is unchanged).
    """
    d = macro_params.estimate_r_gov(debt_ratio_ss=0.30, r_gov_DY2=0.04)

    assert d["r_gov_scale"][0] == pytest.approx(0.24484763593657788)
    assert d["r_gov_shift"][0] == pytest.approx(-0.03736625043803518)
    assert d["r_gov_DY"] == pytest.approx(-0.024)
    assert d["r_gov_DY2"] == pytest.approx(0.04)

    # Premium contribution net of the shift offset, evaluated at the target
    # debt ratio, must equal the base (un-centered) Li-Magud-Werner level of
    # +0.03376625 — i.e. the premium adds nothing at the steady state.
    dbar = 0.30
    net_constant = (
        -d["r_gov_shift"][0] + d["r_gov_DY"] * dbar + d["r_gov_DY2"] * dbar**2
    )
    assert net_constant == pytest.approx(0.03376625043803518)


def test_get_imf_macro_params_falls_back_to_last_available_year(monkeypatch):
    _mock_requests_get(
        monkeypatch,
        {},
        imf_json=_imf_payload(
            {
                "G2_T": {2023: 31.8},
                "G24_T": {2023: 4.1},
                "G27_T": {2023: 3.9},
                "G271_T": {2023: 0.0},
            }
        ),
    )

    result = macro_params._get_imf_macro_params("ETH", 2024)

    assert result["alpha_T"] == [pytest.approx(0.039)]
    assert result["alpha_G"] == [pytest.approx(0.238)]

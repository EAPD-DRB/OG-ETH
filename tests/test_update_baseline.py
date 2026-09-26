"""
Tests of update_baseline.py module
"""

import json
from pathlib import Path

import numpy as np
import pytest
from ogcore.parameters import Specifications

from ogeth import macro_params as mp
from ogeth import update_baseline


class MockCalibration:
    """
    Minimal calibration stub for update_baseline.main().
    """

    def __init__(self, p, update_from_api):
        self.p = p
        self.update_from_api = update_from_api
        self.demographic_params = {}
        self.e = None

    def get_dict(self):
        return {"frisch": 0.5, "g_y_annual": 0.03}

    def update_demographics(
        self, p, demographic_data_path=None, output_path=None
    ):
        omega = np.asarray(p.omega_SS)
        self.demographic_params = {
            "omega_SS": omega,
            "g_n": np.asarray(p.g_n),
            "g_n_ss": np.float64(p.g_n_ss),
        }
        self.e = np.ones(omega.shape) / omega.sum()


def test_demographics_only_writes_just_those_keys(monkeypatch, tmp_path):
    """
    The demographics-only route rewrites the regenerated keys and the fiscal
    program paths in place and leaves every other entry untouched.
    """
    output_dir = tmp_path / "baseline_output"
    output_dir.mkdir()
    src = (
        Path(update_baseline.__file__).parent / "ogeth_default_parameters.json"
    )
    before = json.loads(src.read_text(encoding="utf-8"))
    (output_dir / "ogeth_default_parameters.json").write_text(
        json.dumps(before), encoding="utf-8"
    )
    monkeypatch.setattr(update_baseline, "Calibration", MockCalibration)
    monkeypatch.setattr(
        update_baseline.os.path,
        "realpath",
        lambda _: str(output_dir / "update_baseline.py"),
    )

    update_baseline.main(demographics_only=True)

    after = json.loads(
        (output_dir / "ogeth_default_parameters.json").read_text("utf-8")
    )
    assert set(after) == set(before)
    assert np.allclose(after["e"], np.ones((80, 7)))
    assert after["gamma"] == before["gamma"]
    assert after["chi_n"] == before["chi_n"]
    # the tax functions are refitted from the statutory schedules, so they
    # agree to solver precision rather than bit for bit
    np.testing.assert_allclose(
        after["etr_params"], before["etr_params"], rtol=1e-6, atol=1e-12
    )
    assert "r_gov_shift" in after and "tG1" in after


def test_main_json_updates_specifications(monkeypatch, tmp_path):
    """
    JSON written by main() can be loaded into Specifications without error.
    """
    output_dir = tmp_path / "baseline_output"
    output_dir.mkdir()

    monkeypatch.setattr(update_baseline, "Calibration", MockCalibration)
    monkeypatch.setattr(
        update_baseline.os.path,
        "realpath",
        lambda _: str(output_dir / "update_baseline.py"),
    )

    update_baseline.main()

    json_path = Path(output_dir) / "ogeth_default_parameters.json"
    saved_params = json.loads(json_path.read_text(encoding="utf-8"))

    p = Specifications(baseline=True)
    p.update_specifications(saved_params)

    assert not p.errors
    assert p.frisch == saved_params["frisch"]
    assert p.g_y_annual == saved_params["g_y_annual"]

    # A baseline regeneration only overrides the calibrated macro params, so
    # the hand-set informality tax parameters must round-trip through main()
    # unchanged. Guards against an accidental regen wiping the calibration.
    assert p.tax_func_type == "GS"
    assert np.asarray(p.etr_params).shape[-1] == 3
    start = 1 - mp.COMPLIANCE_SCALE * (1 - np.array(mp.NONCOMPLIANCE_START))
    assert np.asarray(p.labor_income_tax_noncompliance_rate)[
        0
    ].tolist() == pytest.approx(start.tolist())
    assert np.asarray(p.capital_income_tax_noncompliance_rate)[
        0
    ].tolist() == pytest.approx(start.tolist())
    # the CIT collections factor is a path along the IMF program; its
    # FY2024/25 anchor must survive a regeneration
    assert float(
        np.asarray(p.adjustment_factor_for_cit_receipts)[0]
    ) == pytest.approx(0.327)
    assert np.asarray(p.income_tax_filer)[-1].tolist() == pytest.approx(
        [1.0] * 7
    )


def test_main_rebuilds_remittance_objects_from_regenerated_demographics(
    monkeypatch, tmp_path
):
    """
    g_RM and eta_RM are derived from the demographics, so a baseline
    regeneration must rewrite them from the demographics it saves.
    """
    from ogeth import macro_params as remittances

    output_dir = tmp_path / "baseline_output"
    output_dir.mkdir()
    monkeypatch.setattr(update_baseline, "Calibration", MockCalibration)
    monkeypatch.setattr(
        update_baseline.os.path,
        "realpath",
        lambda _: str(output_dir / "update_baseline.py"),
    )

    update_baseline.main()

    saved = json.loads(
        (output_dir / "ogeth_default_parameters.json").read_text(
            encoding="utf-8"
        )
    )
    p = Specifications(baseline=True)
    p.update_specifications(saved)
    expected = remittances.derive_remittance_params(
        p.g_y,
        np.asarray(saved["g_n"])[: p.T + p.S],
        saved["omega_SS"],
        saved["lambdas"],
    )
    assert np.allclose(saved["g_RM"], expected["g_RM"], atol=1e-12)
    assert np.allclose(saved["eta_RM"], expected["eta_RM"], atol=1e-12)

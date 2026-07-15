"""
Tests of update_baseline.py module
"""

import json
from pathlib import Path

import numpy as np
import pytest
from ogcore.parameters import Specifications

from ogeth import update_baseline


class MockCalibration:
    """
    Minimal calibration stub for update_baseline.main().
    """

    def __init__(self, p, update_from_api):
        self.p = p
        self.update_from_api = update_from_api

    def get_dict(self):
        return {"frisch": 0.5, "g_y_annual": 0.03}


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
    assert np.asarray(p.etr_params)[-1, 0].tolist() == pytest.approx([0.1313])
    assert np.asarray(p.mtrx_params)[-1, 0].tolist() == pytest.approx([0.35])
    assert np.asarray(p.labor_income_tax_noncompliance_rate)[
        -1
    ].tolist() == pytest.approx([1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.0])
    assert np.asarray(p.capital_income_tax_noncompliance_rate)[
        -1
    ].tolist() == pytest.approx([1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.0])
    assert float(
        np.asarray(p.adjustment_factor_for_cit_receipts)[-1]
    ) == pytest.approx(0.327)
    assert np.asarray(p.income_tax_filer)[-1].tolist() == pytest.approx(
        [1.0] * 7
    )

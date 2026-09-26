import os
import sys
import json
from importlib.resources import files
import numpy as np
from ogeth.calibrate import Calibration
from ogeth.income import write_json_parameters
from ogeth.macro_params import scenario_params
from ogcore.parameters import Specifications
from ogcore.utils import params_to_json


def _jsonable(value):
    """
    Turn a parameter value into something json.dump accepts.
    """
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def main(demographics_only=False):
    """
    Regenerate the packaged default parameters.

    Args:
        demographics_only (bool): rebuild only the demographics (with the
            income gradients), the earnings matrix and the parameters
            derived from them, writing them into the packaged JSON without
            touching anything else; the default also refreshes the macro
            parameters from the World Bank and IMF APIs and rewrites the
            whole file

    Returns:
        None

    """
    # Directories to save data
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    json_path = os.path.join(CUR_DIR, "ogeth_default_parameters.json")

    # Set up baseline parameterization
    p = Specifications(baseline=True)
    # Update parameters for baseline from default json file
    content = (
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .read_text(encoding="utf-8")
    )
    defaults = json.loads(content)
    p.update_specifications(defaults)
    if demographics_only:
        c = Calibration(p, update_from_api=False)
        c.update_demographics(p)
        d = dict(c.demographic_params)
        d["e"] = c.e
        p.update_specifications({k: _jsonable(v) for k, v in d.items()})
        # the baseline's fiscal paths and remittance path depend on the
        # regenerated g_n (through the implied real rate on debt and the
        # on-trend remittance growth), so they are rebuilt with it
        d.update(scenario_params(p))
        write_json_parameters(
            json_path, {k: _jsonable(v) for k, v in d.items()}
        )
        return
    c = Calibration(
        p,
        update_from_api=True,
    )
    d = c.get_dict()
    # update parameters
    p.update_specifications(d)
    # the baseline's fiscal paths and the remittance objects are derived
    # from the demographics just regenerated, so they are rebuilt here
    # rather than left stale
    p.update_specifications(scenario_params(p))
    # save to json file
    params_to_json(p, json_path)


if __name__ == "__main__":
    main(demographics_only="--demographics-only" in sys.argv)

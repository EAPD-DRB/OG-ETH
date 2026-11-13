# imports
import argparse
import multiprocessing
from distributed import Client
import os
import json
import time
import copy
from importlib.resources import files
import matplotlib.pyplot as plt
from ogeth import macro_params, warm_start
from ogcore.parameters import Specifications
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle
import dask

dask.config.set(scheduler="synchronous")

# Use a custom matplotlib style file for plots
plt.style.use("ogcore.OGcorePlots")


def main(scenario=macro_params.DEFAULT_SCENARIO):
    """
    Run the baseline and a corporate-tax-cut reform.

    Args:
        scenario (str): ``"history"`` runs the packaged history-anchored
            baseline; ``"program"`` overlays the IMF program paths
            (``macro_params.scenario_params``) and writes its results under
            ``OG-ETH-Example/program`` so the two can be compared
    """
    scenario = macro_params.check_scenario(scenario)
    # Define parameters to use for multiprocessing
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    print("Number of workers = ", num_workers)

    # Directories to save data
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(CUR_DIR, "OG-ETH-Example")
    if scenario != macro_params.DEFAULT_SCENARIO:
        save_dir = os.path.join(save_dir, scenario)
    base_dir = os.path.join(save_dir, "OUTPUT_BASELINE")
    reform_dir = os.path.join(save_dir, "OUTPUT_REFORM")

    """
    ---------------------------------------------------------------------------
    Run baseline policy
    ---------------------------------------------------------------------------
    """
    # Set up baseline parameterization
    p = Specifications(
        baseline=True,
        num_workers=num_workers,
        baseline_dir=base_dir,
        output_base=base_dir,
    )
    # Update parameters for baseline from default json file
    with (
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .open("r") as file
    ):
        defaults = json.load(file)
    p.update_specifications(defaults)
    # The packaged file is the history-anchored baseline; the program
    # scenario overlays the IMF program's fiscal, borrowing and remittance
    # paths and its long-run debt ratio (see macro.md).
    if scenario != macro_params.DEFAULT_SCENARIO:
        p.update_specifications(macro_params.scenario_params(p, scenario))
        print(f"Running the {scenario} scenario; results in {save_dir}")
    # Initial household wealth (initial_wealth_ratio), the floor on the
    # sovereign rate (r_gov_floor) and the solver settings (nu and Anderson
    # acceleration of the time path) are in the packaged parameters. The
    # steady state starts from a shipped solved state (ogeth/warm_start.py);
    # without the seed it cold-starts.
    if warm_start.enable():
        print("Warm start enabled (ogeth/data/ss_warm_start.pkl).")
    else:
        print("No warm-start seed found; cold-starting the steady state.")

    # Run model
    start_time = time.time()
    runner(p, time_path=True, client=client)
    print("run time = ", time.time() - start_time)

    """
    Run reform policy
    ---------------------------------------------------------------------------
    """

    # create new Specifications object for reform simulation
    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_dir

    # Parameter change for the reform run
    updated_params_ref = {
        "cit_rate": [[0.25]],  # decrease CIT rate to 25%
    }
    p2.update_specifications(updated_params_ref)

    # Run model
    start_time = time.time()
    runner(p2, time_path=True, client=client)
    print("run time = ", time.time() - start_time)
    client.close()

    """
    ---------------------------------------------------------------------------
    Save some results of simulations
    ---------------------------------------------------------------------------
    """
    base_tpi = safe_read_pickle(os.path.join(base_dir, "TPI", "TPI_vars.pkl"))
    base_params = safe_read_pickle(os.path.join(base_dir, "model_params.pkl"))
    reform_tpi = safe_read_pickle(
        os.path.join(reform_dir, "TPI", "TPI_vars.pkl")
    )
    reform_params = safe_read_pickle(
        os.path.join(reform_dir, "model_params.pkl")
    )
    ans = ot.macro_table(
        base_tpi,
        base_params,
        reform_tpi=reform_tpi,
        reform_params=reform_params,
        var_list=["Y", "C", "K", "L", "r", "w"],
        output_type="pct_diff",
        num_years=10,
        start_year=base_params.start_year,
    )

    # create plots of output
    op.plot_all(
        base_dir, reform_dir, os.path.join(save_dir, "OG-ETH_example_plots")
    )

    print("Percentage changes in aggregates:", ans)
    # save percentage change output to csv file
    ans.to_csv(os.path.join(save_dir, "OG-ETH_example_output.csv"))


if __name__ == "__main__":
    # execute only if run as a script
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument(
        "--scenario",
        choices=macro_params.SCENARIOS,
        default=macro_params.DEFAULT_SCENARIO,
        help="baseline scenario to run (default: %(default)s)",
    )
    main(parser.parse_args().scenario)

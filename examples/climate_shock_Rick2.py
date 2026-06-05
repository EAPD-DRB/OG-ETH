# imports
import numpy as np
import multiprocessing
from distributed import Client
import os
import json
import time
import copy
from importlib.resources import files
import matplotlib.pyplot as plt
from ogeth.calibrate import Calibration
from ogcore.parameters import Specifications
import ogcore.demographics as demog
# This module demogchg.py must be in the same directory as this run script
import demogchg
from ogcore import output_tables as ot
from ogcore import output_plots as op
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle
from ogeth.utils import is_connected
import dask
dask.config.set(scheduler = "synchronous")

# Use a custom matplotlib style file for plots
plt.style.use("ogcore.OGcorePlots")


def main():
    # Define parameters to use for multiprocessing
    num_workers = min(multiprocessing.cpu_count(), 7)
    client = Client(n_workers=num_workers, threads_per_worker=1)
    print("Number of workers = ", num_workers)

    # Directories to save data
    CUR_DIR = os.path.dirname(os.path.realpath(__file__))
    save_dir = os.path.join(CUR_DIR, "Climate2")
    base_dir = os.path.join(save_dir, "OUTPUT_BASELINE")
    #reform_dir = os.path.join(save_dir, "OUTPUT_REFORM")
    reform_mild_dir = os.path.join(save_dir, "OUTPUT_REFORM_MILD")
    # reform_moderate_dir = os.path.join(save_dir, "OUTPUT_REFORM_MODERATE")
    # reform_severe_dir = os.path.join(save_dir, "OUTPUT_REFORM_SEVERE")

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
    with (
        files("ogeth")
        .joinpath("ogeth_default_parameters.json")
        .open("r") as file
    ):
        defaults = json.load(file)
    p.update_specifications(defaults)
    # Update again with multi-industry
    with (
        files("ogeth")
        .joinpath("ogeth_multi_industry_parameters.json")
        .open("r") as file
    ):
        multi_defaults = json.load(file)
    p.update_specifications(multi_defaults)
    # Update parameters from calibrate.py Calibration class
    import ogeth.input_output as io
    import pandas as pd
    # Load SAM data from ogeth package
    sam_file = files("ogeth").joinpath("data").joinpath("IFPRI_SAM_ETH_2022_SAM.csv")
    with sam_file.open("r") as f:
        sam = pd.read_csv(
            f,
            index_col=1,
            thousands=",",
            nrows=109
        )

    sam = sam.fillna(0)
    pi_matrix_df =io.get_io_matrix(sam=sam)
    alpha_c_dict = io.get_alpha_c(sam=sam)

    p.io_matrix = pi_matrix_df.values
    p.alpha_c = pd.Series(alpha_c_dict).values

    #Run model
    start_time = time.time()
    runner(p, time_path=True, client=client)
    print("run time = ", time.time() - start_time)

    """
    ---------------------------------------------------------------------------
    Run reform policy
    ---------------------------------------------------------------------------
    """
    ##### Mild rainfall shock
    # create new Specifications object for reform simulation
    p2 = copy.deepcopy(p)
    p2.baseline = False
    p2.output_base = reform_mild_dir

    # Parameter change for the reform run
    # Prodcutin goods: primery, energy, teritery, secondarty energy,
    updated_params_ref = {
        "Z": [[0.95, 0.95, 1.0, 1.0]],  # decrease in productivity in different industries due to climate shocks
    }

    #"e": [[]]
    p2.update_specifications(updated_params_ref)

    # The reduced rainfall will increase mortality rates permanently by 1%
    # [need citation]
    mort_rates_per1, infmort_rates_per1 = demog.get_mort(
        country_id="231", start_year=p.start_year, end_year=p.start_year
    )
    new_mort_rates_per1 = mort_rates_per1 * 1.01
    new_mort_rates_per1[0,-1] = 1.0
    new_mort_rates_mat = new_mort_rates_per1.copy()
    new_infmort_rates_vec = infmort_rates_per1 * 1.01
    demog_vars_changed_allage = demogchg.get_changed_demog_params(
        p2, new_mort_rates_mat, new_infmort_rates_vec
    )
    p2.omega =demog_vars_changed_allage["omega"]
    p2.omega_SS = demog_vars_changed_allage["omega_SS"]
    p2.omega_S_preTP = demog_vars_changed_allage["omega_S_preTP"]
    p2.g_n = demog_vars_changed_allage["g_n"]
    p2.g_n_ss = demog_vars_changed_allage["g_n_ss"]
    p2.imm_rates = demog_vars_changed_allage["imm_rates"]
    p2.rho = demog_vars_changed_allage["rho"]

    # Run model
    start_time = time.time()
    runner(p2, time_path=True, client=client)
    print("run time = ", time.time() - start_time)
    client.close()

    # # For Moderate rainfall shock
    # # create new Specifications object for reform simulation
    # p3 = copy.deepcopy(p)
    # p3.baseline = False
    # p3.output_base = reform_moderate_dir

    # # Parameter change for the reform run
    # # Prodcutin goods: primery, energy, teritery, secondarty energy,
    # updated_params_ref = {
    #     "Z": [[0.90, 1.0, 1.0, 1.0]],  # decrease in productivity in different industries due to climate shocks
    # }

    # #"e": [[]]
    # p3.update_specifications(updated_params_ref)

    # # Run model
    # start_time = time.time()
    # runner(p3, time_path=True, client=client)
    # print("run time = ", time.time() - start_time)
    # #client.close()

    # # For Severe rainfall shock
    # # create new Specifications object for reform simulation
    # p4 = copy.deepcopy(p)
    # p4.baseline = False
    # p4.output_base = reform_severe_dir

    # # Parameter change for the reform run
    # # Prodcutin goods: primery, energy, teritery, secondarty energy,
    # updated_params_ref = {
    #     "Z": [[0.85, 1.0, 1.0, 1.0]],  # decrease in productivity in different industries due to climate shocks
    # }

    # #"e": [[]]
    # p4.update_specifications(updated_params_ref)

    # # Run model
    # start_time = time.time()
    # runner(p4, time_path=True, client=client)
    # print("run time = ", time.time() - start_time)
    # client.close()

    """
    ---------------------------------------------------------------------------
    Save some results of simulations
    ---------------------------------------------------------------------------
    """

    # Baseline
    base_tpi = safe_read_pickle(
        os.path.join(base_dir, "TPI", "TPI_vars.pkl")
    )
    base_params = safe_read_pickle(
        os.path.join(base_dir, "model_params.pkl")
    )

    # Mild shock
    mild_tpi = safe_read_pickle(
        os.path.join(reform_mild_dir, "TPI", "TPI_vars.pkl")
    )
    mild_params = safe_read_pickle(
        os.path.join(reform_mild_dir, "model_params.pkl")
    )

    # # Moderate shock
    # moderate_tpi = safe_read_pickle(
    #     os.path.join(reform_moderate_dir, "TPI", "TPI_vars.pkl")
    # )
    # moderate_params = safe_read_pickle(
    #     os.path.join(reform_moderate_dir, "model_params.pkl")
    # )

    # # Severe shock
    # severe_tpi = safe_read_pickle(
    #     os.path.join(reform_severe_dir, "TPI", "TPI_vars.pkl")
    # )
    # severe_params = safe_read_pickle(
    #     os.path.join(reform_severe_dir, "model_params.pkl")
    # )

    # Mild results
    ans_mild = ot.macro_table(
        base_tpi,
        base_params,
        reform_tpi=mild_tpi,
        reform_params=mild_params,
        var_list=["Y", "C", "K", "L", "r", "w"],
        output_type="pct_diff",
        num_years=10,
        start_year=base_params.start_year,
    )

    # # Moderate results
    # ans_moderate = ot.macro_table(
    #     base_tpi,
    #     base_params,
    #     reform_tpi=moderate_tpi,
    #     reform_params=moderate_params,
    #     var_list=["Y", "C", "K", "L", "r", "w"],
    #     output_type="pct_diff",
    #     num_years=10,
    #     start_year=base_params.start_year,
    # )

    # # Severe results
    # ans_severe = ot.macro_table(
    #     base_tpi,
    #     base_params,
    #     reform_tpi=severe_tpi,
    #     reform_params=severe_params,
    #     var_list=["Y", "C", "K", "L", "r", "w"],
    #     output_type="pct_diff",
    #     num_years=10,
    #     start_year=base_params.start_year,
    # )

    # create plots of output
    op.plot_all(
        base_dir, reform_mild_dir, os.path.join(save_dir, "mild_plots")
    )

    # Create debt-to-GDP plot for 2026-2045
    op.plot_gdp_ratio(
        base_tpi,
        base_params,
        reform_tpi=mild_tpi,
        reform_params=mild_params,
        var_list=["D"],
        plot_type="levels",
        num_years_to_plot=20,
        start_year=mild_params.start_year,
        vertical_line_years=None,
        plot_title="Debt-to-GDP ratio in baseline and reform: 2026-2045",
        path=os.path.join(save_dir, "mild_plots", "DebtGDPratio_20yr.png")
    )

    # Create aggregates plot for 2026-2045
    op.plot_aggregates(
        base_tpi,
        base_params,
        reform_tpi=mild_tpi,
        reform_params=mild_params,
        var_list=["Y", "C", "K", "L"],
        plot_type="pct_diff",
        stationarized=True,
        num_years_to_plot=20,
        start_year=mild_params.start_year,
        forecast_data=None,
        forecast_units=None,
        vertical_line_years=None,
        plot_title="Percentage change in macro aggregates: 2026-2045",
        path=os.path.join(
            save_dir, "mild_plots", "MacroAgg_PctChange_20yr.png"
        ),
    )

    print("\nMild Climate Shock Results")
    print(ans_mild)

    # print("\nModerate Climate Shock Results")
    # print(ans_moderate)

    # print("\nSevere Climate Shock Results")
    # print(ans_severe)

    ans_mild.to_csv(
        os.path.join(save_dir, "results_mild.csv")
    )

    # ans_moderate.to_csv(
    #     os.path.join(save_dir, "results_moderate.csv")
    # )

    # ans_severe.to_csv(
    #     os.path.join(save_dir, "results_severe.csv")
    # )


if __name__ == "__main__":
    main()

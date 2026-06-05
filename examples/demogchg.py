# imports
# %%
import numpy as np
import pickle
import multiprocessing
import pkgutil
from distributed import Client
import os
import json
import time
import argparse
from ogcore.parameters import Specifications
from ogcore.execute import runner
from ogcore.utils import safe_read_pickle, shift_bio_clock
from ogcore import demographics as demog

import dask
dask.config.set(scheduler="syncronous")


def get_changed_demog_params(p, new_mort_rates_mat, new_infmort_rates_vec):
    if np.ndim(new_mort_rates_mat) == 2:
        num_periods = new_mort_rates_mat.shape[0]
    elif np.ndim(new_mort_rates_mat) == 1:
        num_periods = 1
    if np.isscalar(new_infmort_rates_vec):
        new_infmort_rates_vec = np.ones(num_periods) * new_infmort_rates_vec
    # Get fert_rates baseline
    fert_rates_mat= demog.get_fert(
        start_year=p.start_year, end_year=p.start_year + num_periods - 1
    )
    pop_dist_baseline, pre_pop_baseline = demog.get_pop(
        start_year=p.start_year, end_year=p.start_year + num_periods - 1
    )
    imm_rates_mat = demog.get_imm_rates(
        fert_rates=fert_rates_mat,
        mort_rates=new_mort_rates_mat,
        infmort_rates=new_infmort_rates_vec,
        pop_dist=pop_dist_baseline,
        start_year=p.start_year,
        end_year=p.start_year + num_periods - 1,
    )

    # Extend each fof these over the full time path
    fert_rates_allmat = np.append(
        fert_rates_mat,
        np.tile(
            fert_rates_mat[-1, :].reshape((1, p.E + p.S)),
            (p.T + p.S - num_periods, 1),
        ),
        axis=0,
    )
    mort_rates_allmat = np.append(
        new_mort_rates_mat,
        np.tile(
            new_mort_rates_mat[-1, :].reshape((1, p.E + p.S)),
            (p.T + p.S - num_periods, 1)
        ),
        axis=0,
    )
    infmort_rates_allvec = np.append(
        new_infmort_rates_vec,
        np.ones(p.T + p.S - num_periods) * new_infmort_rates_vec[-1]
    )
    imm_rates_allmat = np.append(
        imm_rates_mat,
        np.tile(
            imm_rates_mat[-1, :].reshape((1, p.E + p.S)),
            (p.T + p.S - num_periods, 1),
        ),
        axis=0,
    )

    pop_baseline_TP, pre_pop_dist_baseline = demog.get_pop(
        infer_pop=True,
        fert_rates=fert_rates_allmat,
        mort_rates=mort_rates_allmat,
        infmort_rates=infmort_rates_allvec,
        imm_rates=imm_rates_allmat,
        initial_pop=None,
        pre_pop_dist=None,
        start_year=p.start_year,
        end_year=p.start_year + num_periods - 1,
    )

    demog_vars_changed_allage = demog.get_pop_objs(
        p.E,
        p.S,
        p.T,
        fert_rates=fert_rates_allmat[:num_periods+1, :],
        mort_rates=mort_rates_allmat[:num_periods+1, :],
        infmort_rates=infmort_rates_allvec[:num_periods+1],
        imm_rates=imm_rates_allmat[:num_periods+1, :],
        infer_pop=True,
        pop_dist=pop_baseline_TP[:2, :],
        pre_pop_dist=pre_pop_dist_baseline,
        initial_data_year=p.start_year,
        final_data_year=p.start_year + num_periods,
    )

    # in parameters, we need: omega (400 x 80), omega_SS (80), omega_S_preTP (80,), g_n (400,), g_n_ss, imm_rates (400, 80), rho (400, 80)

    return demog_vars_changed_allage

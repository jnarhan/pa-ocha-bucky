import pandas as pd
import numpy as np
from .util import date_to_t_int
import datetime

def read_npi_file(fname, start_date, end_t, adm2_map, disable_npi=False):

    # filter by overlap with simulation date range
    df = pd.read_csv(fname)
    df['date'] = pd.to_datetime(df.date) # force a parse in case it's an odd format
    end_date = start_date + datetime.timedelta(days=end_t)
    mask = (df['date'] >= str(start_date)) & (df['date'] <= str(end_date))
    df = df.loc[mask]

    npi_params = {}
    r0_reductions = []
    mobility_reductions = []
    contact_weights = []

    # 1st dimension is date, 2nd is admin2 code
    for name, group in df.sort_values(by=["date"]).groupby("date"):
        # convert adm2 id to int
        group.admin2 = group.admin2.astype(int)
        date_group = group.set_index('admin2').reindex(adm2_map)
        r0_reduction = np.array(date_group[["r0_reduction"]])
        mobility_reduction = np.array(date_group[["mobility_reduction"]])
        contact_weight = np.array(date_group[["home", "other_locations", "school", "work"]])
        r0_reductions.append(r0_reduction)
        mobility_reductions.append(mobility_reduction)
        contact_weights.append(contact_weight)

    npi_params["r0_reduct"] = np.array(r0_reductions)
    npi_params["mobility_reduct"] = np.array(mobility_reductions)
    npi_params["contact_weights"] = np.array(contact_weights)

    for key, value in npi_params.items():
        print(key, value.shape)
        
        #forward fill with last defined date
        tmp = np.repeat(value[-1][None,...], end_t+1-value.shape[0], axis=0)
        npi_params[key] = np.squeeze(np.concatenate((value,tmp),axis=0))

        #print(npi_params[key].shape)

    if disable_npi:
        npi_params["mobility_reduct"].fill(1.)
        npi_params["contact_weights"].fill(1.)
        npi_params["r0_reduct"] = 1./npi_params["r0_reduct"]
    else:
        # rescale the r0 scaling such that it's 1 on the first day because the doubling time is set
        # to match case history @ that date (i.e, it's not unmitigated, it's 'currently mitigated')
        # This doesn't need to happen for Cij or Aij
        npi_params['r0_reduct'] /= npi_params['r0_reduct'][0]

    # Fill any missing values with 1. (in case we don't have all the adm2 in the file)
    for k in npi_params:
        npi_params[k] = np.nan_to_num(npi_params[k], nan=1.)

    return npi_params
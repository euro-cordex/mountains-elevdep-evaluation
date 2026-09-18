import math
import os
import dask
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
import xesmf as xe
from cartopy import crs as ccrs
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
from dask.distributed import Client
from evaltools import obs
from evaltools.obs import eobs_mapping
from evaltools.utils import short_iid
from matplotlib.colors import BoundaryNorm
from tools import (
    check_equal_period,
    create_cordex_grid,
    e_obs_dic,
    fix_360_longitudes,
    height_temperature_correction,
    load_obs,
    mask_invalid,
    open_datasets,
    regional_means,
    regrid_dsets,
    seasonal_mean,
    standardize_unit,
    var_dic,
    variable_mapping,
)
import regionmask
import geopandas as gpd
dask.config.set(scheduler="single-threaded")

# client = Client(dashboard_address="localhost:8889", threads_per_worker=1)

# %% settings

overwrite = False
frequency = "day"
# domain = "EUR-11"
regridding = "bilinear"
year_start = "1991"
# year_end = "1992"
year_end = "2010"
parent = False
period = slice(year_start, year_end)
mip_era = "CMIP6"
driving_source_id = "ERA5"

save_results_path = "intermediate-csv-precsep/"

# # %% check if file already exists
# fn_out_bias = f"{save_results_path}/eobs_{variable}_{mip_era}_{period.start}-{period.stop}_spatial_bias.nc"
# fn_out_obs = f"{save_results_path}/raw-obs/eobs_{variable}_{period.start}-{period.stop}.nc"
# # fn_out_mod = f"{save_results_path}/raw-mod/{variable}_{mip_era}_{period.start}-{period.stop}.nc"
# if os.path.exists(fn_out_bias) and not overwrite:
#     print(f"File {fn_out_bias} already exists. Skipping processing.")
#     continue



# %% aux data
gpd_regions = gpd.read_file("data/roi-02-eea.gpkg")
regions = regionmask.Regions.from_geodataframe(gpd_regions)
rotated_grid = create_cordex_grid("EUR-11")  # No matter CMIP5 or CMIP6

xds_orog = xr.open_dataset("intermediate-nc/orog.nc")
df_orog = xds_orog.to_dataframe().reset_index()
df_orog2 = df_orog[["rlat", "rlon", "dset_id", "orog"]]
df_orog2["dset_id"] = df_orog2["dset_id"].str.replace("mon", "day")

df_orog_mean = pd.read_csv("intermediate-csv/orog/mean_orog_rcm.csv")

# %% helper functions
def make_df_regions_orog(xds, obs=False):
    df = xds.to_dataframe().reset_index()

    mask = regions.mask_3D(xds["lon"], xds["lat"], drop=False)
    df_mask = mask.to_dataframe().reset_index()
    df_mask_tosubset = df_mask[["region", "rlat", "rlon", "names", "mask"]][df_mask["mask"]]

    df_regions = pd.merge(df, df_mask_tosubset).dropna()

    df_regions["rlon_key"] = (df_regions["rlon"] * 1e4).round().astype(int)
    df_regions["rlat_key"] = (df_regions["rlat"] * 1e4).round().astype(int)

    if(obs):
        df_orog_mean["rlon_key"] = (df_orog_mean["rlon"] * 1e4).round().astype(int)
        df_orog_mean["rlat_key"] = (df_orog_mean["rlat"] * 1e4).round().astype(int)

        df_regions_orog = df_regions.merge(
            df_orog_mean,
            on=["rlon_key", "rlat_key"],
            how="left"
        )

        df_regions_orog = df_regions_orog.drop(columns=[
            "rlon_key", "rlat_key", "rlat_x", "rlon_x", "lat_x", "lon_x", "mask"
            ])
    else:
        df_orog2["rlon_key"] = (df_orog2["rlon"] * 1e4).round().astype(int)
        df_orog2["rlat_key"] = (df_orog2["rlat"] * 1e4).round().astype(int)

        df_regions_orog = df_regions.merge(
            df_orog2,
            on=["dset_id", "rlon_key", "rlat_key"],
            how="left"
        )

        df_regions_orog = df_regions_orog.drop(columns=[
            "rlon_key", "rlat_key", "rlat_x", "rlon_x", "mask"
            ])
    
    return df_regions_orog




# %% e-obs

fn_out = f"{save_results_path}/eobs_{period.start}-{period.stop}.csv"
if not os.path.exists(fn_out) or overwrite:

    eobs_var = [key for key, value in eobs_mapping.items() if value in ["tas", "pr"]]
    eobs = obs.eobs(variables=eobs_var, add_mask=False).sel(time=period)
    eobs = mask_invalid(eobs, vars=eobs_var, threshold=0.1)
    eobs = eobs.assign(
        pr_liquid=xr.where(eobs["tg"] >= 2, eobs["rr"], 0),
        pr_solid=xr.where(eobs["tg"] < 2, eobs["rr"], 0),
    )
    eobs_var_new = ["pr_liquid", "pr_solid"]
    regridder = xe.Regridder(eobs, rotated_grid, method=regridding, unmapped_to_nan=True)
    eobs_rot = regridder(eobs)

    ref_seasmean = seasonal_mean(eobs_rot[eobs_var_new].sel(time=period)).compute()
    df_regions_orog = make_df_regions_orog(ref_seasmean, obs=True)
    df_regions_orog.to_csv(fn_out, index=False)





# %% cmip6-era5 

fn_out = f"{save_results_path}/rcm_{period.start}-{period.stop}.csv"
if not os.path.exists(fn_out) or overwrite:

    dsets = open_datasets(
        ["tas", "pr"],
        frequency=frequency,
        driving_source_id=driving_source_id,
        mask=True,
        add_missing_bounds=False,
    )


    for dset in dsets.keys():
        dsets[dset] = dsets[dset].sel(time=period)

    for dset in dsets.keys():
        if not check_equal_period(dsets[dset], period):
            print(f"Temporal coverage of {dset} does not match with {period}")

    for dset in dsets.keys():
        dsets[dset] = standardize_unit(dsets[dset], "tas")
        dsets[dset] = standardize_unit(dsets[dset], "pr")

    dsets = regrid_dsets(dsets, rotated_grid, method=regridding)

    for dset in list(dsets):
        if("pr" in dsets[dset].variables and "tas" in dsets[dset].variables):
            dsets[dset] = dsets[dset].assign(
                pr_liquid=xr.where(dsets[dset]["tas"] >= 2 + 273.15, dsets[dset]["pr"], 0),
                pr_solid=xr.where(dsets[dset]["tas"] < 2 + 273.15, dsets[dset]["pr"], 0),
            )
        else:
            del dsets[dset]

    rcm_var_new = ["pr_liquid", "pr_solid"]

    rcm_seasmean = {
            dset_id: seasonal_mean(ds[rcm_var_new].sel(time=period)).compute()
            for dset_id, ds in dsets.items()
        }

    rcm_seasmean2 = xr.concat(
        list(rcm_seasmean.values()),
        dim=xr.DataArray(
            list(rcm_seasmean.keys()),
            dims="dset_id",
        ),
        compat="override",
        coords="minimal",
    )

    df_regions_orog = make_df_regions_orog(rcm_seasmean2, obs=False)
    df_regions_orog.to_csv(fn_out, index=False)




# %% cerra (does not work!! loads into memory everything)
# year_range = range(int(year_start), int(year_end) + 1)
# fn_out = f"{save_results_path}/cerra_{period.start}-{period.stop}.csv"
# if not os.path.exists(fn_out) or overwrite:

#     ds_pr = load_obs("pr", "cerra-land", frequency, add_fx=False, mask=False)
#     ds_pr = ds_pr.sel(time=period).compute()
#     ds_pr = fix_360_longitudes(ds_pr, lonname="longitude")

#     files_tasmax = [
#         "/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/day/tasmax/tasmax_raw_CERRA_"+
#         str(y) + "0101_" + str(y) + "1231.nc" for y in year_range
#     ]
#     ds_tasmax = xr.open_mfdataset(files_tasmax, concat_dim="time", combine="nested")
#     # ds_tasmax = ds_tasmax.sel(time=period).compute()
#     ds_tasmax = fix_360_longitudes(ds_tasmax)


#     files_tasmin = [
#         "/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/day/tasmin/tasmin_raw_CERRA_"+
#         str(y) + "0101_" + str(y) + "1231.nc" for y in year_range
#     ]
#     ds_tasmin = xr.open_mfdataset(files_tasmin, concat_dim="time", combine="nested")
#     # ds_tasmin = ds_tasmin.sel(time=period).compute()
#     ds_tasmin = fix_360_longitudes(ds_tasmin)

#     ds_pr2 = ds_pr.assign(
#         tas = (ds_tasmax["tasmax"] + ds_tasmin["tasmin"])/2
#     )
#     ds_pr2 = ds_pr2.assign(
#         pr_liquid=xr.where(ds_pr2["tas"] >= 2, ds_pr2["tp"], 0),
#         pr_solid=xr.where(ds_pr2["tas"] < 2, ds_pr2["tp"], 0),
#     )

#     regridder = xe.Regridder(ds_pr2, rotated_grid, method=regridding, unmapped_to_nan=True)
#     cerra_rot = regridder(ds_pr2)
#     cerra_var_new = ["pr_liquid", "pr_solid"]

#     ref_seasmean = seasonal_mean(cerra_rot[cerra_var_new].sel(time=period)).compute()
#     df_regions_orog = make_df_regions_orog(ref_seasmean, obs=True)
#     df_regions_orog.to_csv(fn_out, index=False)


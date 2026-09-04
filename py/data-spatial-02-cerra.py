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

overwrite = True
# variable = "tasmin"
frequency = "mon"
# domain = "EUR-11"
regridding = "bilinear"
year_start = "1991"
year_end = "2020"
parent = False
period = slice(year_start, year_end)
mip_era = "CMIP6"
driving_source_id = "ERA5"

save_results_path = "intermediate-nc/"

# %% run all

all_variables = ["pr", "tas", "tasmax", "tasmin"]

for variable in all_variables:



    # %% check if file already exists
    fn_out = f"{save_results_path}/cerra_{variable}_{mip_era}_{period.start}-{period.stop}_spatial_bias.nc"
    if os.path.exists(fn_out) and not overwrite:
        print(f"File {fn_out} already exists. Skipping processing.")
        continue


    # %% aux data
    gpd_regions = gpd.read_file("data/roi-02-eea.gpkg")
    regions = regionmask.Regions.from_geodataframe(gpd_regions)
    rotated_grid = create_cordex_grid("EUR-11")  # No matter CMIP5 or CMIP6



    # %% cerra preprocessing
    if variable == "pr":
        dset = "cerra-land" # for pr
    else:
        dset = "cerra" # for tas*
        
    ds = load_obs(variable, dset, add_fx=True, mask=True)
    ds = ds.sel(time=period).compute()
    ds = fix_360_longitudes(ds, lonname="longitude")
    if not variable_mapping[dset][variable] == variable:
        ds = ds.rename_vars({variable_mapping[dset][variable]: variable})
    ds = standardize_unit(ds, variable)

    regridder = xe.Regridder(ds, rotated_grid, method=regridding, unmapped_to_nan=True)
    cerra_rot = regridder(ds)
    if not check_equal_period(cerra_rot, period):
        print(f"Temporal coverage of dataset does not match with {period}")
    ref_seasmean = seasonal_mean(cerra_rot[variable].sel(time=period)).compute()
    # ref_seasmean.plot.hist()



    # %% cmip6-era5 preprocessing
    dsets = open_datasets(
        [variable],
        frequency=frequency,
        driving_source_id=driving_source_id,
        mask=True,
        add_missing_bounds=False,
    )


    # %% cmip6-era5  post-proc
    for dset in dsets.keys():
        dsets[dset] = dsets[dset].sel(time=period)

    for dset in dsets.keys():
        if not check_equal_period(dsets[dset], period):
            print(f"Temporal coverage of {dset} does not match with {period}")

    for dset in dsets.keys():
        dsets[dset] = standardize_unit(dsets[dset], variable)

    dsets = regrid_dsets(dsets, rotated_grid, method=regridding)



    # %% seasonal means

    if var_dic[variable]["diff"] == "abs":
        diffs = {
            dset_id: seasonal_mean(ds[[variable]].sel(time=period)).compute()
            - (ref_seasmean)
            for dset_id, ds in dsets.items()
            if variable in ds.variables
        }
    elif var_dic[variable]["diff"] == "rel":
        diffs = {
            dset_id: 100
            * (seasonal_mean(ds[[variable]].sel(time=period)).compute() - (ref_seasmean))
            / (ref_seasmean)
            for dset_id, ds in dsets.items()
            if variable in ds.variables
        }
    seasonal_bias = xr.concat(
        list(diffs.values()),
        dim=xr.DataArray(
            list(diffs.keys()),
            dims="dset_id",
        ),
        compat="override",
        coords="minimal",
    )




    # %% save files
    seasonal_bias.to_netcdf(fn_out)



    # %% save orog grids separately
    # dsets_orog = dict.fromkeys(dsets)
    # for dset in dsets.keys():
    #     if "orog" in dsets[dset].variables:
    #         dsets_orog[dset] = dsets[dset]["orog"]
    # dsets_orog = {k: v for k, v in dsets_orog.items() if v is not None}

    # xds_orog = xr.concat(
    #     list(dsets_orog.values()),
    #     dim=xr.DataArray(
    #         list(
    #             map(
    #                 lambda x: short_iid(x, ["source_id"], delimiter="-"),
    #                 dsets_orog.keys(),
    #             )
    #         ),
    #         dims="dset_id",
    #     ),
    #     compat="override",
    #     coords="minimal",
    # )

    # xds_orog.to_netcdf(
    #     f"{save_results_path}/orog.nc"
    # )

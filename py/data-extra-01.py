import os
import dask
import numpy as np
import pandas as pd
import xarray as xr
import xesmf as xe
# from dask.distributed import Client
from evaltools import obs
# from evaltools.obs import eobs_mapping
# from evaltools.utils import short_iid
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
# dask.config.set(scheduler="single-threaded")

# client = Client(dashboard_address="localhost:8889", threads_per_worker=1)

# %% settings

overwrite = False
variable = "pr"
frequency = "mon"
# domain = "EUR-11"
regridding = "bilinear"
year_start = "1991"
year_end = "2020"
parent = False
period = slice(year_start, year_end)
mip_era = "CMIP6"
driving_source_id = "ERA5"

save_path = "intermediate-csv-extra/"

rocio_dir = {
    "tasmax": "tmax",
    "tasmin": "tmin",
    "pr": "pcp",
}

iberia_files = {
    "tas": "Iberia01_v1.0_DD_010reg_aa3d_tas.nc",
    "tasmax": "Iberia01_v1.0_DD_010reg_aa3d_tasmax.nc",
    "tasmin": "Iberia01_v1.0_DD_010reg_aa3d_tasmin.nc",
    "pr": "Iberia01_v1.0_DD_010reg_aa3d_pr.nc"
}

carpatclim_files = {
    "tas": "CCLIM_t2m19912010.nc",
    "tasmax": "CCLIM_t2max19912010.nc",
    "tasmin": "CCLIM_t2min19912010.nc",
    "pr": "CCLIM_pre19912010.nc"
}
carpatclim_varnames = {
    "tas": "T2M",
    "tasmax": "T2MAX",
    "tasmin": "T2MIN",
    "pr": "PRE"
}

# %% aux data
gpd_regions = gpd.read_file("data/roi-02-eea.gpkg")
regions = regionmask.Regions.from_geodataframe(gpd_regions)
rotated_grid = create_cordex_grid("EUR-11")  # No matter CMIP5 or CMIP6

xds_orog = xr.open_dataset("intermediate-nc/orog.nc")
df_orog = xds_orog.to_dataframe().reset_index()
df_orog2 = df_orog[["rlat", "rlon", "dset_id", "orog"]]

# %% helper functions
def calc_seasonal_bias(ref_seasmean):
    if var_dic[variable]["diff"] == "abs":
        diffs = {
            dset_id: seasonal_mean(ds[[variable]].sel(time=period)).compute()
            - (ref_seasmean)
            for dset_id, ds in dsets_rcm.items()
            if variable in ds.variables
        }
    elif var_dic[variable]["diff"] == "rel":
        diffs = {
            dset_id: 100
            * (seasonal_mean(ds[[variable]].sel(time=period)).compute() - (ref_seasmean))
            / (ref_seasmean)
            for dset_id, ds in dsets_rcm.items()
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
    return seasonal_bias


def make_df_regions_orog(xds):
    df = xds.to_dataframe().reset_index()

    mask = regions.mask_3D(xds["lon"], xds["lat"], drop=False)
    df_mask = mask.to_dataframe().reset_index()
    df_mask_tosubset = df_mask[["region", "rlat", "rlon", "names", "mask"]][df_mask["mask"]]

    df_regions = pd.merge(df, df_mask_tosubset).dropna()

    df_regions["rlon_key"] = (df_regions["rlon"] * 1e4).round().astype(int)
    df_regions["rlat_key"] = (df_regions["rlat"] * 1e4).round().astype(int)

    df_orog2["rlon_key"] = (df_orog2["rlon"] * 1e4).round().astype(int)
    df_orog2["rlat_key"] = (df_orog2["rlat"] * 1e4).round().astype(int)

    df_regions_orog = df_regions.merge(
        df_orog2,
        on=["dset_id", "rlon_key", "rlat_key"],
        how="left"
    )

    df_regions_orog = df_regions_orog.drop(columns=[
        "rlon_key", "rlat_key", "rlat_x", "rlon_x",
        "crs", "mask", "areacella"])
    
    return df_regions_orog


# %% run all

all_variables = ["pr", "tas", "tasmax", "tasmin"]



for variable in all_variables:




    # %% cmip6-era5 
    dsets = open_datasets(
        [variable],
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
        dsets[dset] = standardize_unit(dsets[dset], variable)

    dsets_rcm = regrid_dsets(dsets, rotated_grid, method=regridding)


    # %% rocio-ibeb
    # no tas
    if variable in ["pr", "tasmax", "tasmin"]:

        fn_out = f"{save_path}/rocio-ibeb_{variable}_{period.start}-{period.stop}.csv"
        if not os.path.exists(fn_out) or overwrite:

            variable_rocio = rocio_dir[variable]
            dset_rocio = load_obs(variable_rocio, "rocio-ibeb", "day", add_fx=False, mask=False)
            dset_rocio = dset_rocio.sel(time=period).compute()
            if not variable_mapping["rocio-ibeb"][variable] == variable:
                dset_rocio = dset_rocio.rename_vars({variable_mapping["rocio-ibeb"][variable]: variable})
            dset_rocio = standardize_unit(dset_rocio, variable)

            regridder = xe.Regridder(dset_rocio, rotated_grid, method=regridding, unmapped_to_nan=True)
            rocio_rot = regridder(dset_rocio)
            if not check_equal_period(rocio_rot, period):
                print(f"Temporal coverage of dataset does not match with {period}")
            ref_seasmean_rocio = seasonal_mean(rocio_rot[variable].sel(time=period)).compute()

            seasonal_bias = calc_seasonal_bias(ref_seasmean_rocio)

            df_regions_orog = make_df_regions_orog(seasonal_bias)

            df_regions_orog.to_csv(fn_out)



    # %% apgd

    if variable in ["pr"]:

        fn_out = f"{save_path}/apgd_{variable}_{period.start}-{period.stop}.csv"
        if not os.path.exists(fn_out) or overwrite:

            fn_apgd = "/mnt/CORDEX_CMIP6_tmp/aux_data/apgd/APGDv2_laea_vertices.nc"
            ds = xr.open_dataset(fn_apgd)

            dset_apgd = ds.sel(time=period).compute()
            dset_apgd = dset_apgd.rename_vars({"RapdD": "pr"})
            dset_apgd = standardize_unit(dset_apgd, "pr")

            regridder = xe.Regridder(dset_apgd, rotated_grid, method=regridding, unmapped_to_nan=True)
            apgd_rot = regridder(dset_apgd)
            if not check_equal_period(apgd_rot, period):
                print(f"Temporal coverage of dataset does not match with {period}")
            ref_seasmean = seasonal_mean(apgd_rot["pr"].sel(time=period)).compute()
            # ref_seasmean_apgd.isel(season=0).plot()
            
            seasonal_bias = calc_seasonal_bias(ref_seasmean)

            df_regions_orog = make_df_regions_orog(seasonal_bias)

            df_regions_orog.to_csv(fn_out)



    # %% iberia01

    fn_out = f"{save_path}/iberia01_{variable}_{period.start}-{period.stop}.csv"
    if not os.path.exists(fn_out) or overwrite:
        fn = f"/mnt/CORDEX_CMIP6_tmp/aux_data/iberia01/{iberia_files[variable]}"
        ds = xr.open_dataset(fn)

        dset_obs = ds.sel(time=period).compute()
        # dset_obs = dset_obs.rename_vars({variable_mapping["iberia01"][variable]: variable})
        dset_obs = standardize_unit(dset_obs, variable)

        regridder = xe.Regridder(dset_obs, rotated_grid, method=regridding, unmapped_to_nan=True)
        dset_rot = regridder(dset_obs)
        if not check_equal_period(dset_rot, period):
            print(f"Temporal coverage of dataset does not match with {period}")
        ref_seasmean = seasonal_mean(dset_rot[variable].sel(time=period)).compute()
        # ref_seasmean_apgd.isel(season=0).plot()

        seasonal_bias = calc_seasonal_bias(ref_seasmean)

        df_regions_orog = make_df_regions_orog(seasonal_bias)

        df_regions_orog.to_csv(fn_out)


    # %% carpatclim
    fn_out = f"{save_path}/carpatclim_{variable}_{period.start}-{period.stop}.csv"
    if not os.path.exists(fn_out) or overwrite:
        fn = f"/mnt/CORDEX_CMIP6_tmp/aux_data/carpatclim/{carpatclim_files[variable]}"
        ds = xr.open_dataset(fn)

        if variable in ["pr", "tas"]:
            ds = ds.rename({"TIME2": "TIME"})
        ds = ds.rename({"LATS": "lat", "LONS": "lon", "TIME": "time"})
        dset_obs = ds.sel(time=period).compute()
        dset_obs = dset_obs.rename_vars({carpatclim_varnames[variable]: variable})
        dset_obs = standardize_unit(dset_obs, variable)

        regridder = xe.Regridder(dset_obs, rotated_grid, method=regridding, unmapped_to_nan=True)
        dset_rot = regridder(dset_obs)
        if not check_equal_period(dset_rot, period):
            print(f"Temporal coverage of dataset does not match with {period}")
        ref_seasmean = seasonal_mean(dset_rot[variable].sel(time=period)).compute()
        # ref_seasmean_apgd.isel(season=0).plot()

        seasonal_bias = calc_seasonal_bias(ref_seasmean)

        df_regions_orog = make_df_regions_orog(seasonal_bias)

        df_regions_orog.to_csv(fn_out)

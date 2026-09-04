# extract from the netcdf the region info and values
import os
import xarray as xr
import pandas as pd
import geopandas as gpd
import regionmask



# %% settings
path_csv = "intermediate-csv/"


# %% aux data
gpd_regions = gpd.read_file("data/roi-02-eea.gpkg")
regions = regionmask.Regions.from_geodataframe(gpd_regions)

# eur_colors = pd.read_csv("eurocordex_models.csv")
xds_orog = xr.open_dataset("intermediate-nc/orog.nc")
df_orog = xds_orog.to_dataframe().reset_index()
df_orog2 = df_orog[["rlat", "rlon", "dset_id", "orog"]]

# round rlat and rlon coordinates for better merging later
df_orog2.loc[:,"rlat"] = df_orog2["rlat"].round(4)
df_orog2.loc[:,"rlon"] = df_orog2["rlon"].round(4)

# %% main loop
l_ref_data = ["eobs", "cerra"]
l_variable = ["tas", "tasmax", "tasmin", "pr"]

for ref_data in l_ref_data:
    for variable in l_variable:
        
        # ref_data = "eobs"
        # variable = "tas"
        # elev_bins = 200

        xds = xr.open_dataset("intermediate-nc/" + ref_data + "_" + variable + "_CMIP6_1991-2020_spatial_bias.nc")
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

        df_regions_orog.to_csv(f"{path_csv}/{ref_data}_{variable}.csv")




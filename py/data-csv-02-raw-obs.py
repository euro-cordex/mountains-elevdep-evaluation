# extract from the netcdf the region info and values
import os
import xarray as xr
import pandas as pd
import geopandas as gpd
import regionmask



# %% settings
path_csv = "intermediate-csv-rawobs/"


# %% aux data
gpd_regions = gpd.read_file("data/roi-02-eea.gpkg")
regions = regionmask.Regions.from_geodataframe(gpd_regions)

# %% main loop
l_ref_data = ["eobs", "cerra", "rocio-ibeb", "apgd", "iberia01", "carpatclim"]
l_variable = ["tas", "tasmax", "tasmin", "pr"]

for ref_data in l_ref_data:
    for variable in l_variable:
        
# ref_data = "eobs"
# variable = "tas"
# elev_bins = 200

        fn_in = "intermediate-nc/raw-obs/" + ref_data + "_" + variable + "_1991-2010.nc"
        if(not os.path.exists(fn_in)):
            print(f"File {fn_in} does not exist. Skipping...")
            continue


        xds_rawobs = xr.open_dataset(fn_in)
        xds_rawobs = xds_rawobs.rename({"__xarray_dataarray_variable__": variable})
        df_rawobs = xds_rawobs.to_dataframe().reset_index()

        mask = regions.mask_3D(xds_rawobs["lon"], xds_rawobs["lat"], drop=False)
        df_mask = mask.to_dataframe().reset_index()
        df_mask_tosubset = df_mask[["region", "rlat", "rlon", "names", "mask"]][df_mask["mask"]]

        df_regions = pd.merge(df_rawobs, df_mask_tosubset).dropna()

        df_regions["rlon_key"] = (df_regions["rlon"] * 1e4).round().astype(int)
        df_regions["rlat_key"] = (df_regions["rlat"] * 1e4).round().astype(int)

        df_regions.to_csv(f"{path_csv}/{ref_data}_{variable}.csv")
import intake

cat = intake.open_esm_datastore("https://raw.githubusercontent.com/euro-cordex/jsc-cordex-catalog/refs/heads/main/CORDEX-CMIP6-JSC.json")
cat.keys()




ref_data = "cerra"
ref_data = "eobs"
variable = "tas"
# elev_bins = 200

xds = xr.open_dataset("intermediate-nc/" + ref_data + "_" + variable + "_CMIP6_1991-2020_spatial_bias.nc")
df = xds.to_dataframe().reset_index()

mask = regions.mask_3D(xds["lon"], xds["lat"], drop=False)
df_mask = mask.to_dataframe().reset_index()
df_mask_tosubset = df_mask[["region", "rlat", "rlon", "names", "mask"]][df_mask["mask"]]

# df.loc[:,"rlat"] = df["rlat"].round(4)
# df.loc[:,"rlon"] = df["rlon"].round(4)
# df_mask_tosubset.loc[:,"rlat"] = df_mask_tosubset["rlat"].round(4)
# df_mask_tosubset.loc[:,"rlon"] = df_mask_tosubset["rlon"].round(4)
# df_regions.loc[:,"rlat"] = df_regions["rlat"].round(4)
# df_regions.loc[:,"rlon"] = df_regions["rlon"].round(4)
# df_mask_tosubset["rlat"] = df_mask_tosubset["rlat"].round(4)
# df_mask_tosubset["rlon"] = df_mask_tosubset["rlon"].round(4)

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

df_regions_orog = df_regions_orog.drop(columns=["rlon_key", "rlat_key", "rlat_x", "rlon_x",
"crs", "mask", "areacella"])

# df_regions_orog = pd.merge(df_regions, df_orog2)

df_regions_orog.to_csv(f"{path_csv}/{ref_data}_{variable}.csv")

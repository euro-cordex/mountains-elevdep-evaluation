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

# 18 for daily pr

dsets = open_datasets(
    ["pr"],
    frequency=frequency,
    driving_source_id=driving_source_id,
    mask=True,
    add_missing_bounds=False,
)

kk = 'CORDEX-CMIP6.EUR-12.IDL-FCUL.ERA5.evaluation.r1i1p1f1.WRF451Q.v1-r1.day.v20240630'
dsets[kk]

dsets2 = open_datasets(
    ["pr", "tas"],
    frequency=frequency,
    driving_source_id=driving_source_id,
    mask=True,
    add_missing_bounds=False,
)


ref_seasmean.keys()
# ref_seasmean.sel("DJF")
ref_seasmean.sel(season="DJF").plot()
zz = eobs.tn.isel(time=0)
zz.plot()


eobs = obs.eobs(variables=eobs_var, add_mask=False).sel(time=period)

zz2 = eobs.tn.isel(time=0)
# zz2 = eobs.tn.isel(time=000)
zz2.plot()

eobs2 = mask_invalid(eobs, vars=eobs_var, threshold=0.3)
zz3 = eobs2.tn.isel(time=0)
zz3 = eobs2.tn.isel(time=10000)
zz3.plot()

zz4 = eobs_rot.isel(time=0)
zz4.tn.plot()


regridder = xe.Regridder(eobs, rotated_grid, method=regridding, unmapped_to_nan=True)
eobs_rot2 = regridder(eobs)
eobs_rot2.isel(time=0).tn.plot()




dd = dsets2["CORDEX-CMIP6.EUR-12.CLMcom-Hereon.ERA5.evaluation.r1i1p1f1.CCLM6-0-1.v1-r1.mon.v20230222"]
dd.isel(time=0).tasmin.plot()


zz = xr.open_mfdataset([
    "/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/day/tasmax/tasmax_raw_CERRA_19910101_19911231.nc",
    "/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/day/tasmax/tasmax_raw_CERRA_19920101_19921231.nc"
])
xr.open_dataset("/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/day/tasmax/tasmax_raw_CERRA_19910101_19911231.nc")


period = slice("1991", "1992")

eobs = obs.eobs(variables=eobs_var, add_mask=False).sel(time=period)
eobs = mask_invalid(eobs, vars=eobs_var, threshold=0.1)
eobs = eobs.assign(
    pr_liquid=xr.where(eobs["tg"] >= 202 - 200, eobs["rr"], 0),
    pr_solid=xr.where(eobs["tg"] < 202 - 200, eobs["rr"], 0),
)

eobs.pr_liquid.isel(time=0).plot()
eobs.pr_solid.isel(time=0).plot()
plt.figure()

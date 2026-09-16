# temporary code R

dat <- fread("intermediate-csv/rocio_tasmin.csv")
dat <- fread("intermediate-csv/cerra_tasmin.csv")
dat <- fread("intermediate-csv/eobs_tasmin.csv")
dat[, .N, dset_id]
dat[dset_id == "HCLIM43-ALADIN" & season == "DJF"]
dat[
  dset_id ==
    "CORDEX-CMIP6.EUR-12.MOHC.ERA5.evaluation.r1i1p1f1.HadREM3-GA7-05.v1-r1.mon.v20260318" &
    season == "DJF"
]

dat$dset_id[1] |>
  str_split("[.]")

id_elements <- c(
  "era",
  "domain",
  "institute",
  "driving_model",
  "experiment",
  "realisation",
  "rcm",
  "ds_version",
  "freq",
  "version"
)


dat[, c(id_elements) := tstrsplit(dset_id, "[.]")]

dat[, .N, .(institute, rcm)]
dat[rcm == "HadREM3-GA7-05", .N, .(version)]
dat[rcm == "GCOAST-AHOIB1-1", .N, .(realisation, ds_version, version)]


dat_mm |>
  ggplot(aes(rlon_y, rlat_y, fill = val_mean)) +
  geom_raster() +
  facet_grid(. ~ season) +
  coord_fixed(ratio = 1) +
  cowplot::theme_map()


dir_ls("intermediate-csv/", type = "file") |>
  str_subset("orog", negate = T)

dat_zz <- dir_ls("intermediate-csv/", type = "file")[1:2] |>
  str_subset("orog", negate = T) |>
  map(\(fn) {
    fn_info <- path_file(fn) |>
      path_ext_remove() |>
      str_split_1("_")

    variable <- fn_info[2]
    ref_data <- fn_info[1]

    dat <- fread(fn)
    dat[, elev_grp := cut(orog, breaks = elev_breaks, dig.lab = 5)]
    setnames(dat, variable, "value")

    dat2 <- dat[,
      .(value = mean(value), nn = .N),
      .(dset_id, season, region = names, elev_grp)
    ]
    cbind(dat2, variable, ref_data)
  }) |>
  rbindlist()

dat_zz$region |> table()

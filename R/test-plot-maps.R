#
library(ggplot2)
library(data.table)
library(fs)
library(stringr)
library(forcats)
library(purrr)
library(scico)

id_elements <- c(
  "project",
  "domain",
  "institution",
  "driving_source",
  "driving_experiment",
  "driving_variant",
  "rcm",
  "version_realization",
  "frequency",
  "version"
)

# id_elements <- c(
#   "era",
#   "domain",
#   "institute",
#   "driving_model",
#   "experiment",
#   "realisation",
#   "rcm",
#   "ds_version",
#   "freq",
#   "version"
# )

dir_ls("intermediate-csv-extra/") |>
  map(\(fn) {
    fn_info <- path_file(fn) |>
      path_ext_remove() |>
      str_split_1("_")

    variable <- fn_info[2]
    ref_data <- fn_info[1]

    dat <- fread(fn)
    dat[, c(id_elements) := tstrsplit(dset_id, "[.]")]
    setnames(dat, variable, "value")

    # orog not well matched
    dat <- dat[rcm != "HadREM3-GA7-05"]

    # multiple versions of GCOAST-AHOIB1-1
    dat <- dat[!(rcm == "GCOAST-AHOIB1-1" & version == "v20240920")]
    dat <- dat[!(rcm == "GCOAST-AHOIB1-1" & version_realization == "v1-r1")]

    # dat[, .N, keyby = .(institution, rcm)]

    dat_mm <- dat[,
      .(
        val_mean = mean(value),
        val_min = min(value),
        val_max = max(value)
      ),
      .(season, region = names, lon, lat, rlat_y, rlon_y)
    ]

    dat_mm[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]
    setorder(dat_mm, region)

    cbind(dat_mm, variable, ref_data)
  }) |>
  rbindlist() -> dat_extra


dir_ls("intermediate-csv/") |>
  map(\(fn) {
    fn_info <- path_file(fn) |>
      path_ext_remove() |>
      str_split_1("_")

    variable <- fn_info[2]
    ref_data <- fn_info[1]

    dat <- fread(fn)
    dat[, c(id_elements) := tstrsplit(dset_id, "[.]")]
    setnames(dat, variable, "value")

    # orog not well matched
    dat <- dat[rcm != "HadREM3-GA7-05"]

    # multiple versions of GCOAST-AHOIB1-1
    dat <- dat[!(rcm == "GCOAST-AHOIB1-1" & version == "v20240920")]
    dat <- dat[!(rcm == "GCOAST-AHOIB1-1" & version_realization == "v1-r1")]

    # dat[, .N, keyby = .(institution, rcm)]

    dat_mm <- dat[,
      .(
        val_mean = mean(value),
        val_min = min(value),
        val_max = max(value)
      ),
      .(season, region = names, lon, lat, rlat_y, rlon_y)
    ]

    dat_mm[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]
    setorder(dat_mm, region)

    cbind(dat_mm, variable, ref_data)
  }) |>
  rbindlist() -> dat_main


# sort(unique(dat_extra$region))
all_regions <- c("Alps", "Carpathians", "Iberian mountains")
all_regions_path <- path_sanitize(all_regions)

dat1 <- rbind(
  dat_main[region %in% all_regions],
  dat_extra[region %in% all_regions]
)

# i_variable <- "pr"
# i_region <- "Iberian mountains"

for (i_variable in c("tas", "tasmin", "tasmax", "pr")) {
  for (j_region in seq_along(all_regions)) {
    i_region <- all_regions[j_region]

    dat_plot <- dat1[variable == i_variable & region == i_region]

    # if (nrow(dat_mm[region == i_region]) == 0) {
    #   next
    # }

    gg <-
      dat_plot |>
      ggplot(aes(rlon_y, rlat_y, fill = val_mean)) +
      geom_raster() +

      facet_grid(ref_data ~ season) +
      coord_fixed(ratio = 1) +
      cowplot::theme_map() +
      ggtitle(str_c(i_variable, " - ", i_region))

    if (i_variable == "pr") {
      gg <- gg +
        scale_fill_scico(
          NULL,
          palette = "broc",
          midpoint = 0,
          direction = -1,
          labels = scales::label_percent(scale = 1),
        )
    } else {
      gg <- gg +
        scale_fill_scico(NULL, palette = "roma", midpoint = 0, direction = -1)
    }
    gg

    fn_out <- path(
      "fig/maps-modelmeans-extra/",
      str_c(i_variable, "_", all_regions_path[j_region]),
      ext = "png"
    )

    ggsave(fn_out, gg, width = 12, height = 8, bg = "white")
  }
}

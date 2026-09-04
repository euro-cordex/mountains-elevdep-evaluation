#
library(ggplot2)
library(data.table)
library(fs)
library(stringr)
library(forcats)
library(purrr)
library(scico)

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

all_regions <- sort(unique(dat$names))
all_regions_path <- path_sanitize(all_regions)

# i_refdata <- "cerra"
# i_variable <- "tasmin"
# i_region <- "Alps"

for (i_refdata in c("cerra", "eobs")) {
  for (i_variable in c("tas", "tasmin", "tasmax", "pr")) {
    dat <- fread(str_c("intermediate-csv/", i_refdata, "_", i_variable, ".csv"))
    dat[, c(id_elements) := tstrsplit(dset_id, "[.]")]

    # orog not well matched
    dat <- dat[rcm != "HadREM3-GA7-05"]

    # multiple versions of GCOAST-AHOIB1-1
    dat <- dat[!(rcm == "GCOAST-AHOIB1-1" & version == "v20240920")]
    dat <- dat[!(rcm == "GCOAST-AHOIB1-1" & ds_version == "v1-r1")]

    dat[, .N, keyby = .(institute, rcm)]

    setnames(dat, i_variable, "value")
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

    for (j_region in seq_along(all_regions)) {
      i_region <- all_regions[j_region]

      if (nrow(dat_mm[region == i_region]) == 0) {
        next
      }

      gg <-
        dat_mm[region == i_region] |>
        ggplot(aes(rlon_y, rlat_y, fill = val_mean)) +
        geom_raster() +

        facet_wrap(~season) +
        coord_fixed(ratio = 1) +
        cowplot::theme_map() +
        ggtitle(str_c(i_refdata, " - ", i_variable, " - ", i_region))

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
      # gg

      fn_out <- path(
        "fig/maps-modelmeans/",
        i_refdata,
        str_c(i_variable, "_", all_regions_path[j_region]),
        ext = "png"
      )

      ggsave(fn_out, gg, width = 12, height = 8, bg = "white")
    }
  }
}

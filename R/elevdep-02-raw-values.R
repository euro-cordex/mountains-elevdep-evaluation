#
library(ggplot2)
library(data.table)
library(fs)
library(stringr)
library(forcats)
library(purrr)

dat_colors <- fread("data/eurocordex_models.csv")

elev_bins <- 200
elev_breaks <- c(-20, seq(elev_bins, 3100 - elev_bins, by = elev_bins), 3100)

# 'project_id.domain_id.institution_id.driving_source_id.driving_experiment_id.driving_variant_label.source_id.version_realization.frequency.version'
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

# need a reference orog that is not RCM
dat_orog <- fread("intermediate-csv/orog/mean_orog_rcm.csv")
dat_orog[, rlon_key := as.integer(round(1e4 * rlon))]
dat_orog[, rlat_key := as.integer(round(1e4 * rlat))]


dat_elev_obs <- dir_ls("intermediate-csv-rawobs/", type = "file") |>
  str_subset("eobs|cerra") |>
  map(\(fn) {
    fn_info <- path_file(fn) |>
      path_ext_remove() |>
      str_split_1("_")

    variable <- fn_info[2]
    ref_data <- fn_info[1]

    dat <- fread(fn)
    setnames(dat, variable, "value")

    dat2 <- merge(
      dat,
      dat_orog[, .(rlat_key, rlon_key, orog)]
    )
    dat2[, elev_grp := cut(orog, breaks = elev_breaks, dig.lab = 5)]
    dat3 <- dat2[,
      .(value = mean(value), nn = .N),
      .(season, region = names, elev_grp)
    ]
    cbind(dat3, variable, ref_data)
  }) |>
  rbindlist(use.names = T, fill = T)

dat_elev_rcm <- dir_ls("intermediate-csv/", type = "file") |>
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


dat_elev_rcm[, c(id_elements) := tstrsplit(dset_id, "[.]")]

# orog not well matched
dat_elev_rcm <- dat_elev_rcm[rcm != "HadREM3-GA7-05"]

# multiple versions of GCOAST-AHOIB1-1
dat_elev_rcm <- dat_elev_rcm[
  !(rcm == "GCOAST-AHOIB1-1" & version == "v20240920")
]
dat_elev_rcm <- dat_elev_rcm[
  !(rcm == "GCOAST-AHOIB1-1" & version_realization == "v1-r1")
]

dat_elev_rcm[, .N, keyby = .(institution, rcm)]

dat_elev_rcm2 <- merge(
  dat_elev_rcm[ref_data == "cerra"],
  dat_elev_obs[
    ref_data == "cerra",
    .(season, variable, region, elev_grp, value_obs = value)
  ]
)
dat_elev_rcm2[variable == "pr", value_raw := (value / 100 + 1) * value_obs]
dat_elev_rcm2[variable != "pr", value_raw := value + value_obs]


setorder(dat_elev_obs, elev_grp)

for (i_var in c("tas", "tasmin", "tasmax", "pr")) {
  # xmax <- dat_elev_mm[variable == i_var, max(val_max)]

  if (i_var == "pr") {
    xl <- str_c(i_var, " climatology [mm/d]")
  } else {
    xl <- str_c(i_var, " climatology [K]")
  }

  for (i_seas in c("DJF", "MAM", "JJA", "SON")) {
    dat_plot_rcm <- dat_elev_rcm2[variable == i_var & season == i_seas] |>
      merge(
        dat_colors[, .(
          rcm = model,
          rcm_color = color,
          rcm_family = family
        )],
        by = "rcm"
      )
    setorder(dat_plot_rcm, elev_grp)

    gg <- dat_plot_rcm |>
      ggplot() +
      geom_path(
        aes(
          value_raw,
          elev_grp,
          colour = rcm_color,
          # linetype = rcm_family,
          group = paste0(institution, rcm, version_realization)
        ),
        alpha = 0.7
      ) +
      geom_path(
        data = dat_elev_obs[variable == i_var & season == i_seas],
        aes(
          value,
          elev_grp,
          linetype = ref_data,
          group = paste0(ref_data, region)
        ),
        colour = "black"
      ) +
      scale_color_identity(
        "RCM",
        guide = "legend",
        breaks = dat_colors$color,
        labels = dat_colors$model
      ) +
      scale_linetype("Ref data") +
      facet_wrap(. ~ region) +
      theme_bw() +
      xlab(xl) +
      ylab("Elevation band [m]")

    ggsave(
      str_c("fig/raw-values/", i_var, "_", i_seas, ".pdf"),
      width = 12,
      height = 8,
      create.dir = T
    )
  }
}

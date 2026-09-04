#
library(ggplot2)
library(data.table)
library(fs)
library(stringr)
library(forcats)
library(purrr)

elev_bins <- 200
elev_breaks <- c(-20, seq(elev_bins, 3100 - elev_bins, by = elev_bins), 3100)

# 'project_id.domain_id.institution_id.driving_source_id.driving_experiment_id.driving_variant_label.source_id.version_realization.frequency.version'
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


dat_elev <- dir_ls("intermediate-csv/") |>
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


dat_elev[, c(id_elements) := tstrsplit(dset_id, "[.]")]

# orog not well matched
dat_elev <- dat_elev[rcm != "HadREM3-GA7-05"]

# multiple versions of GCOAST-AHOIB1-1
dat_elev <- dat_elev[!(rcm == "GCOAST-AHOIB1-1" & version == "v20240920")]
dat_elev <- dat_elev[!(rcm == "GCOAST-AHOIB1-1" & ds_version == "v1-r1")]

dat_elev[, .N, keyby = .(institute, rcm)]

dat_elev_mm <- dat_elev[,
  .(
    val_mean = mean(value),
    val_min = min(value),
    val_max = max(value),
    nn_mean = mean(nn)
  ),
  .(ref_data, season, region, elev_grp, variable)
]

dat_elev_mm[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]
setorder(dat_elev_mm, elev_grp)

dat_elev_mm[,
  ref_data2 := fct_recode(ref_data, "CERRA" = "cerra", "E-OBS" = "eobs")
]

for (i_var in c("tas", "tasmin", "tasmax")) {
  xmax <- dat_elev_mm[variable == i_var, max(val_max)]

  gg <- dat_elev_mm[variable == i_var] |>
    ggplot(aes(
      val_mean,
      elev_grp,
      colour = ref_data2,
      fill = ref_data2,
      group = ref_data2
    )) +
    geom_text(
      aes(
        x = xmax,
        y = elev_grp,
        label = nn_mean |> round(0),
        vjust = ifelse(ref_data == "cerra", -0.1, 1.1)
      ),
      size = 1.5,
      hjust = 1
    ) +
    geom_vline(xintercept = 0, linetype = "dashed") +
    geom_ribbon(
      aes(xmin = val_min, xmax = val_max),
      linetype = "blank",
      alpha = 0.3
    ) +
    geom_path() +
    scale_color_brewer(
      "Reference",
      palette = "Set1",
      aesthetics = c("colour", "fill")
    ) +
    facet_grid(season ~ region) +
    theme_bw() +
    xlab(str_c(i_var, "Tas bias: Ensemble mean and range [°C]")) +
    ylab("Elevation band [m]")

  ggsave(
    str_c("fig/elevdep/modelmeanens_", i_var, ".pdf"),
    gg,
    width = 16,
    height = 8
  )
}


xmin <- dat_elev_mm[variable == "pr", min(val_min)]

gg <- dat_elev_mm[variable == "pr"] |>
  ggplot(aes(
    val_mean,
    elev_grp,
    colour = ref_data2,
    fill = ref_data2,
    group = ref_data2
  )) +
  geom_vline(xintercept = 0, linetype = "dashed") +
  geom_text(
    aes(
      x = xmin,
      y = elev_grp,
      label = nn_mean |> round(0),
      vjust = ifelse(ref_data == "cerra", -0.1, 1.1)
    ),
    size = 1.5,
    hjust = 0
  ) +
  geom_ribbon(
    aes(xmin = val_min, xmax = val_max),
    linetype = "blank",
    alpha = 0.3
  ) +
  geom_path() +
  scale_color_brewer(
    "Reference",
    palette = "Set1",
    aesthetics = c("colour", "fill")
  ) +
  facet_grid(season ~ region) +
  theme_bw() +
  scale_x_continuous(limits = c(NA, 200), oob = scales::oob_squish) +
  xlab("Pr bias: Ensemble mean and range [%]") +
  ylab("Elevation band [m]")

ggsave("fig/elevdep/modelmeanens_pr.pdf", gg, width = 16, height = 8)

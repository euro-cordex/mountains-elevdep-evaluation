#
library(ggplot2)
library(data.table)
library(fs)
library(stringr)
library(forcats)
library(purrr)

elev_bins <- 200
elev_breaks <- c(-20, seq(elev_bins, 3100 - elev_bins, by = elev_bins), 3100)

dat_elev <- dir_ls("intermediate-results/csv/") |>
  map(\(fn) {
    fn_info <- path_file(fn) |>
      path_ext_remove() |>
      str_split_1("_")

    variable <- fn_info[3]
    ref_data <- fn_info[2]

    dat <- fread(fn)
    dat[, elev_grp := cut(orog / 1000, breaks = elev_breaks, dig.lab = 5)]
    setnames(dat, variable, "value")

    dat2 <- dat[,
      .(value = mean(value)),
      .(rcm = dset_id, season, region = names, elev_grp)
    ]
    cbind(dat2, variable, ref_data)
  }) |>
  rbindlist()

dat_elev_mm <- dat_elev[,
  .(val_mean = mean(value), val_min = min(value), val_max = max(value)),
  .(ref_data, season, region, elev_grp, variable)
]

dat_elev_mm[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]
setorder(dat_elev_mm, elev_grp)

dat_elev_mm[,
  ref_data2 := fct_recode(ref_data, "CERRA" = "cerra", "E-OBS" = "eobs")
]

dat_elev_mm[variable == "tas"] |>
  ggplot(aes(
    val_mean,
    elev_grp,
    colour = ref_data2,
    fill = ref_data2,
    group = ref_data2
  )) +
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
  xlab("Tas bias: Ensemble mean and range [°C]") +
  ylab("Elevation band [m]")

ggsave("fig/elevdep/modelmeanens_tas.png", width = 12, height = 8)


dat_elev_mm[variable == "pr"] |>
  ggplot(aes(
    val_mean,
    elev_grp,
    colour = ref_data2,
    fill = ref_data2,
    group = ref_data2
  )) +
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
  scale_x_continuous(limits = c(NA, 200), oob = scales::oob_squish) +
  xlab("Pr bias: Ensemble mean and range [%]") +
  ylab("Elevation band [m]")

ggsave("fig/elevdep/modelmeanens_pr.png", width = 12, height = 8)

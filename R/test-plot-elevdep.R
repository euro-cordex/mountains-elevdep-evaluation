#
library(ggplot2)
library(data.table)
library(fs)
library(stringr)
library(forcats)
library(purrr)
library(scico)


# data prep --------------------------------------------------------------

dat_colors <- fread("data/eurocordex_models.csv")

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

elev_bins <- 200
elev_breaks <- c(-20, seq(elev_bins, 3100 - elev_bins, by = elev_bins), 3100)


dir_ls("intermediate-csv-extra/") |>
  map(\(fn) {
    fn_info <- path_file(fn) |>
      path_ext_remove() |>
      str_split_1("_")

    variable <- fn_info[2]
    ref_data <- fn_info[1]

    dat <- fread(fn)
    setnames(dat, variable, "value")

    dat[, elev_grp := cut(orog, breaks = elev_breaks, dig.lab = 5)]
    dat2 <- dat[,
      .(value = mean(value), nn = .N),
      .(dset_id, season, region = names, elev_grp)
    ]
    cbind(dat2, variable, ref_data)
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
    setnames(dat, variable, "value")

    dat[, elev_grp := cut(orog, breaks = elev_breaks, dig.lab = 5)]
    dat2 <- dat[,
      .(value = mean(value), nn = .N),
      .(dset_id, season, region = names, elev_grp)
    ]
    cbind(dat2, variable, ref_data)
  }) |>
  rbindlist() -> dat_main


# sort(unique(dat_extra$region))
all_regions <- c("Alps", "Carpathians", "Iberian mountains")
all_regions_path <- path_sanitize(all_regions)

dat1 <- rbind(
  dat_main[region %in% all_regions],
  dat_extra[region %in% all_regions]
)


dat1[, c(id_elements) := tstrsplit(dset_id, "[.]")]

# orog not well matched
dat1 <- dat1[rcm != "HadREM3-GA7-05"]

# multiple versions of GCOAST-AHOIB1-1
dat1 <- dat1[!(rcm == "GCOAST-AHOIB1-1" & version == "v20240920")]
dat1 <- dat1[!(rcm == "GCOAST-AHOIB1-1" & version_realization == "v1-r1")]


dat_elev_mm <- dat1[,
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


# modelmean tas* ---------------------------------------------------------

for (i_var in c("tas", "tasmin", "tasmax")) {
  xmax <- dat_elev_mm[variable == i_var, max(val_max)]

  gg <- dat_elev_mm[variable == i_var] |>
    ggplot(aes(
      val_mean,
      elev_grp,
      colour = ref_data,
      fill = ref_data,
      group = ref_data
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
    xlab(str_c(i_var, " bias: Ensemble mean and range [°C]")) +
    ylab("Elevation band [m]")

  ggsave(
    str_c("fig/elevdep-extra/modelmeanens_", i_var, ".pdf"),
    gg,
    width = 12,
    height = 8
  )
}


# modelmean pr -----------------------------------------------------------

xmin <- dat_elev_mm[variable == "pr", min(val_min)]

gg <- dat_elev_mm[variable == "pr"] |>
  ggplot(aes(
    val_mean,
    elev_grp,
    colour = ref_data,
    fill = ref_data,
    group = ref_data
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

ggsave("fig/elevdep-extra/modelmeanens_pr.pdf", gg, width = 12, height = 8)

# by model? --------------------------------------------------------------

dat1[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]

# dat1[
#   variable == "pr" & region == "Alps" & season == "DJF",
#   .N,
#   .(institution, rcm)
# ]

for (i in seq_along(all_regions)) {
  i_region <- all_regions[i]
  i_region_path <- all_regions_path[i]

  # tas*
  for (i_var in c("tas", "tasmin", "tasmax")) {
    dat_plot_singlemodel <- dat1[variable == i_var & region == i_region] |>
      merge(dat_colors[, .(
        rcm = model,
        rcm_color = color,
        rcm_family = family
      )])
    setorder(dat_plot_singlemodel, elev_grp)

    gg <- dat_plot_singlemodel |>
      ggplot(aes(
        value,
        elev_grp,
        colour = rcm_color,
        # linetype = rcm_family,
        group = paste0(institution, rcm, version_realization)
      )) +
      geom_vline(xintercept = 0, linetype = "dashed") +
      geom_path(alpha = 0.7) +
      scale_color_identity(
        "RCM",
        guide = "legend",
        breaks = dat_colors$color,
        labels = dat_colors$model
      ) +
      facet_grid(season ~ ref_data) +
      theme_bw() +
      xlab(str_c(i_var, " bias [°C]")) +
      ylab("Elevation band [m]")

    fn_out <- path(
      "fig/elevdep-extra-singlemodel",
      str_c(i_var, "_", i_region_path, ".pdf")
    )

    ggsave(
      fn_out,
      gg,
      width = 12,
      height = 8
    )
  }

  # pr

  dat_plot_singlemodel <- dat1[variable == "pr" & region == i_region] |>
    merge(dat_colors[, .(rcm = model, rcm_color = color, rcm_family = family)])
  setorder(dat_plot_singlemodel, elev_grp)

  gg <- dat_plot_singlemodel |>
    ggplot(aes(
      value,
      elev_grp,
      colour = rcm_color,
      # linetype = rcm_family,
      group = paste0(institution, rcm, version_realization)
    )) +
    geom_vline(xintercept = 0, linetype = "dashed") +
    geom_path(alpha = 0.7) +
    scale_color_identity(
      "RCM",
      guide = "legend",
      breaks = dat_colors$color,
      labels = dat_colors$model
    ) +
    facet_grid(season ~ ref_data) +
    theme_bw() +
    scale_x_continuous(limits = c(NA, 200), oob = scales::oob_squish) +
    xlab("Pr bias [%]") +
    ylab("Elevation band [m]")

  fn_out <- path(
    "fig/elevdep-extra-singlemodel",
    str_c("pr_", i_region_path, ".pdf")
  )

  ggsave(
    fn_out,
    gg,
    width = 12,
    height = 8
  )
}

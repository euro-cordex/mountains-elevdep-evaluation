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


dat_eobs <- fread("intermediate-csv-precsep/eobs_1991-2010.csv")
dat_eobs2 <- melt(
  dat_eobs,
  id.vars = c("season", "names", "orog"),
  measure.vars = c("pr_solid", "pr_liquid")
)
dat_eobs2[, elev_grp := cut(orog, breaks = elev_breaks, dig.lab = 5)]
dat_eobs3 <- dat_eobs2[,
  .(value = mean(value), nn = .N),
  .(season, region = names, elev_grp, variable)
]


dat_rcm <- fread("intermediate-csv-precsep/rcm_1991-2010.csv")

# some weird NA orog in RCMs??
# dat_rcm[dset_id == "CORDEX-CMIP6.EUR-12.IDL-FCUL.ERA5.evaluation.r1i1p1f1.WRF451Q.v1-r1.day.v20240630" &
#   season == "DJF"] |>
#   ggplot(aes(rlon_y, rlat_y, fill = orog))+
#   geom_raster()

dat_rcm2 <- melt(
  dat_rcm,
  id.vars = c("dset_id", "season", "names", "orog"),
  measure.vars = c("pr_solid", "pr_liquid")
)
dat_rcm2[, elev_grp := cut(orog, breaks = elev_breaks, dig.lab = 5)]
dat_rcm3 <- dat_rcm2[
  !is.na(orog),
  .(value = mean(value), nn = .N),
  .(dset_id, season, region = names, elev_grp, variable)
]


dat_rcm3[, c(id_elements) := tstrsplit(dset_id, "[.]")]

# # orog not well matched (not avail)
# dat1 <- dat_rcm3[rcm == "HadREM3-GA7-05"]

# # multiple versions of GCOAST-AHOIB1-1
dat_rcm3 <- dat_rcm3[!(rcm == "GCOAST-AHOIB1-1" & version == "v20240920")]
dat_rcm3 <- dat_rcm3[
  !(rcm == "GCOAST-AHOIB1-1" & version_realization == "v1-r1")
]

# dat_rcm3[rcm == "WRF451Q"] # different institution

dat_rcm3[, .N, rcm]


dat_eobs3[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]
dat_rcm3[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]

dat_elev_mm <- dat_rcm3[,
  .(
    val_mean = mean(value),
    val_min = min(value),
    val_max = max(value),
    nn_mean = mean(nn)
  ),
  .(season, region, elev_grp, variable)
]

# dat_elev_mm[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]
setorder(dat_elev_mm, elev_grp)
setorder(dat_eobs3, elev_grp)

all_regions <- sort(unique(dat_eobs3$region))
# all_regions <- c("Alps", "Carpathians", "Iberian mountains")
all_regions_path <- path_sanitize(all_regions)


# modelmean pr -----------------------------------------------------------

# xmin <- dat_elev_mm[variable == "pr", min(val_min)]

gg <-
  dat_elev_mm |>
  ggplot(aes(
    val_mean,
    elev_grp,
    colour = variable,
    fill = variable,
    group = variable
  )) +
  geom_ribbon(
    aes(xmin = val_min, xmax = val_max),
    linetype = "blank",
    alpha = 0.3
  ) +
  geom_path() +
  geom_path(
    data = dat_eobs3,
    aes(x = value, linetype = variable),
    colour = "black"
  ) +
  scale_color_brewer(
    "RCM",
    palette = "Set1",
    aesthetics = c("colour", "fill")
  ) +
  scale_linetype("E-OBS") +
  facet_grid(season ~ region) +
  theme_bw() +
  # scale_x_continuous(limits = c(NA, 200), oob = scales::oob_squish) +
  xlab("Pr climatology [mm/d]") +
  ylab("Elevation band [m]")

ggsave(
  "fig/precsep/modelmeanens_eobs.pdf",
  gg,
  width = 12,
  height = 8,
  create.dir = T
)

# by model? --------------------------------------------------------------

# dat1[
#   variable == "pr" & region == "Alps" & season == "DJF",
#   .N,
#   .(institution, rcm)
# ]

for (i in seq_along(all_regions)) {
  i_region <- all_regions[i]
  i_region_path <- all_regions_path[i]

  dat_plot_singlemodel <- dat_rcm3[region == i_region] |>
    merge(dat_colors[, .(rcm = model, rcm_color = color, rcm_family = family)])
  setorder(dat_plot_singlemodel, elev_grp)

  gg <-
    dat_plot_singlemodel |>
    ggplot() +
    geom_path(
      aes(
        value,
        elev_grp,
        colour = rcm_color,
        linetype = "RCM",
        group = paste0(institution, rcm, version_realization)
      ),
      alpha = 0.7,
      size = 0.7
    ) +
    geom_path(
      data = dat_eobs3[region == i_region],
      aes(
        value,
        elev_grp,
        linetype = "E-OBS",
        group = paste0(region)
      ),
      colour = "black"
    ) +
    scale_color_identity(
      "RCM",
      guide = "legend",
      breaks = dat_colors$color,
      labels = dat_colors$model
    ) +
    facet_grid(variable ~ season) +
    theme_bw() +
    xlab("Pr liquid/solid [mm/d]") +
    ylab("Elevation band [m]")

  fn_out <- path(
    "fig/precsep-singlemodel/",
    str_c(i_region_path, ".pdf")
  )

  ggsave(
    fn_out,
    gg,
    width = 12,
    height = 6,
    create.dir = T
  )
}

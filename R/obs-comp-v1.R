#
library(ggplot2)
library(data.table)
library(fs)
library(stringr)
library(forcats)
library(purrr)
library(scico)


# data prep --------------------------------------------------------------

elev_bins <- 200
elev_breaks <- c(-20, seq(elev_bins, 3100 - elev_bins, by = elev_bins), 3100)


# need a reference orog that is not RCM
dat_orog <- fread("intermediate-csv/orog/mean_orog_rcm.csv")
dat_orog[, rlon_key := as.integer(round(1e4 * rlon))]
dat_orog[, rlat_key := as.integer(round(1e4 * rlat))]


dir_ls("intermediate-csv-rawobs/") |>
  map(\(fn) {
    fn_info <- path_file(fn) |>
      path_ext_remove() |>
      str_split_1("_")

    variable <- fn_info[2]
    ref_data <- fn_info[1]

    dat <- fread(fn)
    setnames(dat, variable, "value")

    cbind(dat, variable, ref_data)
  }) |>
  rbindlist(use.names = T, fill = T) -> dat_obs


# dat_obs$ref_data |> table()
# dat_obs[, .(rlon_key, rlat_key, names)] |> unique()

dat_obs2 <- merge(
  dat_obs,
  dat_orog[, .(rlat_key, rlon_key, orog)],
  all.x = T
)

dat_obs2 <- dat_obs2[
  ref_data == "eobs" |
    ref_data == "cerra" |
    (ref_data == "carpatclim" & names == "Carpathians") |
    (ref_data == "apgd" & names == "Alps") |
    (ref_data == "iberia01" & names == "Iberian mountains") |
    (ref_data == "rocio-ibeb" & names == "Iberian mountains")
]


dat_obs2[, elev_grp := cut(orog, breaks = elev_breaks, dig.lab = 5)]


dat_elev <- dat_obs2[,
  .(
    value = mean(value),
    nn = .N
  ),
  .(ref_data, season, region = names, elev_grp, variable)
]

dat_elev[, season := factor(season, levels = c("DJF", "MAM", "JJA", "SON"))]
setorder(dat_elev, elev_grp)


dat_nn <- dat_elev[ref_data == "eobs"]

# modelmean tas* ---------------------------------------------------------

# i_var <- "tas"
# i_seas <- "DJF"

# zz <- dat_elev[variable == i_var & season == i_seas] |>
# dcast(region + elev_grp ~ ref_data, value.var = "nn")

for (i_var in c("tas", "tasmin", "tasmax")) {
  for (i_seas in c("DJF", "MAM", "JJA", "SON")) {
    xmax <- dat_elev[variable == i_var & season == i_seas, max(value)]
    gg <-
      dat_elev[variable == i_var & season == i_seas] |>
      ggplot(aes(
        value,
        elev_grp,
        colour = ref_data,
        fill = ref_data,
        group = ref_data
      )) +
      geom_text(
        data = dat_nn[variable == i_var & season == i_seas],
        aes(
          x = xmax,
          y = elev_grp,
          label = nn
        ),
        size = 2.5,
        hjust = 1,
        show.legend = F
      ) +
      geom_path() +
      scale_color_brewer(
        "Reference",
        palette = "Set1",
        aesthetics = c("colour", "fill")
      ) +
      facet_wrap(~region) +
      theme_bw() +
      xlab(str_c(i_var, " climatology [K]")) +
      ylab("Elevation band [m]")

    ggsave(
      str_c("fig/obs-comp/", i_var, "-", i_seas, ".pdf"),
      gg,
      width = 12,
      height = 8,
      create.dir = T
    )
  }
}


# modelmean pr -----------------------------------------------------------

for (i_seas in c("DJF", "MAM", "JJA", "SON")) {
  xmax <- dat_elev[variable == "pr" & season == i_seas, max(value)]

  gg <-
    dat_elev[variable == "pr" & season == i_seas] |>
    ggplot(aes(
      value,
      elev_grp,
      colour = ref_data,
      fill = ref_data,
      group = ref_data
    )) +
    geom_text(
      data = dat_nn[variable == "pr" & season == i_seas],
      aes(
        x = xmax,
        y = elev_grp,
        label = nn
      ),
      size = 2.5,
      hjust = 1,
      show.legend = F
    ) +
    geom_path() +
    scale_color_brewer(
      "Reference",
      palette = "Set1",
      aesthetics = c("colour", "fill")
    ) +
    facet_wrap(~region) +
    theme_bw() +
    xlab("Pr climatology [mm/d]") +
    ylab("Elevation band [m]")

  ggsave(
    str_c("fig/obs-comp/pr-", i_seas, ".pdf"),
    gg,
    width = 12,
    height = 8
  )
}

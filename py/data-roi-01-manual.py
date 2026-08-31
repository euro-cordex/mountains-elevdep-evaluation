# import cartopy.crs as ccrs
# import matplotlib.pyplot as plt
import folium
import numpy as np
import regionmask
from ipyleaflet import basemaps

alps = np.array([[4.5, 43], [4.5, 48.5], [17, 48.5], [17, 43]])

carpathians = np.array([[17.0, 44], [17, 50.5], [27.5, 50.5], [27.5, 44]])  # 4 corners
# carpathians = np.array([[21.0, 47], [17.0, 47], [17, 50.5], [27.5, 50.5], [27.5, 44], [21.0, 44]])

pyrenees = np.array([[-2.5, 41.6], [-2.5, 43.6], [3.5, 43.6], [3.5, 41.6]])

scandes = np.array([[-1.0, 57.5], [17, 71.5], [33, 71.5], [15, 57.5]])  # 4 corners
# scandes = np.array([[3.0, 57.5], [3.0, 62], [18, 71.5], [33, 71.5], [15, 57.5]])


names = ["Alps", "Carpathians", "Pyrenees", "Scandes"]
abbrevs = ["Alp", "Car", "Pyr", "Sca"]

regions = regionmask.Regions(
    [alps, carpathians, pyrenees, scandes],
    names=names,
    abbrevs=abbrevs,
    name="Mountain Regions",
)


# simple plot
# regions.plot(label="abbrev")

# prep and save
regions_gdf = regions.to_geodataframe().set_crs(epsg=4326)

regions_gdf.to_file("data/roi-01-manual.gpkg")


# view on map
# m = folium.Map([50, 7], zoom_start=3, tiles=basemaps.OpenTopoMap)
# folium.GeoJson(regions_gdf).add_to(m)
# m

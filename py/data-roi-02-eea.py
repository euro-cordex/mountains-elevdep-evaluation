# import cartopy.crs as ccrs
# import matplotlib.pyplot as plt
import folium
import numpy as np
import regionmask
from ipyleaflet import basemaps
import geopandas as gpd

gpd_regions = gpd.read_file("data/eea_mountains_final_lonlat.gpkg")

regions = regionmask.Regions.from_geodataframe(gpd_regions)

# simple plot
regions.plot(label="abbrev")


# prep and save
regions_gdf = regions.to_geodataframe().set_crs(epsg=4326)
regions_gdf.to_file("data/roi-02-eea.gpkg")


# view on map
m = folium.Map([50, 7], zoom_start=3, tiles=basemaps.OpenTopoMap)
folium.GeoJson(regions_gdf).add_to(m)
m

import random
from argparse import ArgumentParser
from dataclasses import dataclass

import airportsdata
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import tqdm
from matplotlib.lines import Line2D
from shapely.geometry import Point
from sklearn.neighbors import BallTree

@dataclass
class RegionData:
    series: gpd.GeoSeries
    color: str
    style: str

parser = ArgumentParser()
parser.add_argument("-g", "--geojson", action="store_true", default=False, help="Only generate geojson files")

args = parser.parse_args()

print(f"> Generating region info using voronoi data")
print("> Loading border information...")
state_borders = gpd.read_file("USA_Boundaries_2023.geojson") # This is already in EPSG:3857
colo_border = state_borders.loc[state_borders["STATE_NAME"] == "Colorado"]

print("> Loading airports...")
airports = airportsdata.load('IATA')  # Keyed by IATA code
target_airports = ["ALS", "ASE", "CEZ", "COS", "DEN", "DRO", "EGE", "FNL", "GJT", "GUC", "HDN", "LAA", "MTJ", "PUB", "STK", "TEX"]
airport_coords = []

idx = 0
for code in tqdm.tqdm(target_airports, unit="aps"):
    if code in airports:
        ap = airports[code]
        airport_coords.append({
            'iata_index': idx,
            'code': code,
            'geometry': Point(ap['lon'], ap['lat']),
            'lat': ap['lat'],
            'lon': ap['lon'],
        })
        idx += 1

airports_gdf = gpd.GeoDataFrame(airport_coords, crs="EPSG:3857")

data = airports_gdf.to_json()
with open("json/airports.geojson", "w+") as f:
    f.write(data)


print("> Generating regions...")

voronoi_polys = airports_gdf.voronoi_polygons(extend_to=colo_border.boundary) # type: ignore

voronoi_gdf = gpd.GeoDataFrame(geometry=voronoi_polys, crs="EPSG:3857").clip(colo_border)

merged = gpd.sjoin(airports_gdf, voronoi_gdf, how="right", predicate="within")

for idx, row in merged.iterrows():
    filename = f"json/{row['code']}.geojson"
    single_poly = gpd.GeoDataFrame([row], crs=voronoi_gdf.crs)
    single_poly.to_file(filename, driver="GeoJSON")

if not args.geojson:
    fig, ax = plt.subplots(figsize=(15, 15))
    colo_border.plot(ax=ax, facecolor=None, edgecolor="black", color=None)

    merged.plot(ax=ax, facecolor=None, edgecolor="red", color=None)

    ax.axis(False)
    plt.show()
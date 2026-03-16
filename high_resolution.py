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
parser.add_argument("-r", "--resolution", action="store", type=float, default=0.005, help="Resolution in degrees")

args = parser.parse_args()

resolution = args.resolution
print(f"> Generating region info at a resolution of {resolution} degrees")
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

print("> Generating points...")
bounds = colo_border.total_bounds
x_coords = np.arange(bounds[0], bounds[2], resolution)
y_coords = np.arange(bounds[1], bounds[3], resolution)

points = []
bar = tqdm.tqdm(total=len(x_coords)*len(y_coords), unit="points")
base_limits = colo_border.union_all()
for x in x_coords:
    for y in y_coords:
        pt = Point(x, y)
        if colo_border.geometry.contains(pt).any():
            points.append(pt)
        bar.update()
bar.close()
points_gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:3857")


points_gdf["lon"] = points_gdf.geometry.x
points_gdf["lat"] = points_gdf.geometry.y


print("> Calculating zones...")
tree = BallTree(airports_gdf[['lat', 'lon']].values, leaf_size=2)
_, points_gdf["iata_index"] = tree.query(points_gdf[["lat", "lon"]], k=1)

merged = points_gdf.merge(airports_gdf, on="iata_index")

lines = []
for x in tqdm.tqdm(merged.itertuples(), unit="lines", total=len(merged)):
    lines.append(Line2D((x.geometry_x.x, x.geometry_x.y), (x.geometry_y.x, x.geometry_y.y))) # type: ignore
# lines = [Line2D((x.geometry_x.x, x.geometry_x.y), (x.geometry_y.x, x.geometry_y.y)) for x in merged.itertuples()] 

print("> Plotting...")
colors = ["green", "orange", "blue", "red"]
styles = ["solid", "dashed", "dotted", "dashdot"]
used = []

regions = {}

for airport in tqdm.tqdm(target_airports, unit="aps"):
    mask = merged["code"] == airport
    region = merged.loc[mask]
    region = region.set_geometry("geometry_x")
    bnd = region.union_all().convex_hull
    line = bnd.boundary
    style = random.choice(styles)
    color = random.choice(colors)
    while f"{style}:{color}" in used:
        style = random.choice(styles)
        color = random.choice(colors)

    used.append(f"{style}:{color}")
    series = gpd.GeoSeries([line])
    regions[airport] = RegionData(series=series, color=color, style=style)
    data = series.to_json()
    with open(f"json/hires/{airport}.json", "w+") as f:
        f.write(data)

fig, ax = plt.subplots(figsize=(150, 150))
colo_border.plot(ax=ax, facecolor="none", edgecolor="black")

for region in tqdm.tqdm(regions, unit="regions"):
    series = regions[region].series
    series.plot(ax=ax, color=regions[region].color, linestyle=regions[region].style, label=region)
    center = series.centroid
    ax.annotate(text=region, xy=(float(center.values.x[0]), float(center.values.y[0])), fontsize=100)

print("> Saving figure...")
plt.savefig(f"regions_{resolution}.png", dpi=200)
# plt.show()
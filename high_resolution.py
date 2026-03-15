import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from shapely.geometry import Point
import airportsdata
from sklearn.neighbors import BallTree
import random
import tqdm

print("> Loading border information...")
state_borders = gpd.read_file("USA_Boundaries_2023.geojson") # This is already in EPSG:3857
colo_border = state_borders.loc[state_borders["STATE_NAME"] == "Colorado"]

print("> Loading airports...")
airports = airportsdata.load('IATA')  # Keyed by IATA code
target_airports = ["ALS", "ASE", "CEZ", "COS", "DEN", "DRO", "EGE", "FNL", "GJT", "GUC", "HDN", "LAA", "MTJ", "PUB", "STK", "TEX"]
airport_coords = []

idx = 0
for code in target_airports:
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

print("> Generating points (this will take a while!)...")
# n = .0005
n = .005
bounds = colo_border.total_bounds
print(">>> Generating X coords...")
x_coords = np.arange(bounds[0], bounds[2], n)
print(">>> Generating Y coords...")
y_coords = np.arange(bounds[1], bounds[3], n)

print(">>> Generating points...")
points = []
bar = tqdm.tqdm(total=len(x_coords)*len(y_coords), unit="point")
base_limits = colo_border.union_all()
for x in x_coords:
    for y in y_coords:
        pt = Point(x, y)
        if pt.within(base_limits):
            points.append(pt)
        bar.update()
bar.close()
print(">>> Creating dataframe...")
# points_gdf = gpd.GeoDataFrame(geometry=points, crs=colo_projected.crs)
points_gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:3857")


points_gdf["lon"] = points_gdf.geometry.x
points_gdf["lat"] = points_gdf.geometry.y

# print(">>> Trimming points not within borders...")
# inside_points = points_gdf[points_gdf.within(colo_projected.union_all())]

# print("> Plotting...")
# ax = colo_projected.plot(color="white", edgecolor="black")
# points_gdf.plot(ax=ax, color="red", markersize=1)
# plt.show()

print("> Calculating zones...")
tree = BallTree(airports_gdf[['lat', 'lon']].values, leaf_size=2)
_, points_gdf["iata_index"] = tree.query(points_gdf[["lat", "lon"]], k=1)

merged = points_gdf.merge(airports_gdf, on="iata_index")

lines = [Line2D((x.geometry_x.x, x.geometry_x.y), (x.geometry_y.x, x.geometry_y.y)) for x in merged.itertuples()]

# output.to_file("iata_lookups_by_city.csv", driver="CSV")

print("> Plotting...")
colors = ["green", "orange", "blue", "red"]
styles = ["solid", "dashed", "dotted", "dashdot"]
used = []

regions = {k: {"series": None, "color": None, "style": None} for k in target_airports}

for airport in target_airports:
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
    regions[airport]["series"] = gpd.GeoSeries([line])
    regions[airport]["color"] = color
    regions[airport]["style"] = style
    data = series.to_json()
    with open(f"json/hires/{airport}.json", "w+") as f:
        f.write(data)

fig, ax = plt.subplots(figsize=(30, 30))
colo_border.plot(ax=ax, facecolor="none", edgecolor="black")

for region in regions:
    series: gpd.GeoSeries = regions[region]["series"]
    series.plot(ax=ax, color=regions[region]["color"], linestyle=regions[region]["style"], label=region)
    center = series.centroid
    ax.annotate(text=region, xy=(float(center.values.x[0]), float(center.values.y[0])))

# fig.legend(loc="outside lower left")
plt.show()
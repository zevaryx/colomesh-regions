import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from shapely.geometry import Point
import airportsdata
from sklearn.neighbors import BallTree
import random

state_geo = gpd.read_file("Colorado_City_Point_Locations.geojson").to_crs("EPSG:3857")
state_geo = gpd.GeoDataFrame(state_geo, geometry=gpd.points_from_xy(state_geo.Longitude, state_geo.Latitude), crs="EPSG:3857")

# print(state_geo)

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

tree = BallTree(airports_gdf[['lat', 'lon']].values, leaf_size=2)

_, state_geo['iata_index'] = tree.query(state_geo[['Latitude', 'Longitude']].values, k=1)

# state_geo['iata'] = airports_gdf.iloc[state_geo['iata_index']]['code']
merged = state_geo.merge(airports_gdf, on="iata_index")

print(merged[["name", "county", "code"]].head(50))

# Clean up columns
merged[["name", "county", "code"]].to_csv("iata_lookups_by_city.csv")

lines = [Line2D((x.geometry_x.x, x.geometry_x.y), (x.geometry_y.x, x.geometry_y.y)) for x in merged.itertuples()]

# output.to_file("iata_lookups_by_city.csv", driver="CSV")

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
    with open(f"json/{airport}.json", "w+") as f:
        f.write(data)

fig, ax = plt.subplots(figsize=(30, 30))
state_geo.plot(ax=ax)
#airports_gdf.plot(ax=ax, alpha=0.5, color="red", markersize=(10*1.609)*1000)

for region in regions:
    regions[region]["series"].plot(ax=ax, color=regions[region]["color"], linestyle=regions[region]["style"], label=region)

fig.legend(loc="outside lower left")
plt.show()
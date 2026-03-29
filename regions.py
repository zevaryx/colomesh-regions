from argparse import ArgumentParser
from dataclasses import dataclass

import airportsdata
import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

def flushprint(text: str) -> None:
    print(text, end="", flush=True)

@dataclass
class RegionData:
    series: gpd.GeoSeries
    color: str
    style: str

parser = ArgumentParser()
parser.add_argument("-g", "--geojson", action="store_true", default=False, help="Only generate geojson files")
parser.add_argument("-z", "--zoom", action="store", type=int, default=10, help="Zoom level to use for map tiles")
parser.add_argument("-d", "--dpi", action="store", type=int, default=150, help="DPI to use for figure")

args = parser.parse_args()

print(f"> Generating region info using voronoi data")
flushprint("> Loading border information... ")
state_borders = gpd.read_file("USA_Boundaries_2023.geojson") # This is already in EPSG:4326
colo_border = state_borders.loc[state_borders["STATE_NAME"] == "Colorado"]
print("Done")

flushprint("> Loading airports... ")
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

airports_gdf = gpd.GeoDataFrame(airport_coords, crs="EPSG:4326")

data = airports_gdf.to_json()
with open("json/airports.geojson", "w+") as f:
    f.write(data)
print("Done")

flushprint("> Generating regions... ")

voronoi_polys = airports_gdf.voronoi_polygons(extend_to=colo_border.boundary) # type: ignore

voronoi_gdf = gpd.GeoDataFrame(geometry=voronoi_polys, crs="EPSG:4326").clip(colo_border)

merged = gpd.sjoin(airports_gdf, voronoi_gdf, how="right", predicate="within")

for idx, row in merged.iterrows():
    filename = f"json/{row['code']}.geojson"
    single_poly = gpd.GeoDataFrame([row], crs=voronoi_gdf.crs)
    single_poly.to_file(filename, driver="GeoJSON")

print("Done")
if not args.geojson:
    flushprint(f"> Saving figure to regions_z{args.zoom}.png... ")
    fig, ax = plt.subplots(figsize=(150, 150), dpi=150)

    merged.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=5)
    airports_gdf.plot(ax=ax, markersize=1000)
    
    for idx, row in airports_gdf.iterrows():
        ax.annotate(text=row["code"], xy=[row["lon"], row["lat"] + .05], horizontalalignment="center", fontsize=100)

    ax.axis(False)
    cx.add_basemap(ax, crs=merged.crs, source=cx.providers.OpenStreetMap.Mapnik, zoom=args.zoom)
    plt.savefig(f"regions_z{args.zoom}.png", bbox_inches='tight')
    
    print("Done")
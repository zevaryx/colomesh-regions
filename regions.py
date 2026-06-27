from argparse import ArgumentParser

import airportsdata
import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from pick import pick
from shapely.geometry import Point

from const import STATES

def flushprint(text: str) -> None:
    print(text, end="", flush=True)
    
def get_state() -> str:
    title = "Please pick your state: "
    options = STATES
    state, _ = pick(options, title)
    return str(state)

def get_iatas(state_border: gpd.GeoDataFrame) -> dict[str, airportsdata.Airport]:
    airports = airportsdata.load("IATA")
    state_airports: dict[str, airportsdata.Airport] = {}
    for name, ap in airports.items():
        p = Point(ap['lon'], ap['lat'])
        if state_border.geometry.contains(p).any():
            state_airports[name] = ap
            
    options = list(state_airports.keys())
    title = "Please select all airports you want to use: "
    airports = [x[0] for x in pick(options, title, multiselect=True)]
    selected_airports = {k: v for k, v in state_airports.items() if k in airports}
    return selected_airports
    
def generate_regions():
    print(f"> Generating region info using voronoi data")
    flushprint("> Loading border information... ")
    state_borders = gpd.read_file("USA_Boundaries_2023.geojson") # This is already in EPSG:4326
    state_name = get_state()
    state_border = state_borders.loc[state_borders["STATE_NAME"] == state_name]
    print("Done")

    flushprint("> Loading airports... ")
    target_airports = get_iatas(state_border)
    airport_coords = []

    idx = 0
    for code, ap in target_airports.items():
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
    if not os.path.exists(f"json/{state_name}"):
        os.mkdir(f"json/{state_name}")
    with open(f"json/{state_name}/airports.geojson", "w+") as f:
        f.write(data)
    print("Done")

    flushprint("> Generating regions... ")

    voronoi_polys = airports_gdf.voronoi_polygons(extend_to=state_border.boundary) # type: ignore

    voronoi_gdf = gpd.GeoDataFrame(geometry=voronoi_polys, crs="EPSG:4326").clip(state_border)

    merged = gpd.sjoin(airports_gdf, voronoi_gdf, how="right", predicate="within")

    merged.to_file(f"json/{state_name}/merged.geojson")

    for idx, row in merged.iterrows():
        filename = f"json/{state_name}/{row['code']}.geojson"
        single_poly = gpd.GeoDataFrame([row], crs=voronoi_gdf.crs)
        single_poly.to_file(filename, driver="GeoJSON")

    print("Done")
    return merged, airports_gdf, state_name

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-g", "--geojson", action="store_true", default=False, help="Only generate geojson files (no png of regions)")
    parser.add_argument("-z", "--zoom", action="store", type=int, default=10, help="Zoom level to use for map tiles")
    parser.add_argument("-d", "--dpi", action="store", type=int, default=100, help="DPI to use for figure")

    args = parser.parse_args()

    merged, airports_gdf, state_name = generate_regions()

    if not args.geojson:
        flushprint(f"> Saving figure to regions_z{args.zoom}.png... ")
        fig, ax = plt.subplots(figsize=(150, 150), dpi=150)

        merged.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=5)
        airports_gdf.plot(ax=ax, markersize=1000)
        
        for idx, row in airports_gdf.iterrows():
            ax.annotate(text=row["code"], xy=[row["lon"], row["lat"] + .05], horizontalalignment="center", fontsize=100)

        ax.axis(False)
        cx.add_basemap(ax, crs=merged.crs, source=cx.providers.OpenStreetMap.Mapnik, zoom=args.zoom)
        plt.savefig(f"{state_name}_regions_z{args.zoom}.png", bbox_inches='tight')
        
        print("Done")
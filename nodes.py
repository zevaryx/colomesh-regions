import re
from dataclasses import dataclass

import geopandas as gpd
import requests
from shapely.geometry import Point

from regions import generate_regions

@dataclass
class Suggestion:
    region: str
    prefix: str

name_validator = re.compile(r"^(?P<region>[A-Za-z]{3})-(?P<city>[A-Za-z0-9]{1,})(?:-(?P<landmark>[A-Za-z0-9+.|_]{1,}))?-(?P<type>[A-Z]{2,})-(?P<prefix>[A-Fa-f0-9]{1,})$")
url = "https://raw.githubusercontent.com/Colorado-Mesh/coloradomesh_python/refs/heads/master/data/meshcore/nodes/nodes.json"

valid_types = ["RC", "RD", "RE", "RM", "TS", "TM", "TR"]

r = requests.get(url)
r.raise_for_status()
data = r.json()

valid_nodes = []
for node in data:
    if node["latitude"] and node["longitude"] and node["node_type"] in [2, 3]:
        valid_nodes.append({
            "name": node["name"],
            "public_key": node["public_key"],
            "geometry": Point(node["longitude"], node["latitude"]),
            "node_type": "Repeater" if node["node_type"] == 2 else "Room Server",
        })

nodes_df = gpd.GeoDataFrame(valid_nodes, crs="EPSG:4326")

nodes_df.to_file("json/nodes.geojson", driver="GeoJSON")

regions, airports = generate_regions()

cities = gpd.read_file("Colorado_City_Point_Locations.geojson")

rename_suggestion = {"full_rename": [], "other": []}

for _, node in nodes_df.iterrows():
    suggestion = f"{node['name']} :"
    has_suggestion = False
    nv = name_validator.match(node["name"])
    if not nv:
        rename_suggestion["full_rename"].append(f"{node["name"]} : Full rename")
        continue
    apparent_region = nv.group("region")
    for _, region in regions.iterrows():
        if region["geometry"].contains(node["geometry"]):
            if region["code"] != nv.group("region"):
                has_suggestion = True
                suggestion += f" fix region: {region["code"]},"
            break
    if nv.group("prefix").upper() != node["public_key"][:4].upper():
        has_suggestion = True
        suggestion += f" fix prefix: {node["public_key"][:4].upper()},"
    if nv.group("type").upper() not in valid_types:
        has_suggestion = True
        suggestion += f" fix type: {nv.group("type")} is invalid"
    if has_suggestion:
        rename_suggestion["other"].append(suggestion.rstrip(","))
    
print("The following nodes need a full rename to match the naming standard:")
print("\n".join(rename_suggestion["full_rename"]))

print("\nThe following nodes need the recommended adjustments:")
print("\n".join(rename_suggestion["other"]))
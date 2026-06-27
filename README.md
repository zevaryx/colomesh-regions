# Colorado Mesh Region Generator

Generate regions for any US state using Voronoi noise

## Prerequisites

- Python 3.11 or higher
- [`uv`](https://docs.astral.sh/uv/getting-started/)

## Running
```bash
# Install virtual environment
uv sync

# Run regions.py
uv run python regions.py
```

## Usage

```
usage: regions.py [-h] [-g] [-z ZOOM] [-d DPI]

options:
  -h, --help       show this help message and exit
  -g, --geojson    Only generate geojson files (no png of regions)
  -z, --zoom ZOOM  Zoom level to use for map tiles
  -d, --dpi DPI    DPI to use for figure
  ```
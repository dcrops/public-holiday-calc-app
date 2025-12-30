from __future__ import annotations

from pathlib import Path
import geopandas as gpd

GPKG_PATH = Path("data/ASGS_Ed3_Non_ABS_Structures_GDA2020_updated_2025.gpkg")
LGA_LAYER = "LGA_2025_AUST_GDA2020"
LGA_NAME_COL = "LGA_NAME_2025"
STATE_NAME_COL = "STATE_NAME_2021"

OUT_PATH = Path("data/lga_2025_simplified.geojson")

STATE_MAP = {
    "Victoria": "VIC",
    "New South Wales": "NSW",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Western Australia": "WA",
    "Tasmania": "TAS",
    "Northern Territory": "NT",
    "Australian Capital Territory": "ACT",
}

def main() -> None:
    gdf = gpd.read_file(GPKG_PATH, layer=LGA_LAYER)

    gdf = gdf[[STATE_NAME_COL, LGA_NAME_COL, "geometry"]].copy()
    gdf["state"] = gdf[STATE_NAME_COL].map(STATE_MAP).fillna(gdf[STATE_NAME_COL])

    gdf = gdf.to_crs("EPSG:4326")

    # simplify geometries (tune tolerance later if needed)
    gdf["geometry"] = gdf["geometry"].simplify(
        tolerance=0.001,
        preserve_topology=True
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    gdf[["state", LGA_NAME_COL, "geometry"]].to_file(
        OUT_PATH,
        driver="GeoJSON"
    )

    print(f"Wrote {OUT_PATH} ({len(gdf)} LGAs)")

if __name__ == "__main__":
    main()

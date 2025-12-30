from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point

ARTIFACT_PATH = Path("data/lga_2025_simplified.geojson")
LGA_NAME_COL = "LGA_NAME_2025"

# Module-level cache so we only load once per app process
_LGA_GDF: gpd.GeoDataFrame | None = None


def _load_lgas() -> gpd.GeoDataFrame:
    """
    Load AU LGA polygons (simplified artifact) once and keep them in memory.
    """
    global _LGA_GDF

    if _LGA_GDF is None:
        if not ARTIFACT_PATH.exists():
            raise FileNotFoundError(
                f"Missing LGA artifact: {ARTIFACT_PATH}. "
                f"Run scripts/build_lga_artifact.py to generate it."
            )

        gdf = gpd.read_file(ARTIFACT_PATH)

        # Ensure WGS84 (lat/lon) for contains() checks
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        else:
            gdf = gdf.to_crs("EPSG:4326")

        _LGA_GDF = gdf

    return _LGA_GDF


def lga_from_latlon(lat: float, lon: float) -> str | None:
    """
    Return the LGA name for a given latitude/longitude.
    """
    gdf = _load_lgas()

    point = Point(lon, lat)  # shapely uses (x, y) == (lon, lat)
    match = gdf[gdf.contains(point)]

    if match.empty:
        return None

    return str(match.iloc[0][LGA_NAME_COL])

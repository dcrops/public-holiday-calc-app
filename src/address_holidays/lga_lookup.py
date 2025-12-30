from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point

GPKG_PATH = "data/ASGS_Ed3_Non_ABS_Structures_GDA2020_updated_2025.gpkg"
LGA_LAYER = "LGA_2025_AUST_GDA2020"
LGA_NAME_COL = "LGA_NAME_2025"
STATE_NAME_COL = "STATE_NAME_2021"  # handy later


# Module-level cache so we only load once per app process
_LGA_VIC_GDF: gpd.GeoDataFrame | None = None


def _load_vic_lgas() -> gpd.GeoDataFrame:
    """
    Load VIC LGA polygons once and keep them in memory.
    """
    global _LGA_VIC_GDF

    if _LGA_VIC_GDF is None:
        gdf = gpd.read_file(GPKG_PATH, layer=LGA_LAYER)

        # Filter to Victoria only (faster lookups)
        vic = gdf[gdf[STATE_NAME_COL] == "Victoria"].copy()

        # Optional speed-up: spatial index gets built automatically if available
        _LGA_VIC_GDF = vic

    return _LGA_VIC_GDF


def lga_from_latlon(lat: float, lon: float) -> str | None:
    """
    Return the VIC LGA name for a given latitude/longitude.
    """
    gdf = _load_vic_lgas()

    point = Point(lon, lat)  # shapely uses (x, y) == (lon, lat)
    match = gdf[gdf.contains(point)]

    if match.empty:
        return None

    return str(match.iloc[0][LGA_NAME_COL])

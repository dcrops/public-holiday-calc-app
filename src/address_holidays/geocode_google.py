from __future__ import annotations

import os
import re
import requests
from dotenv import load_dotenv, find_dotenv

from .geocode_cache import get_cached, set_cached

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


load_dotenv(find_dotenv(), override=False)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def _simplify_address_for_fallback(address: str) -> str:
    """
    Remove likely street-number + street-name parts and keep suburb/state/postcode-ish tokens.
    This is a best-effort fallback when full address geocode returns ZERO_RESULTS.
    """
    a = address.strip()

    # If user typed comma-separated parts, keep the last 1–2 parts (often suburb/state/postcode)
    parts = [p.strip() for p in a.split(",") if p.strip()]
    if len(parts) >= 2:
        return ", ".join(parts[-2:])  # e.g. "Brunswick VIC 3056"

    # Otherwise, strip a leading street number and common street suffix words
    a = re.sub(r"^\s*\d+\s+", "", a)  # drop leading house number
    a = re.sub(r"\b(st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|ct|court|ln|lane|pde|parade)\b\.?", "", a, flags=re.I)
    a = " ".join(a.split())
    return a


def geocode_address(address: str) -> dict:
    cache_key = " ".join(address.lower().split())

    cached = get_cached(cache_key)
    if cached:
        return cached

    def _call_geocode(query: str) -> dict:
        params = {"address": query, "key": GOOGLE_MAPS_API_KEY}
        resp = requests.get(GEOCODE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")

        if status == "ZERO_RESULTS":
            raise ValueError(
                "Address not found. Try adding suburb + state/postcode (e.g. 'Brunswick VIC 3056') "
                "or check spelling."
            )

        if status != "OK":
            raise ValueError(f"Geocoding failed: {status}")


        result = data["results"][0]
        location = result["geometry"]["location"]

        components = {}
        for c in result.get("address_components", []):
            for t in c.get("types", []):
                components[t] = c.get("long_name")

        state = components.get("administrative_area_level_1")
        postcode = components.get("postal_code")
        locality = (
            components.get("locality")
            or components.get("postal_town")
            or components.get("administrative_area_level_2")
        )

        # Normalise state code if you already do this
        state_code = STATE_MAP.get(state, state)

        return {
            "formatted_address": result.get("formatted_address"),
            "lat": location.get("lat"),
            "lon": location.get("lng"),
            "state": state_code,
            "postcode": postcode,
            "locality": locality,
            "geocode_query_used": query,          # <— new (debug)
            "is_fallback_match": query != address # <— new (flag)
        }

    try:
        result_obj = _call_geocode(address)
    except ValueError as e:
        # Only retry if the failure is ZERO_RESULTS
        if "ZERO_RESULTS" not in str(e):
            raise

        fallback_query = _simplify_address_for_fallback(address)
        if fallback_query.strip() and fallback_query.strip() != address.strip():
            result_obj = _call_geocode(fallback_query)
        else:
            raise

    set_cached(cache_key, result_obj)
    return result_obj


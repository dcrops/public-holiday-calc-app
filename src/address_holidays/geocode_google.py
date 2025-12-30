from __future__ import annotations

import os
import requests
from dotenv import load_dotenv

from .geocode_cache import get_cached, set_cached

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode_address(address: str) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY not set")

    if not address or not address.strip():
        raise ValueError("Address is required")


    cache_key = " ".join(address.lower().split())  # normalize whitespace + lowercase
    cached = get_cached(cache_key)
    if cached:
        return cached

    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY,
        "region": "au",
    }


    resp = requests.get(GEOCODE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data["status"] != "OK":
        raise ValueError(f"Geocoding failed: {data['status']}")

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
        or components.get("sublocality")
        or components.get("sublocality_level_1")
        or components.get("administrative_area_level_2")  # sometimes “Merri-bek City”
    )


    # Normalize state to VIC / NSW / QLD if needed
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

    state = components.get("administrative_area_level_1")
    state_code = STATE_MAP.get(state, state)


    result_obj = {
        "formatted_address": result["formatted_address"],
        "lat": location["lat"],
        "lon": location["lng"],
        "state": state_code,
        "postcode": components.get("postal_code"),
        "locality": locality,
    }


    set_cached(cache_key, result_obj)
    return result_obj

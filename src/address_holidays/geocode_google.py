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
    Best-effort fallback when full address geocode returns ZERO_RESULTS.
    """
    a = address.strip()

    parts = [p.strip() for p in a.split(",") if p.strip()]
    if len(parts) >= 2:
        return ", ".join(parts[-2:])  # e.g. "Brunswick VIC 3056"

    a = re.sub(r"^\s*\d+\s+", "", a)  # drop leading house number
    a = re.sub(
        r"\b(st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|ct|court|ln|lane|pde|parade)\b\.?",
        "",
        a,
        flags=re.I,
    )
    a = " ".join(a.split())
    return a


def _looks_like_street_address(query: str) -> bool:
    """
    True if the user likely intended a street-level address.
    IMPORTANT: postcodes contain digits too, so digits alone isn't enough.
    """
    q = f" {query.lower()} "

    street_tokens = [
        " street", " st ", " road", " rd ",
        " avenue", " ave ", " boulevard", " blvd",
        " lane", " ln ", " drive", " dr ",
        " court", " ct ", " parade", " pde",
    ]

    has_street_word = any(tok in q for tok in street_tokens)
    has_number = any(ch.isdigit() for ch in q)

    return has_number and has_street_word


def _is_street_level_result(result: dict) -> bool:
    """True only when Google likely resolved a real street-level address."""
    if result.get("partial_match") is True:
        return False

    types = set(result.get("types", []))

    # Strong street-level indicators
    if types & {"street_address", "premise", "subpremise"}:
        return True

    # If it's only locality/postcode/admin-level, it's not street-level
    if types & {
        "postal_code",
        "locality",
        "administrative_area_level_1",
        "administrative_area_level_2",
    }:
        return False

    # Fallback: check address_components include BOTH route and street_number
    component_types = set()
    for c in result.get("address_components", []):
        component_types.update(c.get("types", []))

    return "route" in component_types and "street_number" in component_types


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

        # Only enforce street-level quality when the user intended a street-level address.
        # Allow suburb/postcode-only queries to resolve (they'll be lower confidence downstream).
        if _looks_like_street_address(query) and not _is_street_level_result(result):
            raise ValueError(
                "Address not found. Try adding suburb + state/postcode (e.g. 'Brunswick VIC 3056') "
                "or check spelling."
            )

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

        state_code = STATE_MAP.get(state, state)

        return {
            "formatted_address": result.get("formatted_address"),
            "lat": location.get("lat"),
            "lon": location.get("lng"),
            "state": state_code,
            "postcode": postcode,
            "locality": locality,
            "geocode_query_used": query,
            "is_fallback_match": query.strip() != address.strip(),
            # Optional: pass through quality signal if you want it later
            "location_type": result.get("geometry", {}).get("location_type"),
        }

    try:
        result_obj = _call_geocode(address)
    except ValueError as e:
        # Only retry if the failure came from ZERO_RESULTS
        # (Street-level rejection should NOT auto-fallback silently)
        if "ZERO_RESULTS" not in str(e):
            raise

        fallback_query = _simplify_address_for_fallback(address)
        if fallback_query.strip() and fallback_query.strip() != address.strip():
            result_obj = _call_geocode(fallback_query)
        else:
            raise

    set_cached(cache_key, result_obj)
    return result_obj

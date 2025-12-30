from __future__ import annotations
from datetime import date

from .geocode_google import geocode_address
from .lga_lookup import lga_from_latlon
from .holidays_au import get_vic_public_holidays

from src.address_holidays.regional_rules import (
    load_regional_rules,
    match_regional_rules,
    merge_holidays,
)

from src.address_holidays.holidays_au import get_au_public_holidays, filter_holidays_for_subdivision


def lookup_address_info(
    address: str,
    year: int,
    start: date | None = None,
    end: date | None = None,
):
    geo = geocode_address(address)
    lga = lga_from_latlon(lat=geo["lat"], lon=geo["lon"])

    # 1) Base holidays (still VIC-only for now)
    all_holidays = get_au_public_holidays(year)
    state = (geo.get("state") or "").upper()
    holidays = filter_holidays_for_subdivision(all_holidays, state)


    # Normalise base holidays (optional but nice)
    for h in holidays:
        h.setdefault("scope", "FULL_DAY")
        h.setdefault("is_regional", False)
        h.setdefault("source", "Nager.Date")
        h.setdefault("applies_to", "ALL")



    # 2) Apply regional holiday rules
    rules = load_regional_rules(year)

    matched_rules = match_regional_rules(
        rules,
        state=geo.get("state"),
        lga=lga,
        postcode=geo.get("postcode"),
        locality=geo.get("locality"),
        include_restricted=False,
    )

    holidays = merge_holidays(holidays, matched_rules)

     # 3) Pay-period filtering (now includes regional holidays)
    if start and end:
        holidays_in_period = [
            h for h in holidays
            if start <= date.fromisoformat(h["date"]) <= end
        ]
    else:
        holidays_in_period = holidays


    return {
        "input_address": address,
        "formatted_address": geo["formatted_address"],  # 👈 must be this exact key
        "state": geo.get("state"),
        "postcode": geo.get("postcode"),
        "locality": geo.get("locality"),   # ← add this too
        "lga": lga,
        "holidays": holidays,
        "holiday_count": len(holidays),
        "pay_period": {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
        "holidays_in_period": holidays_in_period,
        "holiday_count_in_period": len(holidays_in_period) if holidays_in_period is not None else None,
        "regional_holidays_applied": [
            f"{r.date.isoformat()} - {r.name}" for r in matched_rules
        ],

    }


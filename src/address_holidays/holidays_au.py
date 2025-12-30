from __future__ import annotations

import requests


NAGER_BASE = "https://date.nager.at/api/v3"


def get_au_public_holidays(year: int) -> list[dict]:
    """
    Return all Australian public holidays for the given year.
    """
    url = f"{NAGER_BASE}/PublicHolidays/{year}/AU"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def filter_holidays_for_subdivision(holidays: list[dict], subdivision_code: str) -> list[dict]:
    out = []
    target = f"AU-{subdivision_code}"

    for h in holidays:
        counties = h.get("counties") or []
        is_global = bool(h.get("global"))

        if is_global or (target in counties):
            out.append(h)

    return out



def get_vic_public_holidays(year: int) -> list[dict]:
    """
    Return VIC public holidays for the given year as a tidy list.
    """
    holidays = get_au_public_holidays(year)
    vic = filter_holidays_for_subdivision(holidays, "VIC")

    # Tidy + sort
    tidy = [{"date": h["date"], "name": h.get("name") or h.get("localName")} for h in vic]
    tidy.sort(key=lambda x: x["date"])
    return tidy

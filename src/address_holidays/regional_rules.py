from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path


@dataclass(frozen=True)
class RegionalHolidayRule:
    date: date
    name: str
    state: str
    match_type: str      # LGA | POSTCODE | LOCALITY
    match_value: str
    scope: str           # FULL_DAY | HALF_DAY_AM | HALF_DAY_PM
    applies_to: str      # ALL | PUBLIC_SERVICE_ONLY | BANKING_ONLY
    source: str
    notes: str


def _data_dir() -> Path:
    """
    Returns the project's /data directory.
    Assumes this file is: <root>/src/address_holidays/regional_rules.py
    """
    return Path(__file__).resolve().parents[2] / "data"


def load_regional_rules(year: int) -> list[RegionalHolidayRule]:
    """
    Load curated regional holiday rules for a given year from:
      <root>/data/regional_holidays_{year}.csv

    Safe behavior:
    - If the file doesn't exist, returns [].
    - If the file exists but is empty (header only), returns [].
    """
    path = _data_dir() / f"regional_holidays_{year}.csv"
    if not path.exists():
        return []

    rules: list[RegionalHolidayRule] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip completely blank lines (sometimes happen in CSV editors)
            if not row or not row.get("date"):
                continue

            rules.append(
                RegionalHolidayRule(
                    date=datetime.strptime(row["date"].strip(), "%Y-%m-%d").date(),
                    name=row["name"].strip(),
                    state=row["state"].strip().upper(),
                    match_type=row["match_type"].strip().upper(),
                    match_value=row["match_value"].strip(),
                    scope=row["scope"].strip().upper(),
                    applies_to=row["applies_to"].strip().upper(),
                    source=row.get("source", "").strip(),
                    notes=row.get("notes", "").strip(),
                )
            )
    return rules


def _norm(s: str | None) -> str:
    return " ".join((s or "").strip().lower().split())

def match_regional_rules(
    rules: list[RegionalHolidayRule],
    *,
    state: str,
    lga: str | None,
    postcode: str | None,
    locality: str | None,
    include_restricted: bool = False,
) -> list[RegionalHolidayRule]:
    state_n = _norm(state).upper()
    lga_n = _norm(lga)
    postcode_n = _norm(postcode)
    locality_n = _norm(locality)

    matched: list[RegionalHolidayRule] = []
    for r in rules:
        if _norm(r.state).upper() != state_n:
            continue

        if (not include_restricted) and (r.applies_to != "ALL"):
            continue

        mt = r.match_type.upper()
        mv = _norm(r.match_value)

        if mt == "LGA" and mv == lga_n:
            matched.append(r)
        elif mt == "POSTCODE" and mv == postcode_n:
            matched.append(r)
        elif mt == "LOCALITY" and mv == locality_n:
            matched.append(r)

    return matched


def merge_holidays(
    base_holidays: list[dict],
    regional_rules: list[RegionalHolidayRule],
) -> list[dict]:
    """
    Merge base holiday dicts with regional rule holidays.
    Your base_holidays can be whatever you already use; we just add rows in same shape.
    Expected dict keys (recommended):
      - date (YYYY-MM-DD)
      - name
      - scope (FULL_DAY/HALF_DAY_AM/HALF_DAY_PM)
      - source (optional)
      - is_regional (bool)
    """
    # de-dupe by (date, name)
    seen = {(h.get("date"), h.get("name")) for h in base_holidays}

    out = list(base_holidays)
    for r in regional_rules:
        key = (r.date.isoformat(), r.name)
        if key in seen:
            continue
        out.append(
            {
                "date": r.date.isoformat(),
                "name": r.name,
                "scope": r.scope,
                "source": r.source,
                "is_regional": True,
                "applies_to": r.applies_to,
                "notes": r.notes,
            }
        )
        seen.add(key)

    # optional: sort by date then name
    out.sort(key=lambda x: (x.get("date", ""), x.get("name", "")))
    return out



if __name__ == "__main__":
    rules = load_regional_rules(2025)
    print(f"Loaded {len(rules)} regional rules")

from __future__ import annotations

import csv
import warnings
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
    - If headers are invalid, returns [] with a warning.
    - Invalid rows are skipped with warnings.
    """
    path = _data_dir() / f"regional_holidays_{year}.csv"
    if not path.exists():
        return []

    rules: list[RegionalHolidayRule] = []

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # --- header validation (warnings only) ---
        required_cols = {
            "date",
            "name",
            "state",
            "match_type",
            "match_value",
            "scope",
            "applies_to",
        }

        fieldnames = set(reader.fieldnames or [])
        missing = required_cols - fieldnames
        if missing:
            warnings.warn(
                f"[regional_rules] {path.name}: missing required columns "
                f"{sorted(missing)}. No regional rules loaded.",
                RuntimeWarning,
            )
            return []

        allowed_match_types = {"LGA", "POSTCODE", "LOCALITY"}
        allowed_scopes = {"FULL_DAY", "HALF_DAY_AM", "HALF_DAY_PM"}
        allowed_applies_to = {"ALL", "PUBLIC_SERVICE_ONLY", "BANKING_ONLY"}
        allowed_states = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}

        for row in reader:
            # Skip completely blank lines
            if not row or not row.get("date"):
                continue

            row_num = reader.line_num

            # Extract & normalize raw values
            raw_date = (row.get("date") or "").strip()
            raw_name = (row.get("name") or "").strip()
            raw_state = (row.get("state") or "").strip().upper()
            raw_match_type = (row.get("match_type") or "").strip().upper()
            raw_match_value = (row.get("match_value") or "").strip()
            raw_scope = (row.get("scope") or "").strip().upper()
            raw_applies_to = (row.get("applies_to") or "").strip().upper()

            # Required values present?
            if not all([raw_date, raw_name, raw_state, raw_match_type, raw_match_value]):
                warnings.warn(
                    f"[regional_rules] {path.name}:{row_num}: missing required values. "
                    "Row skipped.",
                    RuntimeWarning,
                )
                continue

            # Validate enums
            if raw_match_type not in allowed_match_types:
                warnings.warn(
                    f"[regional_rules] {path.name}:{row_num}: invalid match_type "
                    f"{raw_match_type!r}. Row skipped.",
                    RuntimeWarning,
                )
                continue

            if raw_scope and raw_scope not in allowed_scopes:
                warnings.warn(
                    f"[regional_rules] {path.name}:{row_num}: invalid scope "
                    f"{raw_scope!r}. Row skipped.",
                    RuntimeWarning,
                )
                continue

            if raw_applies_to and raw_applies_to not in allowed_applies_to:
                warnings.warn(
                    f"[regional_rules] {path.name}:{row_num}: invalid applies_to "
                    f"{raw_applies_to!r}. Row skipped.",
                    RuntimeWarning,
                )
                continue

            if raw_state not in allowed_states:
                warnings.warn(
                    f"[regional_rules] {path.name}:{row_num}: suspicious state "
                    f"{raw_state!r}.",
                    RuntimeWarning,
                )

            # Locality hygiene warning (warn only)
            if raw_match_type == "LOCALITY":
                mv_lower = raw_match_value.lower()
                if any(tok in mv_lower for tok in ("city of", "shire of", "council", "municipality")):
                    warnings.warn(
                        f"[regional_rules] {path.name}:{row_num}: suspicious LOCALITY "
                        f"match_value {raw_match_value!r}.",
                        RuntimeWarning,
                    )

            # Parse date
            try:
                parsed_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except ValueError:
                warnings.warn(
                    f"[regional_rules] {path.name}:{row_num}: invalid date "
                    f"{raw_date!r}. Expected YYYY-MM-DD. Row skipped.",
                    RuntimeWarning,
                )
                continue

            rules.append(
                RegionalHolidayRule(
                    date=parsed_date,
                    name=raw_name,
                    state=raw_state,
                    match_type=raw_match_type,
                    match_value=raw_match_value,
                    scope=raw_scope or "FULL_DAY",
                    applies_to=raw_applies_to or "ALL",
                    source=(row.get("source") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
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

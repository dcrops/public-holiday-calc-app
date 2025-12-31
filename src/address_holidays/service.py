from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, List, Optional

from .geocode_google import geocode_address
from .lga_lookup import lga_from_latlon

from src.address_holidays.regional_rules import (
    load_regional_rules,
    match_regional_rules,
    merge_holidays,
)

from src.address_holidays.holidays_au import (
    get_au_public_holidays,
    filter_holidays_for_subdivision,
)

# ----------------------------
# Status codes (Step 1)
# ----------------------------
STATUS_OK = "OK"
STATUS_LOW_CONFIDENCE = "LOW_CONFIDENCE"
STATUS_AMBIGUOUS_LGA = "AMBIGUOUS_LGA"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_RULES_MISSING = "RULES_MISSING"
STATUS_UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
STATUS_ERROR = "ERROR"


def _confidence_from_geocode_quality(q: str | None) -> float:
    """Coarse confidence mapping; good enough for v1 audit trail."""
    if not q:
        return 0.5
    q = q.upper()
    if q == "ROOFTOP":
        return 1.0
    if q == "RANGE_INTERPOLATED":
        return 0.8
    if q in {"GEOMETRIC_CENTER", "GEOMETRIC_CENTRE"}:
        return 0.6
    if q == "APPROXIMATE":
        return 0.4
    return 0.5


def _init_audit(address: str) -> Dict[str, Any]:
    return {
        "status": STATUS_OK,
        "manual_review": False,
        "confidence": 1.0,
        "audit_message": "",
        "geocode_provider": "google",   # v1: your app uses Google; later privacy mode can set this
        "geocode_quality": None,
        "lga_resolution_method": None,
        "rules_applied": [],
        "replacement_applied": None,
        # extra context (useful for debugging/support)
        "input_address": address,
        "error": None,
    }


def _finalise_audit(audit: Dict[str, Any]) -> None:
    audit["manual_review"] = audit.get("status") != STATUS_OK
    # confidence should always be bounded
    try:
        audit["confidence"] = max(0.0, min(1.0, float(audit.get("confidence", 0.0))))
    except Exception:
        audit["confidence"] = 0.0


def lookup_address_info(
    address: str,
    year: int,
    start: date | None = None,
    end: date | None = None,
):
    audit = _init_audit(address)

    geo: Dict[str, Any] = {}
    lga: Optional[str] = None
    holidays: List[Dict[str, Any]] = []
    holidays_in_period: List[Dict[str, Any]] = []
    matched_rules: List[Any] = []

    try:
        # ----------------------------
        # 1) Geocode
        # ----------------------------
        geo = geocode_address(address) or {}

        # Common patterns: either raises, or returns fields like {"ok": False, "error": "..."}
        if geo.get("ok") is False or geo.get("status") in {"ZERO_RESULTS", "NOT_FOUND"}:
            audit["status"] = STATUS_NOT_FOUND
            audit["confidence"] = 0.0
            audit["audit_message"] = geo.get("error") or "Address could not be resolved."
            _finalise_audit(audit)

            return {
                "input_address": address,
                "formatted_address": geo.get("formatted_address"),
                "state": geo.get("state"),
                "postcode": geo.get("postcode"),
                "locality": geo.get("locality"),
                "lga": None,
                "holidays": [],
                "holiday_count": 0,
                "pay_period": {
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                },
                "holidays_in_period": [],
                "holiday_count_in_period": 0,
                "regional_holidays_applied": [],
                # audit (flat + json)
                **audit,
                "audit_json": json.dumps(audit, ensure_ascii=False),
            }

        # geocode quality (try a few likely keys)
        geocode_quality = (
            geo.get("location_type")
            or geo.get("geocode_quality")
            or geo.get("quality")
            or None
        )
        audit["geocode_quality"] = geocode_quality
        audit["confidence"] = _confidence_from_geocode_quality(geocode_quality)

        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is None or lon is None:
            audit["status"] = STATUS_NOT_FOUND
            audit["confidence"] = 0.0
            audit["audit_message"] = "Geocoding returned no coordinates."
            _finalise_audit(audit)
            return {
                "input_address": address,
                "formatted_address": geo.get("formatted_address"),
                "state": geo.get("state"),
                "postcode": geo.get("postcode"),
                "locality": geo.get("locality"),
                "lga": None,
                "holidays": [],
                "holiday_count": 0,
                "pay_period": {
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                },
                "holidays_in_period": [],
                "holiday_count_in_period": 0,
                "regional_holidays_applied": [],
                **audit,
                "audit_json": json.dumps(audit, ensure_ascii=False),
            }

        # ----------------------------
        # 2) LGA lookup (lat/lon → polygon)
        # ----------------------------
        lga = lga_from_latlon(lat=lat, lon=lon)
        audit["lga_resolution_method"] = "polygon"

        if not lga:
            # If geocode was approximate-ish, flag low confidence rather than hard fail
            if audit["confidence"] < 0.7:
                audit["status"] = STATUS_AMBIGUOUS_LGA
                audit["audit_message"] = "Could not deterministically resolve LGA from coordinates (low confidence geocode)."
            else:
                audit["status"] = STATUS_AMBIGUOUS_LGA
                audit["audit_message"] = "Could not deterministically resolve LGA from coordinates."
            _finalise_audit(audit)

            return {
                "input_address": address,
                "formatted_address": geo.get("formatted_address"),
                "state": geo.get("state"),
                "postcode": geo.get("postcode"),
                "locality": geo.get("locality"),
                "lga": None,
                "holidays": [],
                "holiday_count": 0,
                "pay_period": {
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                },
                "holidays_in_period": [],
                "holiday_count_in_period": 0,
                "regional_holidays_applied": [],
                **audit,
                "audit_json": json.dumps(audit, ensure_ascii=False),
            }

        # ----------------------------
        # 3) Base holidays
        # ----------------------------
        all_holidays = get_au_public_holidays(year)
        state = (geo.get("state") or "").upper()
        holidays = filter_holidays_for_subdivision(all_holidays, state)

        # Normalise base holidays (optional but nice)
        for h in holidays:
            h.setdefault("scope", "FULL_DAY")
            h.setdefault("is_regional", False)
            h.setdefault("source", "Nager.Date")
            h.setdefault("applies_to", "ALL")

        # ----------------------------
        # 4) Apply regional holiday rules
        # ----------------------------
        rules = load_regional_rules(year)

        matched_rules = match_regional_rules(
            rules,
            state=geo.get("state"),
            lga=lga,
            postcode=geo.get("postcode"),
            locality=geo.get("locality"),
            include_restricted=False,
        )

        # Track rule ids/names applied for audit trail
        applied = []
        for r in matched_rules:
            # try common attributes; fall back to date-name string
            rule_id = getattr(r, "rule_id", None) or getattr(r, "id", None)
            if rule_id:
                applied.append(str(rule_id))
            else:
                r_date = getattr(r, "date", None)
                r_name = getattr(r, "name", None)
                if r_date and r_name:
                    applied.append(f"{r_date.isoformat()}:{r_name}")
        audit["rules_applied"] = applied

        holidays = merge_holidays(holidays, matched_rules)

        # If we only have approximate geocode quality, downgrade outcome to LOW_CONFIDENCE
        if audit["confidence"] < 0.7 and audit["status"] == STATUS_OK:
            audit["status"] = STATUS_LOW_CONFIDENCE

        # If somehow no holidays matched after filtering (rare), flag it
        if not holidays:
            audit["status"] = STATUS_RULES_MISSING
            audit["confidence"] = min(audit["confidence"], 0.6)

        # ----------------------------
        # 5) Pay-period filtering
        # ----------------------------
        if start and end:
            holidays_in_period = [
                h for h in holidays
                if start <= date.fromisoformat(h["date"]) <= end
            ]
        else:
            holidays_in_period = holidays

        # ----------------------------
        # 6) Final audit message (human sentence)
        # ----------------------------
        if audit["status"] == STATUS_OK:
            audit["audit_message"] = "Resolved via geocode coordinates and LGA polygon match; holidays calculated with regional rules."
        elif audit["status"] == STATUS_LOW_CONFIDENCE:
            audit["audit_message"] = "Result generated but geocode confidence is low; manual review recommended."
        elif audit["status"] == STATUS_RULES_MISSING:
            audit["audit_message"] = "No holidays matched for the derived state/subdivision; manual review recommended."
        # other statuses already set earlier

    except ValueError as e:
        msg = str(e).lower()

        # Map known user-facing geocode failures to NOT_FOUND
        if "address not found" in msg or "zero_results" in msg:
            audit["status"] = STATUS_NOT_FOUND
            audit["confidence"] = 0.0
            audit["audit_message"] = str(e)
        else:
            # Other ValueErrors: treat as upstream issue (e.g., API issues)
            audit["status"] = STATUS_UPSTREAM_UNAVAILABLE
            audit["confidence"] = 0.0
            audit["audit_message"] = str(e)

        audit["error"] = f"{type(e).__name__}: {e}"
        _finalise_audit(audit)

        return {
            "input_address": address,
            "formatted_address": geo.get("formatted_address"),
            "state": geo.get("state"),
            "postcode": geo.get("postcode"),
            "locality": geo.get("locality"),
            "lga": None,
            "holidays": [],
            "holiday_count": 0,
            "pay_period": {
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
            "holidays_in_period": [],
            "holiday_count_in_period": 0,
            "regional_holidays_applied": [],
            **audit,
            "audit_json": json.dumps(audit, ensure_ascii=False),
        }

    
    except Exception as e:
        # Upstream unavailability vs unexpected error:
        # If you want to get fancy later, detect requests/timeouts here.
        audit["status"] = STATUS_ERROR
        audit["confidence"] = 0.0
        audit["error"] = f"{type(e).__name__}: {e}"
        audit["audit_message"] = "An unexpected error occurred while processing this address."
        _finalise_audit(audit)

        return {
            "input_address": address,
            "formatted_address": geo.get("formatted_address"),
            "state": geo.get("state"),
            "postcode": geo.get("postcode"),
            "locality": geo.get("locality"),
            "lga": lga,
            "holidays": [],
            "holiday_count": 0,
            "pay_period": {
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
            "holidays_in_period": [],
            "holiday_count_in_period": 0,
            "regional_holidays_applied": [],
            **audit,
            "audit_json": json.dumps(audit, ensure_ascii=False),
        }

    _finalise_audit(audit)

    return {
        "input_address": address,
        "formatted_address": geo.get("formatted_address") or geo.get("formatted_address", geo.get("formatted_address")),
        "state": geo.get("state"),
        "postcode": geo.get("postcode"),
        "locality": geo.get("locality"),
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
            f"{getattr(r, 'date', None).isoformat()} - {getattr(r, 'name', '')}".strip()
            for r in matched_rules
            if getattr(r, "date", None) is not None
        ],
        # audit (flat + json)
        **audit,
        "audit_json": json.dumps(audit, ensure_ascii=False),
    }

"""
Batch entry point for Public Holiday report.

Behaviour:
- Reads a CSV input (same structure as the Streamlit batch template)
- Writes enriched findings to: outputs/public_holiday_run/payroll_holiday_check_results.csv
- Generates the same Markdown / HTML / (best-effort) PDF report as the Streamlit UI.

This uses the same reporting functions as streamlit_app.py, so outputs stay aligned.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .service import lookup_address_info
from .reporting.public_holiday_report_md import generate_public_holiday_report
from .reporting.html_builder import build_html_and_pdf


# ---------- Paths & defaults ----------

BASE_DIR = Path(__file__).resolve().parents[2]

BATCH_INPUTS_DIR = BASE_DIR / "batch_inputs"
DEFAULT_INPUT_CSV = BATCH_INPUTS_DIR / "mixed_example.csv"

# Single, canonical output folder for batch + Streamlit
PH_OUTPUT_DIR = BASE_DIR / "outputs" / "public_holiday_run"
FINDINGS_CSV_PATH = PH_OUTPUT_DIR / "payroll_holiday_check_results.csv"


def _parse_iso_date(value: str | None) -> Optional[date]:
    """Parse a simple YYYY-MM-DD string into a date, or return None."""
    if not value:
        return None
    s = value.strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


# ---------- Core batch runner ----------

def run_public_holiday_batch(
    input_csv: Path = DEFAULT_INPUT_CSV,
    output_csv: Path = FINDINGS_CSV_PATH,
    year: Optional[int] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> Path:
    """
    Run the Public Holiday batch using a CSV shaped like the Streamlit template.

    Columns expected (same as template):
    - employee_id
    - office_address
    - home_address
    - work_mode (OFFICE | HOME)
    - year (optional; overrides default year if present)
    - start_date (optional; YYYY-MM-DD)
    - end_date   (optional; YYYY-MM-DD)
    """
    if year is None:
        year = date.today().year

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    PH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Read all rows once
    with input_csv.open("r", newline="", encoding="utf-8-sig") as f_in:
        reader = csv.DictReader(f_in)
        rows: List[Dict[str, Any]] = list(reader)
        original_fieldnames = reader.fieldnames or []

    if not rows:
        # still write an empty file with original headers for consistency
        with output_csv.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=original_fieldnames)
            writer.writeheader()
        return output_csv

    enriched_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows):
        employee_id = row.get("employee_id", None)

        # Normalise work_mode
        work_mode_raw = row.get("work_mode", "")
        work_mode = str(work_mode_raw).upper().strip()

        if work_mode == "OFFICE":
            address = row.get("office_address", "")
        elif work_mode == "HOME":
            address = row.get("home_address", "")
        else:
            # Match Streamlit behaviour for invalid work_mode
            enriched_rows.append({
                "row": idx,
                "employee_id": employee_id,
                "error": "Invalid work_mode (must be OFFICE or HOME)",
            })
            continue

        if not isinstance(address, str) or not address.strip():
            # Match Streamlit behaviour for missing address
            enriched_rows.append({
                "row": idx,
                "employee_id": employee_id,
                "work_mode": work_mode,
                "error": "Missing address for work_mode",
            })
            continue

        # Row overrides (optional) – same semantics as Streamlit batch
        row_year = row.get("year", None)
        if row_year is None or str(row_year).strip() == "":
            effective_year = year
        else:
            try:
                effective_year = int(row_year)
            except (TypeError, ValueError):
                effective_year = year

        # Pay period overrides
        row_start_raw = row.get("start_date", None)
        row_end_raw = row.get("end_date", None)

        start = _parse_iso_date(row_start_raw) or period_start
        end = _parse_iso_date(row_end_raw) or period_end

        try:
            r = lookup_address_info(address.strip(), effective_year, start=start, end=end)

            holidays_in_period = r.get("holidays_in_period") or []
            pay_period = r.get("pay_period") or {}

            # Build a sorted list of unique holiday dates (strings)
            dates = sorted({h.get("date") for h in holidays_in_period if h.get("date")})

            # Map date -> name (first name wins if duplicates)
            names_by_date: Dict[str, str] = {}
            for h in holidays_in_period:
                d = h.get("date")
                if not d:
                    continue
                n = h.get("name") or h.get("localName", "") or ""
                names_by_date.setdefault(d, n)

            # Names aligned to the sorted dates list
            names = [names_by_date.get(d, "") for d in dates]

            enriched_rows.append({
                "row": idx,
                "employee_id": employee_id,
                "work_mode": work_mode,
                "input_address": address.strip(),

                "formatted_address": r.get("formatted_address", ""),
                "state": r.get("state"),
                "postcode": r.get("postcode"),
                "locality": r.get("locality"),
                "lga": r.get("lga"),
                "pay_period_start": pay_period.get("start") or "",
                "pay_period_end": pay_period.get("end") or "",
                "holiday_count_in_period": r.get("holiday_count_in_period"),
                "holiday_dates_in_period": "; ".join(dates),
                "holiday_names_in_period": "; ".join(names),
                "status": r.get("status"),
                "manual_review": r.get("manual_review"),
                "confidence": r.get("confidence"),
                "audit_message": r.get("audit_message"),
                "geocode_quality": r.get("geocode_quality") or r.get("location_type"),
                "lga_resolution_method": r.get("lga_resolution_method"),
                "rules_applied": "; ".join(r.get("rules_applied", [])),
                "replacement_applied": r.get("replacement_applied"),
            })
        except Exception as e:
            # Match Streamlit error shape
            enriched_rows.append({
                "row": idx,
                "employee_id": employee_id,
                "work_mode": work_mode,
                "input_address": address.strip(),
                "error": str(e),
            })

    # --- Write output CSV ---
    if enriched_rows:
        # Union of all keys across rows, like pandas DataFrame would do
        fieldname_set = set()
        for rec in enriched_rows:
            fieldname_set.update(rec.keys())
        fieldnames: List[str] = list(fieldname_set)
    else:
        fieldnames = original_fieldnames

    with output_csv.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    return output_csv


# ---------- CLI entry point ----------

def main() -> None:
    print(f"Running Public Holiday batch using: {DEFAULT_INPUT_CSV}")
    findings_csv = run_public_holiday_batch()
    print(f"Wrote enriched results to: {findings_csv}")

    # Generate Markdown report from findings CSV (same as Streamlit)
    report_md_path = generate_public_holiday_report(
        findings_csv=findings_csv,
        output_dir=PH_OUTPUT_DIR,
        input_files=[DEFAULT_INPUT_CSV.name],
    )
    print(f"Wrote Markdown report to: {report_md_path}")

    # Build HTML (and best-effort PDF) in the same output folder
    html_path, pdf_path = build_html_and_pdf(
        md_path=report_md_path,
        out_dir=PH_OUTPUT_DIR,
        title="Public Holiday Compliance Review",
    )

    print(f"Wrote HTML report to: {html_path}")
    if pdf_path is not None and pdf_path.exists():
        print(f"Wrote PDF report to: {pdf_path}")
    else:
        print("PDF generation skipped (WeasyPrint not available).")


if __name__ == "__main__":
    main()

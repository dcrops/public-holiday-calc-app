from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from datetime import datetime

def fmt_date(d: date) -> str:
    return d.strftime("%d %b %Y")

def fmt_iso_date(s: str | None) -> str:
    if not s or not str(s).strip():
        return "—"
    # handle YYYY-MM-DD strings safely
    return date.fromisoformat(str(s)).strftime("%d %b %Y")



# Keep wording consistent: "potential issues" / "areas for review" (not legal conclusions).
DISCLAIMER_BLOCK = (
    "This review assesses **public holiday applicability and entitlement preconditions** for employees based on their recorded work location and applicable Australian public holiday calendars.\n\n"
    "Public holiday entitlements in Australia are **location-dependent**. In order to confirm whether an employee was entitled to payment, penalty rates, or an alternative day, the applicable public holidays for their work location must first be determined with sufficient certainty.\n\n"
    "This report identifies: "
    "- public holidays that apply to each employee for the reviewed period, based on available location data, and "
    "- records where entitlement outcomes **cannot be reliably confirmed** without further validation due to uncertainty in the employee’s applicable location.\n\n"
    "This review does **not** calculate pay outcomes, interpret awards or enterprise agreements, or determine whether an underpayment has occurred. Findings represent potential areas for review only."
)

STATUS_ORDER = [
    "NOT_FOUND",
    "LOW_CONFIDENCE",
    "REVIEW_REQUIRED",
    "MISMATCH",
    "OK",
    "INFO",
]

SEVERITY_EXPLANATION = """
    ### Severity classification (how to read this report)

    Findings are classified to help prioritise review effort based on **potential public holiday entitlement impact**, not data quality alone:

    Applicable work location refers to the geographic location used to determine which Australian public holiday calendar applies for the work performed during the review period. 
    This may differ from an employee’s residential address or contractual office location.
        
    - **High** – The applicable public holiday calendar could not be reliably determined
    (for example, unresolved or ambiguous work location). Public holiday entitlements
    **cannot be confirmed** without manual validation.

    - **Medium** – The work location was resolved with lower confidence and **one or more
    public holidays fall within the employee’s pay period**. Entitlements are likely
    correct but should be reviewed to confirm the correct calendar was applied.

    - **Low** – Minor location uncertainty was identified, but **no public holidays fall
    within the employee’s pay period**. These records are unlikely to result in incorrect
    public holiday entitlements.
"""


def _as_bool(value: Any) -> bool:
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in {"true", "1", "yes", "y", "t"}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _status_sort_key(status: str) -> Tuple[int, str]:
    s = (status or "").strip()
    if s in STATUS_ORDER:
        return (STATUS_ORDER.index(s), s)
    return (999, s)


def _status_to_severity(status: str | None, manual_review: bool, holiday_count_in_period: int) -> str:
    """
    Map a row's status/manual_review + entitlement impact into a report severity bucket.

    Principle:
    - Severity should reflect entitlement risk, not just input cleanliness.
    - Location uncertainty only becomes MED/HIGH when it affects holiday applicability for a pay period.
    """
    s = (status or "").strip().upper()
    hc = int(holiday_count_in_period or 0)

    # Highest risk: cannot determine applicable holiday calendar at all
    if s in {"NOT_FOUND", "AMBIGUOUS_LGA"}:
        return "HIGH"

    # Location resolved but uncertain: severity depends on whether holidays actually apply
    if s == "LOW_CONFIDENCE":
        return "MED" if hc > 0 else "LOW"

    # Any other manual review flags: treat as MED only if there is potential entitlement impact
    if manual_review:
        return "MED" if hc > 0 else "LOW"

    # Otherwise: informational / no action required
    return "INFO"


def _as_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        s = str(value).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default

def _fmt_iso_to_long(value: str | None) -> str:
    """
    Convert ISO date strings (YYYY-MM-DD) to 'DD Mon YYYY'.
    Falls back to the original value if parsing fails.
    """
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value)).date().strftime("%d %b %Y")
    except Exception:
        return str(value)


@dataclass(frozen=True)
class ReportContext:
    prepared_as_at: date
    findings_csv: Path
    output_dir: Path
    input_files: List[str]


def load_findings(findings_csv: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with findings_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Normalise a few fields we use a lot
            r["manual_review"] = _as_bool(r.get("manual_review"))
            r["confidence"] = _as_float(r.get("confidence"), default=0.0)
            r["holiday_count_in_period"] = _safe_int(r.get("holiday_count_in_period"), default=0)
            rows.append(r)
    return rows


def summarise(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Period (derived from CSV)
    starts = sorted({_clean(r.get("pay_period_start")) for r in findings if _clean(r.get("pay_period_start"))})
    ends = sorted({_clean(r.get("pay_period_end")) for r in findings if _clean(r.get("pay_period_end"))})

    period_start = starts[0] if starts else ""
    period_end = ends[-1] if ends else ""

    total = len(findings)
    manual_review_count = sum(1 for r in findings if r.get("manual_review") is True)

    # Counts by status and severity
    by_status: Dict[str, int] = {}
    by_sev: Dict[str, int] = {"HIGH": 0, "MED": 0, "LOW": 0, "INFO": 0}

    not_found = 0
    low_conf = 0

    for r in findings:
        status = _clean(r.get("status")) or "UNKNOWN"
        by_status[status] = by_status.get(status, 0) + 1

        hc = _as_int(r.get("holiday_count_in_period"), 0)
        sev = _status_to_severity(
            status,
            manual_review=bool(r.get("manual_review") is True),
            holiday_count_in_period=hc,
        )
        by_sev[sev] = by_sev.get(sev, 0) + 1

        if status.upper() == "NOT_FOUND":
            not_found += 1
        if status.upper() == "LOW_CONFIDENCE":
            low_conf += 1

    # Holiday distribution within pay period
    zero_holidays = 0
    one_holiday = 0
    two_plus_holidays = 0

    for r in findings:
        try:
            count = int(r.get("holiday_count_in_period") or 0)
        except Exception:
            count = 0

        if count == 0:
            zero_holidays += 1
        elif count == 1:
            one_holiday += 1
        else:
            two_plus_holidays += 1


        # A simple, deterministic "key messages" list
    key_messages: List[str] = []

    if total > 0:
        key_messages.append(
            "This review analysed public holiday applicability for employees during the review period "
            "based on their recorded work location. Applicable national, state, and regional public "
            "holidays were identified for each record."
        )
        key_messages.append(
            f"Public holiday outcomes in the review period: "
            f"**{zero_holidays}** record(s) with **no public holidays**, "
            f"**{one_holiday}** with **one public holiday**, and "
            f"**{two_plus_holidays}** with **two or more public holidays** in the applicable pay period."
        )

    if manual_review_count > 0:
        key_messages.append(
            f"In **{manual_review_count}** record(s), public holiday entitlement outcomes "
            "**cannot yet be confidently confirmed** without further validation due to uncertainty "
            "in the employee’s applicable location."
        )

    if not_found > 0:
        key_messages.append(
            f"**{not_found}** record(s) could not be resolved to a valid location "
            "(status **NOT_FOUND**) and require address correction before public holiday "
            "entitlements can be validated."
        )

    if low_conf > 0:
        key_messages.append(
            f"**{low_conf}** record(s) were resolved with **low location certainty** "
            "(status **LOW_CONFIDENCE**); manual validation of the applicable work location "
            "is recommended before confirming entitlements."
        )

    # Always include a closing orientation statement
    key_messages.append(
        "Records flagged for manual review do not indicate an error, but highlight cases "
        "where public holiday entitlement depends on confirmation of the employee’s applicable work location."
    )


    return {
        "period_start": period_start,
        "period_end": period_end,
        "total": total,
        "manual_review_count": manual_review_count,
        "by_status": dict(sorted(by_status.items(), key=lambda kv: _status_sort_key(kv[0]))),
        "by_severity": by_sev,
        "key_messages": key_messages,
    }


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    # Simple markdown table helper
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def render_markdown(ctx: ReportContext, findings: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    prepared = ctx.prepared_as_at.isoformat()
    period_start = summary.get("period_start", "")
    period_end = summary.get("period_end", "")

    # Executive summary bullets
    exec_bullets = "\n".join([f"- {m}" for m in summary.get("key_messages", [])]) or "- No records were provided."

    # Summary tables
    sev_rows = [[k, str(v)] for k, v in summary.get("by_severity", {}).items()]
    status_rows = [[k, str(v)] for k, v in summary.get("by_status", {}).items()]

    # Detailed findings: group by severity then status
    def find_key(r: Dict[str, Any]) -> Tuple[int, int, str]:
        status = _clean(r.get("status"))
        hc = _as_int(r.get("holiday_count_in_period"), 0)
        sev = _status_to_severity(
            status,
            manual_review=bool(r.get("manual_review") is True),
            holiday_count_in_period=hc,
        )
        sev_order = {"HIGH": 0, "MED": 1, "LOW": 2, "INFO": 3}.get(sev, 9)
        status_order = _status_sort_key(status)[0]
        emp = _clean(r.get("employee_id"))
        return (sev_order, status_order, emp)

    findings_sorted = sorted(findings, key=find_key)

    blocks: List[str] = []
    for r in findings_sorted:
        status = _clean(r.get("status")) or "UNKNOWN"
        manual = bool(r.get("manual_review"))
        hc = _as_int(r.get("holiday_count_in_period"), 0)
        sev = _status_to_severity(
            status,
            manual_review=bool(r.get("manual_review") is True),
            holiday_count_in_period=hc,
        )
        emp = _clean(r.get("employee_id"))
        work_mode = _clean(r.get("work_mode"))
        addr_in = _clean(r.get("input_address"))
        addr_fmt = _clean(r.get("formatted_address"))
        state = _clean(r.get("state"))
        postcode = _clean(r.get("postcode"))
        locality = _clean(r.get("locality"))
        lga = _clean(r.get("lga"))
        pstart = _clean(r.get("pay_period_start"))
        pend = _clean(r.get("pay_period_end"))
        hcount = _safe_int(r.get("holiday_count_in_period"), 0)
        hdates = _clean(r.get("holiday_dates_in_period"))
        confidence = _as_float(r.get("confidence"), 0.0)
        msg = _clean(r.get("audit_message")) or "(No audit message provided.)"
        geocode_quality = _clean(r.get("geocode_quality"))
        lga_method = _clean(r.get("lga_resolution_method"))
        rules_applied = _clean(r.get("rules_applied"))
        replacement = _clean(r.get("replacement_applied"))

        # “Why it matters” and “Next action” – deterministic, status-driven
        manual_review = bool(r.get("manual_review") is True)
        status = (r.get("status") or "").upper()

        if status == "NOT_FOUND":
            msg = "Work location could not be resolved; public holiday applicability cannot be determined."
            why = "Without a resolvable work location, public holiday calendars cannot be applied reliably."
            next_action = "Correct the address input (include suburb + state/postcode), rerun, and validate the result."

        elif status == "LOW_CONFIDENCE":
            if manual_review:
                msg = "Public holiday applicability was derived, but entitlement outcome cannot be confirmed until location is validated."
                why = "Low certainty in the resolved location may change which public holiday calendar applies, potentially affecting payment, penalty rates, or substitute day entitlements."
                next_action = "Validate the employee’s work location against internal records, then rerun if corrections are required."
            else:
                msg = "Public holiday applicability was derived for the pay period based on recorded work location."
                why = "Public holiday entitlements are location-dependent; holidays in-period drive correct treatment."
                next_action = "Confirm payroll configuration/pay events align with the applicable holiday calendar for this location."

        else:
            # e.g. AMBIGUOUS_LGA etc
            if manual_review:
                msg = "Entitlement outcome cannot be confirmed without further validation due to uncertainty in applicable location."
                why = "Ambiguity in LGA/locality mapping can change applicable regional holidays."
                next_action = "Validate the employee’s applicable work location and confirm public holiday treatment."
            else:
                msg = "Public holiday applicability was derived for the pay period."
                why = "This identifies holidays in-period that may affect pay treatment."
                next_action = "Cross-check payroll pay events for the listed holiday dates."

        # Build labelled holiday list for evidence (Name + Date)
        holiday_dates_raw = (r.get("holiday_dates_in_period") or "").strip()
        holiday_names_raw = (r.get("holiday_names_in_period") or "").strip()

        labelled_holidays = "-"
        if holiday_dates_raw:
            dates = [d.strip() for d in holiday_dates_raw.split(";") if d.strip()]
            names = [n.strip() for n in holiday_names_raw.split(";") if n.strip()] if holiday_names_raw else []

            items = []
            for i, d in enumerate(dates):
                date_label = _fmt_iso_to_long(d) if len(d) == 10 and d[4] == "-" else d
                if i < len(names) and names[i]:
                    items.append(f"{names[i]} ({date_label})")
                else:
                    items.append(date_label)

            labelled_holidays = "; ".join(items)

        evidence_lines = [
            f"- **Employee:** `{emp}`",
            f"- **Work mode:** {work_mode or '—'}",
            f"- **Input address:** {addr_in or '—'}",
            f"- **Resolved address:** {addr_fmt or '—'}",
            f"- **Resolved location:** {', '.join([x for x in [locality, state, postcode, lga] if x]) or '—'}",
            f"- **Pay period:** {pstart or '—'} → {pend or '—'}",
            f"- **Holidays in period:** {hcount} ({labelled_holidays})",
            f"- **Status:** `{status}`  |  **Severity:** **{sev}**  |  **Manual review:** `{manual}`  |  **Confidence:** `{confidence:.2f}`",
        ]

        # Optional evidence lines (only if present)
        if geocode_quality:
            evidence_lines.append(f"- **Geocode quality:** {geocode_quality}")
        if lga_method:
            evidence_lines.append(f"- **LGA resolution method:** {lga_method}")
        if rules_applied:
            evidence_lines.append(
                f"- **Applicable regional holiday rules (full year):** {rules_applied}")
        if replacement:
            evidence_lines.append(f"- **Replacement applied:** {replacement}")

        blocks.append(
            "\n".join(
                [
                    f"### {sev} — {status} — Employee {emp}",
                    "",
                    f"**Finding**: {msg}",
                    "",
                    "**Evidence**:",
                    "",
                    *evidence_lines,
                    "",
                    f"**Why it matters**: {why}",
                    "",
                    f"**Recommended next action**: {next_action}",
                    "",
                ]
            )
        )

    detailed_section = "\n".join(blocks) if blocks else "_No findings to display._"

    inputs_list = "\n".join([f"- `{name}`" for name in (ctx.input_files or [])]) or "- (Not provided)"

    prepared = fmt_date(ctx.prepared_as_at)
    period_start = fmt_iso_date(summary.get("period_start"))
    period_end = fmt_iso_date(summary.get("period_end"))

    md_parts = [
        "# Public Holiday Compliance Review",
        "",
        f"**Report prepared as at:** {prepared}  ",
        f"**Review period (derived from results):** {period_start} to {period_end}",
        "",
        "## Purpose and disclaimer",
        "",
        DISCLAIMER_BLOCK,
        "",
        "## Data sources",
        "",
        inputs_list,
        "",
        f"- Findings CSV: `{ctx.findings_csv.name}`",
        "",
        "## Executive Summary",
        "",
        exec_bullets,
        "",
        SEVERITY_EXPLANATION,
        "",
        build_holiday_applicability_overview(findings),
        "",
        "## Scope & Methodology",
        "",
        "- This review is based on the supplied CSV outputs from the Public Holiday Compliance check.",
        "- Locations are determined from the provided addresses and mapped to state/LGA/locality where possible.",
        "- Holiday dates are derived from the configured holiday datasets and any applicable regional rules.",
        "- Findings highlight potential issues and areas for review; they do not confirm compliance outcomes.",
        "- The review does **not** independently calculate pay, loadings, or other entitlements; those remain subject to your payroll setup and industrial instruments.",
        "",
        "## Key Findings",
        "",
        "Severity is determined based on the ability to confirm the correct public holiday ",
        " calendar and whether public holidays fall within the employee’s pay period."
        "",
        "### Findings by severity",
        "",
        _md_table(["Severity", "Count"], sev_rows),
        "",
        "### Findings by status",
        "",
        _md_table(["Status", "Count"], status_rows),
        "",
        "## Detailed Findings",
        "",
        detailed_section,
        "",
        "## Limitations & Assumptions",
        "",
        "- **Industrial instrument context not assessed:** Award/EBA/contract rules are not inferred from CSV outputs.",
        "- **Address quality impacts results:** Missing, partial or ambiguous addresses can lead to unresolved or low-confidence geocoding outcomes.",
        "- **Regional holiday nuance:** Some holidays apply only at LGA or locality level (for example, local show days or race days instead of, or in addition to, state-wide holidays).",
        "- **Replacement holidays:** Where replacement or substituted holidays exist, outcomes depend on correct regional rule configuration and maintained holiday datasets.",
        "",
        "## Recommended Next Steps",
        "",
        "- Triage **HIGH** severity items first (e.g., addresses not found).",
        "- Validate any **LOW_CONFIDENCE** items against internal location records.",
        "- Where mismatches are suspected, cross-check payroll configuration, timesheets, and pay events for impacted periods.",
        "- Rerun the check after corrections to confirm that items are resolved.",
        "",
        "## Appendix",
        "",
        "### Field notes (from findings CSV)",
        "",
        "- `status`: Engine outcome for the record (e.g., NOT_FOUND, LOW_CONFIDENCE).",
        "- `manual_review`: Indicates the record should be reviewed by a payroll administrator.",
        "- `confidence`: Numeric indicator supporting the resolution outcome (used for triage, not a compliance verdict).",
        "- `rules_applied` / `replacement_applied`: Evidence of regional rules influencing the holiday set.",
    ]

    return "\n".join(md_parts).strip() + "\n"

def build_holiday_applicability_overview(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "## Holiday applicability overview\n\nNo records were available.\n"

    counts = [_as_int(r.get("holiday_count_in_period"), 0) for r in findings]
    total = len(counts)
    zero = sum(1 for c in counts if c == 0)
    one = sum(1 for c in counts if c == 1)
    two_plus = sum(1 for c in counts if c >= 2)

    # Top holiday dates (frequency), optionally including names
    # key = (date_str, name_str)
    freq: Dict[Tuple[str, str], int] = {}

    for r in findings:
        dates_str = (r.get("holiday_dates_in_period") or "").strip()
        names_str = (r.get("holiday_names_in_period") or "").strip()

        if not dates_str:
            continue

        date_parts = [x.strip() for x in dates_str.split(";") if x.strip()]
        name_parts = [x.strip() for x in names_str.split(";") if x.strip()] if names_str else []

        for idx, dt in enumerate(date_parts):
            name = name_parts[idx] if idx < len(name_parts) else ""
            key = (dt, name)
            freq[key] = freq.get(key, 0) + 1

    # Sort by frequency desc, then by date, then by name
    top = sorted(
        freq.items(),
        key=lambda kv: (-kv[1], kv[0][0], kv[0][1])
    )[:10]

    lines = [
        "## Holiday applicability overview",
        "",
        "This section summarises the public holidays identified within the employee pay periods provided.",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Records analysed | {total} |",
        f"| Records with 0 holidays in period | {zero} |",
        f"| Records with 1 holiday in period | {one} |",
        f"| Records with 2+ holidays in period | {two_plus} |",
        "",
        "Public holiday entitlements are derived from the applicable state, LGA, or locality calendar. ",
        "If the wrong calendar is applied, employees may be incorrectly paid, underpaid, or granted incorrect substitute days.",
        "",
    ]

    if top:
        lines += [
            "### Most common holiday dates in period",
            "",
            "| Holiday date | Holiday name | Records impacted |",
            "|---|---|---:|",
        ]
        for (d, name), n in top:
            # Format ISO date -> 01 Jan 2025 style when possible
            disp_date = _fmt_iso_to_long(d) if len(d) == 10 and d[4] == "-" else d
            disp_name = name or "—"
            lines.append(f"| {disp_date} | {disp_name} | {n} |")
        lines.append("")

    return "\n".join(lines)


def write_report_markdown(md: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "public_holiday_compliance_report.md"
    out_path.write_text(md, encoding="utf-8")
    return out_path


def generate_public_holiday_report(
    findings_csv: Path,
    output_dir: Path,
    *,
    input_files: Optional[List[str]] = None,
) -> Path:
    ctx = ReportContext(
        prepared_as_at=date.today(),
        findings_csv=findings_csv,
        output_dir=output_dir,
        input_files=input_files or [],
    )
    findings = load_findings(findings_csv)
    summary = summarise(findings)
    md = render_markdown(ctx, findings, summary)
    return write_report_markdown(md, output_dir)

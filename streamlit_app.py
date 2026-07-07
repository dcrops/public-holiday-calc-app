import streamlit as st
import pandas as pd
from pathlib import Path
from PIL import Image
from textwrap import dedent

from src.address_holidays.service import lookup_address_info
from src.address_holidays.reporting.public_holiday_report_md import (
    generate_public_holiday_report,
)
from src.address_holidays.reporting.html_builder import build_html_and_pdf


# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="CRC | Public Holiday Entitlements",
    page_icon="🗺️",
    layout="wide",
)

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
if "batch_results" not in st.session_state:
    st.session_state.batch_results = None

if "batch_uploaded_name" not in st.session_state:
    st.session_state.batch_uploaded_name = None


# ---------------------------------------------------
# LOAD LOGO
# ---------------------------------------------------
logo = Image.open("assets/crc_logo.png")

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------
col1, col2 = st.columns([1, 7])

with col1:
    st.image(logo, width=90)

with col2:
    st.markdown(
        dedent(
            """
            <div style='font-size:14px; letter-spacing:0.25em; color:#A1A1AA; font-weight:600; margin-bottom:6px; text-transform:uppercase;'>
                Chase Risk & Compliance
            </div>

            <div style='font-size:42px; font-weight:800; line-height:1.1; margin-bottom:10px; color:white;'>
                Australian Address → LGA & Public Holidays
            </div>

            <div style='font-size:17px; color:#A1A1AA; max-width:900px; line-height:1.6;'>
                Governance-aware operational entitlement intelligence for national, state, LGA and locality-specific public holiday logic.
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

office_address = st.text_input(
    "Office address",
    placeholder="e.g. 123 Collins St, Melbourne VIC",
)
home_address = st.text_input(
    "Home address",
    placeholder="e.g. 10 Smith St, Brunswick VIC",
)
year = st.selectbox("Year", options=[2024, 2025, 2026, 2027], index=1)

show_debug = st.toggle("🔎 Show debug (state/locality/LGA/postcode)", value=False)

if show_debug:
    if st.button("🧹 Clear geocode cache (dev)"):
        from src.address_holidays.geocode_cache import clear_cache

        n = clear_cache()
        st.success(f"Cleared {n} cached geocode entr{'y' if n == 1 else 'ies'}.")
        st.rerun()


if st.button("Lookup", type="primary"):
    if not office_address.strip() and not home_address.strip():
        st.warning("Enter at least one address (office and/or home).")
        st.stop()

    with st.spinner("Looking up…"):
        office_result = None
        home_result = None

        if office_address.strip():
            try:
                office_result = lookup_address_info(office_address, int(year))
            except Exception as e:
                msg = str(e)
                if "Address not found" in msg or "ZERO_RESULTS" in msg:
                    st.error(
                        "Address not found. Try adding suburb + state/postcode "
                        "(e.g. 'Brunswick VIC 3056') or check spelling."
                    )
                else:
                    st.error(f"Office lookup failed: {e}")

        if home_address.strip():
            try:
                home_result = lookup_address_info(home_address, int(year))
            except Exception as e:
                msg = str(e)
                if "Address not found" in msg or "ZERO_RESULTS" in msg:
                    st.error(
                        "Address not found. Try adding suburb + state/postcode "
                        "(e.g. 'Brunswick VIC 3056') or check spelling."
                    )
                else:
                    st.error(f"Home lookup failed: {e}")

    col1, col2 = st.columns([3, 3])

    with col1:
        st.subheader("🏢 Office location")
        if office_result:
            m1, m2, m3 = st.columns(3)
            m1.metric("Public holidays", office_result.get("holiday_count", 0))
            m2.metric("Status", office_result.get("status", "-"))
            m3.metric("Confidence", f"{office_result.get('confidence', 0):.2f}")

            st.caption(office_result.get("audit_message", ""))

            if office_result.get("manual_review"):
                status = office_result.get("status")
                if status == "LOW_CONFIDENCE":
                    st.warning(
                        "Manual review recommended — the address was resolved with lower geocoding confidence."
                    )
                elif status == "NOT_FOUND":
                    st.error(
                        "Address could not be resolved. Please check spelling or add suburb + state/postcode."
                    )
                else:
                    st.warning("Manual review recommended — please check the audit details.")

            st.text(office_result.get("formatted_address", ""))

            with st.expander("Audit details"):
                st.json(
                    {
                        "status": office_result.get("status"),
                        "manual_review": office_result.get("manual_review"),
                        "confidence": office_result.get("confidence"),
                        "geocode_provider": office_result.get("geocode_provider"),
                        "geocode_quality": office_result.get("geocode_quality"),
                        "lga_resolution_method": office_result.get("lga_resolution_method"),
                        "rules_applied": office_result.get("rules_applied"),
                        "replacement_applied": office_result.get("replacement_applied"),
                    }
                )

            # 🔎 Debug block (Office)
            if show_debug:
                st.code(
                    {
                        "state": office_result.get("state"),
                        "postcode": office_result.get("postcode"),
                        "locality": office_result.get("locality"),
                        "lga": office_result.get("lga"),
                    },
                    language="json",
                )

            st.dataframe(office_result.get("holidays", []), use_container_width=True)
        else:
            st.info("No office address provided.")

    with col2:
        st.subheader("🏠 Home location")
        if home_result:
            m1, m2, m3 = st.columns(3)
            m1.metric("Public holidays", home_result.get("holiday_count", 0))
            m2.metric("Status", home_result.get("status", "-"))
            m3.metric("Confidence", f"{home_result.get('confidence', 0):.2f}")

            st.caption(home_result.get("audit_message", ""))

            if home_result.get("manual_review"):
                status = home_result.get("status")
                if status == "LOW_CONFIDENCE":
                    st.warning(
                        "Manual review recommended — the address was resolved with lower geocoding confidence."
                    )
                elif status == "NOT_FOUND":
                    st.error(
                        "Address could not be resolved. Please check spelling or add suburb + state/postcode."
                    )
                else:
                    st.warning("Manual review recommended — please check the audit details.")

            st.text(home_result.get("formatted_address", ""))

            with st.expander("Audit details"):
                st.json(
                    {
                        "status": home_result.get("status"),
                        "manual_review": home_result.get("manual_review"),
                        "confidence": home_result.get("confidence"),
                        "geocode_provider": home_result.get("geocode_provider"),
                        "geocode_quality": home_result.get("geocode_quality"),
                        "lga_resolution_method": home_result.get("lga_resolution_method"),
                        "rules_applied": home_result.get("rules_applied"),
                        "replacement_applied": home_result.get("replacement_applied"),
                    }
                )

            # 🔎 Debug block (Home)
            if show_debug:
                st.code(
                    {
                        "state": home_result.get("state"),
                        "postcode": home_result.get("postcode"),
                        "locality": home_result.get("locality"),
                        "lga": home_result.get("lga"),
                    },
                    language="json",
                )

            st.dataframe(home_result.get("holidays", []), use_container_width=True)
        else:
            st.info("No home address provided.")


st.divider()
st.header("📦 Batch payroll check (CSV)")

template_csv = """employee_id,office_address,home_address,work_mode,year,start_date,end_date
E001,"Federation Square, Melbourne VIC","10 Smith St, Brunswick VIC",OFFICE,2025,2025-04-18,2025-04-21
E002,"123 Collins St, Melbourne VIC","42 Hutchinson St, Brunswick East VIC",HOME,2025,,
"""

st.download_button(
    "⬇️ Download batch CSV template",
    data=template_csv,
    file_name="batch_template.csv",
    mime="text/csv",
)

st.caption(
    "Upload a CSV with OFFICE/HOME work_mode. The app will calculate holidays for the chosen location per row."
)

uploaded = st.file_uploader("Upload CSV", type=["csv"])

# Clear old batch results when the uploaded file changes or is removed.
current_uploaded_name = uploaded.name if uploaded is not None else None
if current_uploaded_name != st.session_state.batch_uploaded_name:
    st.session_state.batch_results = None
    st.session_state.batch_uploaded_name = current_uploaded_name

if uploaded is not None:
    input_files = [uploaded.name]
else:
    input_files = []

default_year = st.selectbox(
    "Default year (used only if missing in CSV)",
    options=[2024, 2025, 2026, 2027],
    index=1,
)

default_start = st.date_input(
    "Default pay period start (used only if missing in CSV)",
    value=None,
)

default_end = st.date_input(
    "Default pay period end (used only if missing in CSV)",
    value=None,
)

st.caption("If your CSV provides year or pay period dates, those values take precedence.")

run_batch = st.button(
    "▶ Run Compliance Review",
    type="primary",
    disabled=uploaded is None,
)

if run_batch:
    if uploaded is None:
        st.warning("Upload a CSV before running the compliance review.")
        st.stop()

    uploaded.seek(0)
    df = pd.read_csv(uploaded)

    if "work_mode" not in df.columns:
        st.error("CSV must include a 'work_mode' column with OFFICE or HOME.")
        st.stop()

    results = []

    with st.spinner("Processing rows…"):
        for idx, row in df.iterrows():
            employee_id = row.get("employee_id", None)
            work_mode = str(row.get("work_mode", "")).upper().strip()

            if work_mode == "OFFICE":
                address = row.get("office_address", "")
            elif work_mode == "HOME":
                address = row.get("home_address", "")
            else:
                results.append(
                    {
                        "row": idx,
                        "employee_id": employee_id,
                        "error": "Invalid work_mode (must be OFFICE or HOME)",
                    }
                )
                continue

            if not isinstance(address, str) or not address.strip():
                results.append(
                    {
                        "row": idx,
                        "employee_id": employee_id,
                        "work_mode": work_mode,
                        "error": "Missing address for work_mode",
                    }
                )
                continue

            # Row overrides (optional)
            row_year = row.get("year", default_year)
            row_year = int(row_year) if pd.notna(row_year) else int(default_year)

            start = row.get("start_date", default_start)
            end = row.get("end_date", default_end)

            start = (
                pd.to_datetime(start).date()
                if pd.notna(start) and str(start).strip()
                else None
            )
            end = (
                pd.to_datetime(end).date()
                if pd.notna(end) and str(end).strip()
                else None
            )

            try:
                r = lookup_address_info(address.strip(), row_year, start=start, end=end)

                holidays_in_period = r.get("holidays_in_period") or []
                pay_period = r.get("pay_period") or {}

                # Build a sorted list of unique holiday dates
                dates = sorted({h.get("date") for h in holidays_in_period if h.get("date")})

                # Map date -> name (first name wins if duplicates)
                names_by_date = {}
                for h in holidays_in_period:
                    d = h.get("date")
                    if not d:
                        continue
                    n = h.get("name") or h.get("localName", "") or ""
                    names_by_date.setdefault(d, n)

                # Names aligned to the sorted dates list
                names = [names_by_date.get(d, "") for d in dates]

                results.append(
                    {
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
                        "geocode_quality": (
                            r.get("geocode_quality")
                            or r.get("location_type")
                            or "UNKNOWN"
                        ),
                        "lga_resolution_method": r.get("lga_resolution_method"),
                        "rules_applied": "; ".join(r.get("rules_applied", [])),
                        "replacement_applied": r.get("replacement_applied"),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "row": idx,
                        "employee_id": employee_id,
                        "work_mode": work_mode,
                        "input_address": address.strip(),
                        "error": str(e),
                    }
                )

    out_df = pd.DataFrame(results)

    # Choose / reuse your output directory
    output_dir = Path("outputs") / "public_holiday_run"
    output_dir.mkdir(parents=True, exist_ok=True)

    results_csv_path = output_dir / "payroll_holiday_check_results.csv"
    out_df.to_csv(results_csv_path, index=False)

    report_md_path = generate_public_holiday_report(
        findings_csv=results_csv_path,
        output_dir=output_dir,
        input_files=input_files,
    )

    html_path, pdf_path = build_html_and_pdf(
        md_path=report_md_path,
        out_dir=output_dir,
        title="Public Holiday Compliance Review",
    )

    csv_bytes = out_df.to_csv(index=False).encode("utf-8")
    md_bytes = report_md_path.read_bytes()
    html_bytes = html_path.read_bytes()
    pdf_bytes = pdf_path.read_bytes() if pdf_path and pdf_path.exists() else None

    st.session_state.batch_results = {
        "out_df": out_df,
        "csv_bytes": csv_bytes,
        "md_bytes": md_bytes,
        "html_bytes": html_bytes,
        "pdf_bytes": pdf_bytes,
    }

    st.success("Compliance review complete. Downloads are ready.")

if st.session_state.batch_results is not None:
    batch_results = st.session_state.batch_results
    out_df = batch_results["out_df"]

    st.dataframe(out_df, use_container_width=True)

    st.download_button(
        "⬇️ Download results CSV",
        data=batch_results["csv_bytes"],
        file_name="payroll_holiday_check_results.csv",
        mime="text/csv",
    )

    st.download_button(
        "⬇ Download audit report (Markdown)",
        data=batch_results["md_bytes"],
        file_name="public_holiday_compliance_report.md",
        mime="text/markdown",
    )

    st.download_button(
        "⬇ Download audit report (HTML)",
        data=batch_results["html_bytes"],
        file_name="public_holiday_compliance_report.html",
        mime="text/html",
    )

    if batch_results.get("pdf_bytes"):
        st.download_button(
            "⬇ Download audit report (PDF – best effort)",
            data=batch_results["pdf_bytes"],
            file_name="public_holiday_compliance_report.pdf",
            mime="application/pdf",
        )

import streamlit as st
import pandas as pd
import traceback


from src.address_holidays.service import lookup_address_info

st.set_page_config(page_title="AU Address → LGA + Public Holidays", page_icon="🗺️", layout="wide")

st.title("🗺️ Australian Address → LGA & Public Holidays")
st.caption(
    "Enter an Australian address. The app geocodes it, resolves the LGA, "
    "and lists applicable national, state, and regional public holidays for the selected year."
)

office_address = st.text_input("Office address", placeholder="e.g. 123 Collins St, Melbourne VIC")
home_address = st.text_input("Home address", placeholder="e.g. 10 Smith St, Brunswick VIC")
year = st.selectbox("Year", options=[2024, 2025, 2026, 2027], index=1)

show_debug = st.toggle("🔎 Show debug (state/locality/LGA/postcode)", value=False)

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
                st.error(f"Office lookup failed: {e}")

        if home_address.strip():
            try:
                home_result = lookup_address_info(home_address, int(year))
            except Exception as e:
                st.exception(e)

    col1, col2 = st.columns([3, 3])

    with col1:
        st.subheader("🏢 Office location")
        if office_result:
            st.metric("Public holidays", office_result.get("holiday_count", 0))
            st.text(office_result.get("formatted_address", ""))

            st.markdown("**Details**")
            st.markdown(f"- **State:** {office_result.get('state') or '-'}")
            st.markdown(f"- **Postcode:** {office_result.get('postcode') or '-'}")
            st.markdown(f"- **Locality:** {office_result.get('locality') or '-'}")
            st.markdown(f"- **LGA:** {office_result.get('lga') or '-'}")

            # 🔎 Debug block (ADD THIS)
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
        st.subheader("🏢 Home location")
        if home_result:
            st.metric("Public holidays", home_result.get("holiday_count", 0))
            st.text(home_result.get("formatted_address", ""))

            st.markdown("**Details**")
            st.markdown(f"- **State:** {home_result.get('state') or '-'}")
            st.markdown(f"- **Postcode:** {home_result.get('postcode') or '-'}")
            st.markdown(f"- **Locality:** {home_result.get('locality') or '-'}")
            st.markdown(f"- **LGA:** {home_result.get('lga') or '-'}")

            # 🔎 Debug block (ADD THIS)
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


st.caption("Upload a CSV with OFFICE/HOME work_mode. The app will calculate holidays for the chosen location per row.")

uploaded = st.file_uploader("Upload CSV", type=["csv"])

default_year = st.selectbox("Default year (used if missing in CSV)", [2024, 2025, 2026, 2027], index=1)

default_start = st.date_input("Default pay period start (optional)", value=None)
default_end = st.date_input("Default pay period end (optional)", value=None)

if uploaded:
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
                results.append({"row": idx, "employee_id": employee_id, "error": "Invalid work_mode (must be OFFICE or HOME)"})
                continue

            if not isinstance(address, str) or not address.strip():
                results.append({"row": idx, "employee_id": employee_id, "work_mode": work_mode, "error": "Missing address for work_mode"})
                continue

            # Row overrides (optional)
            year = row.get("year", default_year)
            year = int(year) if pd.notna(year) else int(default_year)

            start = row.get("start_date", default_start)
            end = row.get("end_date", default_end)

            start = pd.to_datetime(start).date() if pd.notna(start) and str(start).strip() else None
            end = pd.to_datetime(end).date() if pd.notna(end) and str(end).strip() else None

            try:
                r = lookup_address_info(address.strip(), year, start=start, end=end)

                holidays_in_period = r.get("holidays_in_period") or []
                pay_period = r.get("pay_period") or {}

                results.append({
                    "row": idx,
                    "employee_id": employee_id,
                    "work_mode": work_mode,
                    "input_address": address.strip(),

                    "formatted_address": r.get("formatted_address", ""),
                    "state": r.get("state"),
                    "postcode": r.get("postcode"),
                    "locality": r.get("locality"),   # nice to include now
                    "lga": r.get("lga"),
                    "pay_period_start": pay_period.get("start") or "",
                    "pay_period_end": pay_period.get("end") or "",
                    "holiday_count_in_period": r.get("holiday_count_in_period"),
                    "holiday_dates_in_period": "; ".join(
                        h.get("date", "") for h in holidays_in_period if h.get("date")
                    ),
                })
            except Exception as e:
                results.append({
                    "row": idx,
                    "employee_id": employee_id,
                    "work_mode": work_mode,
                    "input_address": address.strip(),
                    "error": str(e),
                })

    out_df = pd.DataFrame(results)
    st.dataframe(out_df, use_container_width=True)

    st.download_button(
        "⬇️ Download results CSV",
        data=out_df.to_csv(index=False),
        file_name="payroll_holiday_check_results.csv",
        mime="text/csv",
    )


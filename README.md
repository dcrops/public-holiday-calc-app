# Australian Address → LGA & Public Holidays

A production-ready Streamlit application that resolves Australian addresses to LGAs and determines applicable public holidays, including state and regional variations, with a transparent audit trail and confidence indicators.

This tool is designed for **payroll, HR, and compliance support**, where public holiday applicability depends on *location*, *work mode*, and *local rules*.

---

## ✨ Key Features

- 🇦🇺 **Australian address geocoding**
  - Google Geocoding API with local SQLite caching
  - Strict validation to prevent false-positive matches
  - Supports street-level and suburb/postcode inputs with confidence signalling

- 🏛️ **LGA resolution**
  - Nationwide coverage using ASGS Edition 3 Non-ABS Structures
  - Polygon-based spatial lookup (no postcode shortcuts)

- 📅 **Public holiday calculation**
  - National & state holidays via Nager.Date
  - Regional and local holidays via data-driven CSV rules
  - Supports holiday replacements (e.g. Melbourne Cup Day substitutions)

- 🏢🏠 **OFFICE vs HOME payroll logic**
  - Calculates applicable holidays based on employee work location
  - Supports hybrid and remote work scenarios

- 📦 **Batch CSV processing**
  - Upload payroll-style CSVs
  - Export auditable results
  - Per-row status, confidence score, and audit messages

- 🔍 **Audit & confidence model**
  - Explicit status per lookup: `OK`, `LOW_CONFIDENCE`, `NOT_FOUND`
  - Manual review flag where appropriate
  - Clear explanation of how each result was derived

---

## 🚦 Why this exists

Public holiday applicability in Australia is **not always state-wide**.

Examples include:
- Victorian LGAs that observe local holidays instead of Melbourne Cup Day
- Regional festivals applying only to specific towns or councils
- Hybrid work arrangements affecting payroll obligations

This tool helps answer:

> *“Which public holidays apply to this employee, and how confident are we in that answer?”*

It is intended as **decision-support**, not an automated payroll engine.

---

## Known Limitations

- Public holiday observance in Australia is not uniform and may vary by state, LGA, locality, industry, award, or enterprise agreement.

- Some state-declared holidays (e.g. Melbourne Cup Day in Victoria) are **regionally substituted** and do not apply uniformly across all LGAs or localities.  
  This tool relies on curated regional rules to model these substitutions where known.

- Regional holiday coverage depends on maintained rule data and may not be exhaustive or up to date for all locations.

- Address geocoding may return approximate results for ambiguous or incomplete addresses.

- This tool flags **potential payroll risk** for review and does not determine legal entitlement.

---

## 🧠 Status & Confidence Model

Each lookup returns:

| Status | Meaning |
|------|--------|
| `OK` | High-confidence address resolution |
| `LOW_CONFIDENCE` | Approximate resolution (manual review recommended) |
| `NOT_FOUND` | Address could not be resolved safely |

Confidence scores are **directional**, not absolute, and are surfaced transparently in both the UI and batch outputs.

---

## 🔐 Data & Privacy

- No employee names or payroll values are required
- Uploaded CSVs are processed **in memory**
- No payroll data is persisted
- Local cache stores only:
  - formatted address
  - latitude / longitude
  - state, postcode, locality
- All geocoding is performed via Google Maps API

The app is designed with **privacy-by-default** principles.

---

## 📄 Batch CSV Format

Example input:

```csv
employee_id,office_address,home_address,work_mode,year,start_date,end_date
E001,"1 Collins St, Melbourne VIC 3000","",OFFICE,2025,2025-01-01,2025-12-31
E002,"","Brunswick VIC 3056",HOME,2025,2025-01-01,2025-12-31

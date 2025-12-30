🇦🇺 AU Address → LGA & Public Holidays

A production-ready Streamlit application that resolves Australian public holidays for a given address — including state, LGA-level, and locality-specific regional holidays — with support for payroll validation and batch processing.

Why this exists

Australian public holidays are not uniform. Many apply only to specific LGAs or even individual towns (e.g. regional show days).
Most holiday APIs stop at the state level — this app explicitly models and resolves those real-world edge cases.

✨ Features
🔍 Address Resolution

Geocodes Australian addresses using the Google Geocoding API

Extracts:

State / Territory

Locality (suburb / town)

Postcode

Resolves Local Government Area (LGA) via spatial lookup

🗺️ Accurate LGA Mapping (AU-wide)

Uses a precomputed, simplified GeoJSON artifact (~11.5 MB)

Covers all Australian LGAs

Designed for fast startup and cloud deployment
(no large GIS files required at runtime)

📅 Public Holiday Coverage

National & State holidays via Nager.Date

Regional holidays via curated rules:

LGA-based (e.g. Ballarat Cup Day)

Locality-based (e.g. Cairns Show Day)

Postcode-based (optional)

🧾 Payroll-Aware Logic

OFFICE vs HOME work-location handling

Optional pay-period filtering

Per-employee holiday counts

📦 Batch Mode (CSV)

Upload payroll CSVs with mixed states and locations

Per-row validation (one bad row won’t fail the batch)

Export payroll-ready results

⚡ Performance & Reliability

SQLite-backed geocode caching

Deterministic, repeatable results

Optimised for Render deployment

🧠 How Holiday Resolution Works

Holidays are resolved in layers:

Base holidays

National + state/territory public holidays

Regional rules

Applied when the address matches:

an LGA

a locality

or a postcode

Merge & de-duplication

Regional holidays supplement base holidays where applicable

This mirrors how Australian payroll and award compliance works in practice.

🏛️ State vs LGA vs Locality Holidays
Level	Applies To	Example
State	Entire state / territory	VIC Labour Day
LGA	Entire council area	Ballarat Cup Day
Locality	Specific town / suburb	Cairns Show Day

Some holidays apply to a town but not the entire council.
This app models that distinction explicitly.

📌 Example Use Case

A payroll team needs to validate whether an employee working from Ballarat during November 2025 is entitled to a local public holiday.

Standard holiday APIs miss Ballarat Cup Day

This app:

resolves the employee’s LGA

applies the correct regional rule

includes the holiday in payroll calculations

🧪 Usage & Testing
Single Lookup

Returns all applicable holidays for a selected year

Intended for exploratory checks and validation

Batch Mode

Supports pay-period filtering

Intended for payroll and compliance validation

Mixed states and locations supported

📂 Project Structure
address-holidays-app/
├── data/
│   ├── lga_2025_simplified.geojson
│   ├── regional_holidays_2025.csv
├── scripts/
│   └── build_lga_artifact.py
├── src/
│   └── address_holidays/
│       ├── geocode_google.py
│       ├── geocode_cache.py
│       ├── lga_lookup.py
│       ├── regional_rules.py
│       └── service.py
├── streamlit_app.py
├── requirements.txt
└── README.md

🛠️ Tech Stack

Python

Streamlit

Google Geocoding API

Nager.Date

GeoPandas / Shapely

SQLite

Render

⚠️ Known Limitations

Regional holidays are curated, not exhaustive

Polygon simplification may affect addresses very close to LGA boundaries

SQLite cache is ephemeral on Render (by design)

These trade-offs are intentional and documented.
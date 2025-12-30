🇦🇺 Address → LGA & Public Holidays (Australia)

A production-ready Streamlit application that resolves Australian public holidays for a given address — including state, LGA-level, and locality-specific regional holidays — with support for payroll validation and batch processing.

This tool is designed to handle real-world edge cases that standard holiday APIs often miss, such as regional show days and council-specific race days.

✨ Features
🔍 Address Resolution

Geocodes Australian addresses using Google Geocoding API

Extracts:

State / Territory

Locality (suburb / town)

Postcode

Resolves Local Government Area (LGA) via spatial lookup

🗺️ Accurate LGA Mapping (AU-wide)

Uses a precomputed, simplified GeoJSON artifact (~11.5 MB)

Supports all Australian LGAs

Designed for fast startup and cloud deployment (no large GIS files at runtime)

📅 Public Holiday Coverage

National & State holidays via Nager.Date

Regional holidays via curated rules:

LGA-based (e.g. Ballarat Cup Day)

Locality-based (e.g. Cairns Show Day)

Postcode-based (optional)

🧾 Payroll-Aware Logic

OFFICE vs HOME work location handling

Optional pay-period filtering

Per-employee holiday counts

📦 Batch Mode (CSV)

Upload a payroll CSV

Mixed states and locations supported

Per-row error handling (one bad row won’t fail the batch)

Export payroll-ready results

⚡ Performance & Reliability

SQLite-backed geocode caching

Deterministic results

Render-friendly deployment (no large runtime downloads)

🧠 How Holiday Logic Works

Holidays are resolved in layers:

Base holidays

National + state/territory public holidays

Regional rules

Applied if the address matches:

an LGA

a locality (town/suburb)

or a postcode

De-duplication

Regional holidays override or supplement base holidays where applicable

This layered approach mirrors how payroll systems must handle Australian award compliance.

🏛️ State vs LGA vs Locality Holidays
Level	Applies To	Example
State	Entire state/territory	VIC Labour Day
LGA	Entire council area	Ballarat Cup Day
Locality	Specific town/suburb	Cairns Show Day

Some holidays apply only to a town (not the whole council).
This app models that distinction explicitly.

🚀 Live Deployment

The app is deployed on Render as a Web Service.

Key deployment considerations:

No large .gpkg files committed to Git

Simplified GeoJSON artifact used at runtime

Environment variables injected via Render

🧪 Testing Approach
Single Lookup

Returns all applicable holidays for a selected year

Intended for exploratory checks

Batch Mode

Supports pay-period filtering

Intended for payroll validation

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
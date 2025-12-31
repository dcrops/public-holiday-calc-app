# 🇦🇺 AU Address → LGA & Public Holidays

A production-ready **Streamlit application** that resolves Australian public holidays for a given address — including **state**, **LGA-level**, and **locality-specific regional holidays** — with support for **payroll validation** and **batch processing**.

This tool is designed to handle real-world edge cases that standard holiday APIs often miss, such as **regional show days**, **council race days**, and **local observances**.

---

## ✨ Features

### 📍 Address Resolution
Geocodes Australian addresses using the **Google Geocoding API**, extracting:
- State / Territory
- Locality (suburb / town)
- Postcode
- Latitude / Longitude

---

### 🗺️ Accurate LGA Mapping (AU-wide)
- Resolves **Local Government Area (LGA)** via spatial point-in-polygon lookup
- Uses a **precomputed, simplified GeoJSON artifact (~11.5 MB)**
- Covers **all Australian LGAs**
- Optimised for fast startup and cloud deployment  
  *(no large GIS files at runtime)*

---

### 📅 Public Holiday Coverage

#### National & State Holidays
- Sourced from **Nager.Date**
- Automatically filtered by state / territory

#### Regional Holidays (Curated Rules)
Supports holidays that are **not reliably available via public APIs**, including:
- **LGA-based** holidays (e.g. *Ballarat Cup Day*)
- **Locality-based** holidays (e.g. *Cairns Show Day*)
- Optional postcode-based rules

Rules are explicitly modelled to avoid silent over- or under-application.

---

### 💼 Payroll-Aware Logic
- Supports **OFFICE vs HOME** work locations
- Optional **pay-period filtering**
- Clearly differentiates:
  - State holidays
  - Regional (LGA / locality) holidays
- Designed for auditability and compliance

---

### 📦 Batch Processing (CSV)
Upload a CSV to validate public holidays across multiple employees.

Supports:
- OFFICE / HOME work modes
- Row-level overrides (year, pay period)
- Per-row error isolation
- CSV export of results

A downloadable template is included in the UI.

---

## 🧠 Why This Exists

Australian public holidays are **not uniform**.

Many payroll systems:
- Rely only on state-level calendars
- Ignore LGA or locality-specific holidays
- Break down for remote and hybrid workforces

These gaps have historically led to **large-scale payroll underpayments** across major Australian employers.

This application demonstrates how to **correctly model and resolve** those edge cases in a deterministic, explainable way.

---

## 🏗️ Architecture Overview

### `streamlit_app.py`
- UI layer
- Handles user input and batch uploads
- Displays resolved holidays and payroll metrics

### `service.py`
- Orchestrates the full lookup flow:
  - Geocoding
  - LGA resolution
  - Holiday retrieval
  - Regional rule application
  - Pay-period filtering

### `geocode_google.py`
- Google Geocoding API integration
- Extracts structured address components
- Includes SQLite-based caching

### `lga_lookup.py`
- Spatial LGA resolution using simplified GeoJSON
- Point-in-polygon lookup
- Cached in memory per app process

### `holidays_au.py`
- Fetches AU public holidays from Nager.Date
- Filters by subdivision (state / territory)

### `regional_rules.py`
- Loads curated regional holiday rules from CSV
- Matches rules by:
  - State
  - LGA
  - Locality
  - Postcode (optional)
- Merges regional holidays with base holidays

---

## 📂 Regional Holiday Rules

Curated rules live in:


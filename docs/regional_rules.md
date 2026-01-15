# Regional Holiday Rules – Authoring Guide

This document explains how to author **regional holiday rules** used by the app to supplement national/state calendars.

The biggest source of mistakes is confusing **LGA (council area)** with **LOCALITY (suburb/town)**.

---

## Rule matching types

### 1) LGA
Use when a holiday applies to the **entire Local Government Area**.

Examples:
- Ballarat
- Greater Geelong
- Albury
- Merri-bek

**Must match the ASGS LGA name** used by the geospatial lookup (case/spacing/punctuation matter unless the app canonicalises names).

---

### 2) LOCALITY
Use when a holiday applies to a **specific suburb or town** (not the whole council area).

Examples:
- Cairns
- Brunswick East
- Lavington

**Must match the Google Geocoding `locality` output** (the suburb/town field).

Tip: If unsure, run a single lookup in the UI and copy the `locality` value.

---

### 3) POSTCODE
Use only when a holiday is officially defined by **postcode**.

This is rare. Prefer LGA or LOCALITY when possible.

---

## Common mistakes (avoid these)

❌ Using council-style labels as LOCALITY  
Examples of suspicious LOCALITY values:
- "City of …"
- "Shire of …"
- "Council"
- "Municipality"

❌ Putting a suburb into an LGA rule  
(Suburbs are LOCALITY. LGAs are council boundaries.)

❌ Assuming LOCALITY and LGA are interchangeable  
They often overlap, but they are not the same concept.

---

## Rule authoring checklist

Before adding a new rule:

1. Decide the scope:
   - Council-wide → **LGA**
   - Suburb/town-only → **LOCALITY**
   - Postcode-only → **POSTCODE**

2. Verify your match value:
   - For **LGA**: confirm it matches the app’s resolved LGA name.
   - For **LOCALITY**: confirm it matches Google’s `locality` value for a representative address.

3. Add the smallest rule that accurately describes the holiday.

---

## Non-goals

These rules are not intended to model:
- employer-specific holidays
- industry-specific holidays
- enterprise agreements or bespoke arrangements

The app is a **risk flagging tool**, not a legal decision engine.

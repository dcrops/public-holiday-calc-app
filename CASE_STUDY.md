# Case Study
## Preventing Payroll Underpayment via Location-Aware Public Holiday Resolution

### Problem
Australian public holidays are **not uniform**. While national and state holidays are well understood, many public holidays apply only to specific **Local Government Areas (LGAs)** or even individual **towns or suburbs** (for example, regional race days and agricultural show days).

Most payroll systems:
- Rely on **state-level holiday calendars**
- Do not account for **LGA- or locality-specific observances**
- Struggle with **remote and hybrid work arrangements**

These gaps have led to **systemic payroll underpayments**, large-scale remediation programs, and regulatory scrutiny across major Australian employers, including banks.

---

### Objective
Design and implement a **deterministic, explainable system** that accurately resolves public holidays for Australian employees based on their **actual work location**, including:
- State-wide holidays
- LGA-level regional holidays
- Locality-specific observances

The solution needed to be:
- Auditable
- Payroll-safe
- Resistant to silent misclassification
- Deployable in a cloud environment

---

### Solution Overview
I built a production-ready application that resolves public holidays for Australian addresses by combining:

- **Geocoding**
  - Converts free-text addresses into structured location data (state, locality, postcode, latitude/longitude)

- **Spatial LGA Resolution**
  - Determines the governing LGA using point-in-polygon spatial lookup

- **Layered Holiday Logic**
  - National and state holidays sourced from **Nager.Date**
  - Regional holidays modelled explicitly via curated rules:
    - LGA-scoped
    - Locality-scoped
    - Postcode-scoped (optional)

- **Payroll-Aware Processing**
  - OFFICE vs HOME work location handling
  - Optional pay-period filtering
  - Batch CSV processing with per-row error isolation

---

### Key Design Decisions

#### Explicit Scope Modelling
Rather than assuming all holidays are state-wide, the system distinguishes between:
- **State** holidays (apply to everyone in a state)
- **LGA** holidays (apply to an entire council)
- **Locality** holidays (apply only to a specific town or suburb)

This avoids common over-application or under-application errors.

---

#### Conservative Matching
Holiday rules match on **exact, normalised identifiers**:
- State
- LGA
- Locality
- Postcode

No fuzzy matching or heuristic

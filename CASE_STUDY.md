
---

# 📄 `CASE_STUDY.md`

```markdown
# Case Study: Australian Address → LGA & Public Holidays

## Overview

This project was built to address a recurring real-world problem in Australian payroll and HR systems:

> **Public holiday applicability is often location-specific and difficult to automate correctly.**

The goal was to build a tool that prioritises **correctness, transparency, and auditability** over silent automation.

---

## Problem Statement

Australian public holidays can vary by:
- State
- Local Government Area (LGA)
- Locality or postcode
- Replacement rules (e.g. local holidays replacing Melbourne Cup Day)
- Employee work location (OFFICE vs HOME)

Many systems:
- Assume state-wide applicability
- Rely on postcodes instead of spatial boundaries
- Silently accept approximate address matches

This creates compliance and payroll risk.

---

## Design Goals

1. **No false positives**
   - It is better to return `NOT_FOUND` than an incorrect LGA
2. **Explicit confidence**
   - Every result should communicate how trustworthy it is
3. **Auditability**
   - Each decision must be explainable after the fact
4. **Data-driven rules**
   - Regional holidays should be configurable without code changes
5. **Low operational complexity**
   - Minimal infrastructure, easy local or hosted deployment

---

## Architecture Summary

1. **Geocoding**
   - Google Geocoding API
   - Local SQLite cache to reduce API calls
   - Strict validation to reject vague or centroid-only matches

2. **Spatial LGA Resolution**
   - ASGS Edition 3 Non-ABS Structures
   - Polygon-based point-in-area lookup

3. **Holiday Calculation**
   - Base national/state holidays via Nager.Date
   - Regional and replacement holidays via CSV rule engine

4. **Confidence & Audit Layer**
   - Status classification (`OK`, `LOW_CONFIDENCE`, `NOT_FOUND`)
   - Confidence score
   - Manual review flag
   - Human-readable audit message

5. **User Interface**
   - Streamlit UI for single lookups
   - Batch CSV processing for payroll scenarios
   - Debug and audit views for validation

---

## Key Technical Challenges

### 1. Preventing False Positives
Google will often resolve invalid addresses to:
- Postcode centroids
- State-level locations

The solution was to:
- Detect user intent (street-level vs suburb-level)
- Reject matches that do not meet the required granularity
- Surface uncertainty explicitly instead of guessing

---

### 2. Regional Holiday Replacement Logic
Some LGAs observe:
- A local holiday **instead of** a state holiday

The system supports:
- Rule-based replacements
- Explicit tracking of which holidays were removed or added
- Audit visibility for downstream review

---

### 3. Trust & Compliance Considerations
Payroll users need to know:
- *Why* a holiday was included
- *How confident* the system is
- *What to review manually*

This led to a design that prefers:
- Conservative results
- Clear warnings
- Zero silent assumptions

---

## Outcomes

- Fully functional production-ready prototype
- Handles valid, ambiguous, and invalid addresses correctly
- Supports both interactive and batch payroll workflows
- Provides a defensible audit trail suitable for compliance review

---

## Lessons Learned

- Correctness beats automation in compliance-heavy domains
- Confidence signalling is as important as the result itself
- Data-driven rule engines scale better than hard-coded logic
- “Failing safely” builds trust faster than appearing smart

---

## Future Considerations

If extended further, this project could:
- Expose an internal API
- Support alternative geocoding providers
- Add role-based access controls
- Support customer-managed data hosting

These were intentionally out of scope for the initial build.

---

## Final Note

This project was built as a **problem-focused engineering exercise**, prioritising clarity, correctness, and trust over feature count or speed.

It demonstrates an approach suitable for regulated or compliance-adjacent environments.

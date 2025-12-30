from __future__ import annotations

import pandas as pd
from datetime import date

CSV_PATH = "data/important-dates-vic-2025.csv"


def get_vic_public_holidays(year: int) -> list[dict]:
    """
    Return VIC public holidays for the given year.
    """
    df = pd.read_csv(CSV_PATH)

    # Filter to public holidays
    holidays = df[df["dateType"].astype(str).str.upper() == "PUBLIC_HOLIDAY"].copy()

    # Parse dates
    holidays["important_date"] = pd.to_datetime(
        holidays["important_date"], errors="coerce"
    )

    # Filter by year
    holidays = holidays[holidays["important_date"].dt.year == year]

    # Sort by date
    holidays = holidays.sort_values("important_date")

    return [
        {
            "date": d.date().isoformat(),
            "name": name,
        }
        for d, name in zip(
            holidays["important_date"],
            holidays["name"],
        )
    ]

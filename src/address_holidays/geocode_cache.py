from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path("cache/geocode_cache.db")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS geocode_cache (
            cache_key TEXT PRIMARY KEY,
            formatted_address TEXT,
            lat REAL,
            lon REAL,
            state TEXT,
            postcode TEXT,
            locality TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    # Migration: add locality column if DB already exists
    try:
        conn.execute("ALTER TABLE geocode_cache ADD COLUMN locality TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    return conn



def get_cached(cache_key: str) -> Optional[dict]:
    conn = _connect()
    try:
        cur = conn.execute(
            """
            SELECT formatted_address, lat, lon, state, postcode, locality
            FROM geocode_cache
            WHERE cache_key = ?
            """,
            (cache_key,),
        )

        row = cur.fetchone()
        if not row:
            return None
        return {
            "formatted_address": row[0],
            "lat": row[1],
            "lon": row[2],
            "state": row[3],
            "postcode": row[4],
            "locality": row[5],
        }
    finally:
        conn.close()


def set_cached(cache_key: str, geo: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO geocode_cache
            (cache_key, formatted_address, lat, lon, state, postcode, locality)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                geo.get("formatted_address"),
                geo.get("lat"),
                geo.get("lon"),
                geo.get("state"),
                geo.get("postcode"),
                geo.get("locality"),
            ),
        )

        conn.commit()
    finally:
        conn.close()

#!/usr/bin/env python3
"""Create tables and seed Health_Impact reference data."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import text

from backend.config import config
from backend.db import get_engine

IMPACT_ROWS = [
    ("0-50", 0, 50, "Good", "Minimal health impact.", "Enjoy outdoor activities."),
    ("51-100", 51, 100, "Satisfactory", "Minor breathing discomfort for sensitive groups.", "Limit prolonged outdoor exertion if sensitive."),
    ("101-200", 101, 200, "Moderate", "Breathing discomfort to people with lung/heart disease.", "Use masks if sensitive; reduce outdoor exercise."),
    ("201-300", 201, 300, "Poor", "Breathing discomfort to most people on prolonged exposure.", "Avoid outdoor exercise; keep windows closed."),
    ("301-400", 301, 400, "Very Poor", "Respiratory illness on prolonged exposure.", "Stay indoors; use air purifiers if available."),
    ("401-500", 401, 500, "Severe", "Serious health impacts for all.", "Avoid all outdoor activity; follow government advisories."),
]


def main() -> None:
    from backend.db import database_url as db_url

    use_sqlite = config.USE_SQLITE or db_url().startswith("sqlite")
    schema_file = _ROOT / "database" / ("schema.sql" if use_sqlite else "schema_mysql.sql")
    sql = schema_file.read_text(encoding="utf-8")
    engine = get_engine()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    with engine.begin() as conn:
        for stmt in sql.split(";"):
            chunk = stmt.strip()
            if chunk:
                conn.execute(text(chunk))

        for row in IMPACT_ROWS:
            if use_sqlite:
                conn.execute(
                    text(
                        """
                        INSERT OR IGNORE INTO Health_Impact
                        (aqi_range, min_aqi, max_aqi, category, health_effect, precautions)
                        VALUES (:a, :min_a, :max_a, :cat, :he, :pr)
                        """
                    ),
                    {
                        "a": row[0],
                        "min_a": row[1],
                        "max_a": row[2],
                        "cat": row[3],
                        "he": row[4],
                        "pr": row[5],
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT IGNORE INTO Health_Impact
                        (aqi_range, min_aqi, max_aqi, category, health_effect, precautions)
                        VALUES (:a, :min_a, :max_a, :cat, :he, :pr)
                        """
                    ),
                    {
                        "a": row[0],
                        "min_a": row[1],
                        "max_a": row[2],
                        "cat": row[3],
                        "he": row[4],
                        "pr": row[5],
                    },
                )

    print(f"Database initialized using {schema_file.name}")


if __name__ == "__main__":
    main()

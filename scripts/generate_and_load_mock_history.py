#!/usr/bin/env python3
"""Generate synthetic AQI history for demo / ML training."""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import text

from backend.db import get_engine

CATEGORIES = [
    (0, 50, "Good"),
    (51, 100, "Satisfactory"),
    (101, 200, "Moderate"),
    (201, 300, "Poor"),
    (301, 400, "Very Poor"),
    (401, 500, "Severe"),
]


def aqi_category(aqi: int) -> str:
    for lo, hi, name in CATEGORIES:
        if lo <= aqi <= hi:
            return name
    return "Severe"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    engine = get_engine()
    with engine.connect() as conn:
        city_ids = [r[0] for r in conn.execute(text("SELECT city_id FROM Cities")).all()]

    if not city_ids:
        print("No cities found. Run scripts/load_states_cities.py first.")
        sys.exit(1)

    now = datetime.utcnow().replace(microsecond=0)
    rows_to_insert = []
    for city_id in city_ids:
        base = random.randint(60, 180)
        for day in range(args.days):
            ts = now - timedelta(days=args.days - day)
            for hour in (6, 12, 18):
                t = ts.replace(hour=hour, minute=0, second=0)
                aqi = max(20, min(450, base + random.randint(-25, 25)))
                pm25 = round(aqi * random.uniform(0.35, 0.55), 2)
                pm10 = round(pm25 * random.uniform(1.4, 1.8), 2)
                rows_to_insert.append({
                    "city_id": city_id,
                    "timestamp": t.isoformat(sep=" ", timespec="seconds"),
                    "pm25": pm25,
                    "pm10": pm10,
                    "no2": round(random.uniform(10, 80), 2),
                    "so2": round(random.uniform(5, 40), 2),
                    "co": round(random.uniform(0.2, 2.5), 2),
                    "o3": round(random.uniform(20, 90), 2),
                    "aqi_value": aqi,
                    "aqi_category": aqi_category(aqi),
                    "source": "mock",
                })

    insert_sql = text(
        """
        INSERT INTO AQI_Data
        (city_id, timestamp, pm25, pm10, no2, so2, co, o3, aqi_value, aqi_category, source)
        VALUES
        (:city_id, :timestamp, :pm25, :pm10, :no2, :so2, :co, :o3, :aqi_value, :aqi_category, :source)
        """
    )

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM AQI_Data WHERE source = 'mock'"))
        conn.execute(insert_sql, rows_to_insert)

    print(f"Inserted {len(rows_to_insert)} mock readings over {args.days} days.")


if __name__ == "__main__":
    main()

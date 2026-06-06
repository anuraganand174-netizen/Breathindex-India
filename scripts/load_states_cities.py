#!/usr/bin/env python3
"""Load Indian states and major cities (idempotent)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import text

from backend.db import get_engine

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal",
]

# state_name -> [(city, lat, lon), ...]
CITIES: dict[str, list[tuple[str, float, float]]] = {
    "Delhi": [("New Delhi", 28.6139, 77.2090), ("Dwarka", 28.5921, 77.0460)],
    "Maharashtra": [("Mumbai", 19.0760, 72.8777), ("Pune", 18.5204, 73.8567), ("Nagpur", 21.1458, 79.0882)],
    "Karnataka": [("Bengaluru", 12.9716, 77.5946), ("Mysuru", 12.2958, 76.6394)],
    "Tamil Nadu": [("Chennai", 13.0827, 80.2707), ("Coimbatore", 11.0168, 76.9558)],
    "West Bengal": [("Kolkata", 22.5726, 88.3639)],
    "Gujarat": [("Ahmedabad", 23.0225, 72.5714), ("Surat", 21.1702, 72.8311)],
    "Uttar Pradesh": [("Lucknow", 26.8467, 80.9462), ("Kanpur", 26.4499, 80.3319), ("Noida", 28.5355, 77.3910)],
    "Rajasthan": [("Jaipur", 26.9124, 75.7873), ("Jodhpur", 26.2389, 73.0243)],
    "Telangana": [("Hyderabad", 17.3850, 78.4867)],
    "Kerala": [("Thiruvananthapuram", 8.5241, 76.9366), ("Kochi", 9.9312, 76.2673)],
    "Punjab": [("Chandigarh", 30.7333, 76.7794), ("Ludhiana", 30.9010, 75.8573)],
    "Madhya Pradesh": [("Bhopal", 23.2599, 77.4126), ("Indore", 22.7196, 75.8577)],
    "Bihar": [("Patna", 25.5941, 85.1376)],
    "Haryana": [("Gurugram", 28.4595, 77.0266), ("Faridabad", 28.4089, 77.3178)],
}


def _insert_state(conn, name: str) -> int:
    if "sqlite" in str(conn.engine.url):
        conn.execute(text("INSERT OR IGNORE INTO States (state_name) VALUES (:n)"), {"n": name})
    else:
        conn.execute(text("INSERT IGNORE INTO States (state_name) VALUES (:n)"), {"n": name})
    return conn.execute(
        text("SELECT state_id FROM States WHERE state_name = :n"), {"n": name}
    ).scalar_one()


def main() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        for state in STATES:
            _insert_state(conn, state)
        for state_name, cities in CITIES.items():
            sid = conn.execute(
                text("SELECT state_id FROM States WHERE state_name = :n"),
                {"n": state_name},
            ).scalar_one()
            for city_name, lat, lon in cities:
                if "sqlite" in str(conn.engine.url):
                    conn.execute(
                        text(
                            """
                            INSERT OR IGNORE INTO Cities (city_name, state_id, latitude, longitude)
                            VALUES (:c, :s, :lat, :lon)
                            """
                        ),
                        {"c": city_name, "s": sid, "lat": lat, "lon": lon},
                    )
                else:
                    conn.execute(
                        text(
                            """
                            INSERT IGNORE INTO Cities (city_name, state_id, latitude, longitude)
                            VALUES (:c, :s, :lat, :lon)
                            """
                        ),
                        {"c": city_name, "s": sid, "lat": lat, "lon": lon},
                    )
    print("States and cities loaded.")


if __name__ == "__main__":
    main()

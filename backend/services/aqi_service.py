"""AQI queries: states, cities, readings, aggregates."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_states(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        text("SELECT state_id, state_name FROM States ORDER BY state_name")
    ).mappings().all()
    return [dict(r) for r in rows]


def list_cities(session: Session, state_id: int | None = None) -> list[dict[str, Any]]:
    if state_id is not None:
        rows = session.execute(
            text(
                """
                SELECT c.city_id, c.city_name, c.state_id, s.state_name,
                       c.latitude, c.longitude
                FROM Cities c
                JOIN States s ON s.state_id = c.state_id
                WHERE c.state_id = :state_id
                ORDER BY c.city_name
                """
            ),
            {"state_id": state_id},
        ).mappings().all()
    else:
        rows = session.execute(
            text(
                """
                SELECT c.city_id, c.city_name, c.state_id, s.state_name,
                       c.latitude, c.longitude
                FROM Cities c
                JOIN States s ON s.state_id = c.state_id
                ORDER BY s.state_name, c.city_name
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def latest_reading(session: Session, city_id: int) -> dict[str, Any] | None:
    row = session.execute(
        text(
            """
            SELECT d.id, d.city_id, d.timestamp, d.pm25, d.pm10, d.no2, d.so2,
                   d.co, d.o3, d.aqi_value, d.aqi_category, d.source,
                   c.city_name, s.state_name
            FROM AQI_Data d
            JOIN Cities c ON c.city_id = d.city_id
            JOIN States s ON s.state_id = c.state_id
            WHERE d.city_id = :city_id
            ORDER BY d.timestamp DESC
            LIMIT 1
            """
        ),
        {"city_id": city_id},
    ).mappings().first()
    return dict(row) if row else None


def history(
    session: Session,
    city_id: int,
    days: int = 30,
) -> list[dict[str, Any]]:
    since = datetime.utcnow() - timedelta(days=max(1, days))
    rows = session.execute(
        text(
            """
            SELECT id, city_id, timestamp, pm25, pm10, no2, so2, co, o3,
                   aqi_value, aqi_category, source
            FROM AQI_Data
            WHERE city_id = :city_id AND timestamp >= :since
            ORDER BY timestamp ASC
            """
        ),
        {"city_id": city_id, "since": since.isoformat(sep=" ", timespec="seconds")},
    ).mappings().all()
    return [dict(r) for r in rows]


def summary_stats(session: Session) -> dict[str, Any]:
    row = session.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*) FROM States) AS states,
              (SELECT COUNT(*) FROM Cities) AS cities,
              (SELECT COUNT(*) FROM AQI_Data) AS readings,
              (SELECT MAX(timestamp) FROM AQI_Data) AS latest_reading
            """
        )
    ).mappings().first()
    return dict(row) if row else {}

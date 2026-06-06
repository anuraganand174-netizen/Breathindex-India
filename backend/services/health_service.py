"""Health impact lookup by AQI value."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def all_impacts(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT aqi_range, min_aqi, max_aqi, category,
                   health_effect, precautions
            FROM Health_Impact
            ORDER BY min_aqi
            """
        )
    ).mappings().all()
    return [dict(r) for r in rows]


def impact_for_aqi(session: Session, aqi: int) -> dict[str, Any] | None:
    row = session.execute(
        text(
            """
            SELECT aqi_range, min_aqi, max_aqi, category,
                   health_effect, precautions
            FROM Health_Impact
            WHERE :aqi BETWEEN min_aqi AND max_aqi
            LIMIT 1
            """
        ),
        {"aqi": aqi},
    ).mappings().first()
    return dict(row) if row else None

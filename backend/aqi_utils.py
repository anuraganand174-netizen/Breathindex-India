"""Indian AQI (NAQI-style) categories and colors."""
from __future__ import annotations


def category_from_aqi(aqi: int | None) -> str:
    if aqi is None:
        return "Unknown"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


def color_from_aqi(aqi: int | None) -> str:
    if aqi is None:
        return "#64748b"
    if aqi <= 50:
        return "#22c55e"
    if aqi <= 100:
        return "#84cc16"
    if aqi <= 200:
        return "#eab308"
    if aqi <= 300:
        return "#f97316"
    if aqi <= 400:
        return "#ef4444"
    return "#991b1b"


def level_label(aqi: int | None) -> str:
    if aqi is None:
        return "unknown"
    if aqi <= 50:
        return "good"
    if aqi <= 100:
        return "moderate"
    if aqi <= 200:
        return "unhealthy_sensitive"
    if aqi <= 300:
        return "unhealthy"
    return "hazardous"

"""Real-time AQI from Open-Meteo (free, no API key). Cached server-side."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.aqi_utils import category_from_aqi, color_from_aqi

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
CACHE_TTL_SEC = 600  # 10 minutes
_map_cache: dict[str, Any] = {"ts": 0, "data": []}
_city_cache: dict[int, dict[str, Any]] = {}


def _fetch_coords(lat: float, lon: float) -> dict[str, Any] | None:
    try:
        resp = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "us_aqi,pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone",
                "timezone": "auto",
            },
            timeout=12,
        )
        resp.raise_for_status()
        payload = resp.json()
        cur = payload.get("current") or {}
        aqi = cur.get("us_aqi")
        if aqi is None and cur.get("pm2_5") is not None:
            aqi = int(round(float(cur["pm2_5"]) * 2.5))
        if aqi is None:
            return None
        aqi = int(max(0, min(500, round(float(aqi)))))
        return {
            "aqi_value": aqi,
            "aqi_category": category_from_aqi(aqi),
            "aqi_color": color_from_aqi(aqi),
            "pm25": cur.get("pm2_5"),
            "pm10": cur.get("pm10"),
            "no2": cur.get("nitrogen_dioxide"),
            "so2": cur.get("sulphur_dioxide"),
            "co": cur.get("carbon_monoxide"),
            "o3": cur.get("ozone"),
            "observed_at": cur.get("time") or datetime.now(timezone.utc).isoformat(),
            "source": "open_meteo_live",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo fetch failed lat=%s lon=%s: %s", lat, lon, exc)
        return None


def _city_row_to_live(city: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    return {
        **live,
        "city_id": city["city_id"],
        "city_name": city["city_name"],
        "state_id": city["state_id"],
        "state_name": city["state_name"],
        "latitude": city["latitude"],
        "longitude": city["longitude"],
    }


def get_live_for_city(session: Session, city_id: int, force: bool = False) -> dict[str, Any]:
    now = time.time()
    if not force and city_id in _city_cache:
        entry = _city_cache[city_id]
        if now - entry.get("_ts", 0) < CACHE_TTL_SEC:
            return {k: v for k, v in entry.items() if k != "_ts"}

    row = session.execute(
        text(
            """
            SELECT c.city_id, c.city_name, c.state_id, s.state_name,
                   c.latitude, c.longitude
            FROM Cities c
            JOIN States s ON s.state_id = c.state_id
            WHERE c.city_id = :cid
            """
        ),
        {"cid": city_id},
    ).mappings().first()
    if not row:
        return {"ok": False, "error": "City not found"}
    city = dict(row)
    lat, lon = city.get("latitude"), city.get("longitude")
    if lat is None or lon is None:
        return {"ok": False, "error": "City has no coordinates for live feed"}

    live = _fetch_coords(float(lat), float(lon))
    if not live:
        db_latest = session.execute(
            text(
                """
                SELECT aqi_value, aqi_category, pm25, pm10, no2, so2, co, o3,
                       timestamp AS observed_at, source
                FROM AQI_Data WHERE city_id = :cid
                ORDER BY timestamp DESC LIMIT 1
                """
            ),
            {"cid": city_id},
        ).mappings().first()
        if db_latest:
            data = dict(db_latest)
            data["ok"] = True
            data["fallback"] = True
            data["aqi_color"] = color_from_aqi(data.get("aqi_value"))
            data.update({k: city[k] for k in ("city_id", "city_name", "state_id", "state_name", "latitude", "longitude")})
            return data
        return {"ok": False, "error": "Live feed unavailable"}

    result = {"ok": True, "fallback": False, **_city_row_to_live(city, live)}
    _city_cache[city_id] = {**result, "_ts": now}
    _save_reading(session, city_id, live)
    return result


def get_map_data(session: Session, force: bool = False) -> dict[str, Any]:
    now = time.time()
    if not force and _map_cache["data"] and now - _map_cache["ts"] < CACHE_TTL_SEC:
        return {
            "ok": True,
            "cached": True,
            "updated_at": _map_cache.get("updated_at"),
            "data": _map_cache["data"],
        }

    cities = session.execute(
        text(
            """
            SELECT c.city_id, c.city_name, c.state_id, s.state_name,
                   c.latitude, c.longitude
            FROM Cities c
            JOIN States s ON s.state_id = c.state_id
            WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
            ORDER BY c.city_id
            """
        )
    ).mappings().all()
    city_list = [dict(c) for c in cities]
    results: list[dict[str, Any]] = []
    errors = 0

    def work(city: dict[str, Any]) -> dict[str, Any] | None:
        live = _fetch_coords(float(city["latitude"]), float(city["longitude"]))
        if not live:
            return None
        return _city_row_to_live(city, live)

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(work, c): c for c in city_list}
        for fut in as_completed(futures):
            item = fut.result()
            if item:
                results.append(item)
            else:
                errors += 1

    updated_at = datetime.now(timezone.utc).isoformat()
    _map_cache["ts"] = now
    _map_cache["data"] = results
    _map_cache["updated_at"] = updated_at

    return {
        "ok": True,
        "cached": False,
        "updated_at": updated_at,
        "count": len(results),
        "errors": errors,
        "data": results,
    }


def _save_reading(session: Session, city_id: int, live: dict[str, Any]) -> None:
    session.execute(
        text(
            """
            INSERT INTO AQI_Data
            (city_id, timestamp, pm25, pm10, no2, so2, co, o3, aqi_value, aqi_category, source)
            VALUES
            (:city_id, :ts, :pm25, :pm10, :no2, :so2, :co, :o3, :aqi, :cat, :src)
            """
        ),
        {
            "city_id": city_id,
            "ts": live.get("observed_at") or datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
            "pm25": live.get("pm25"),
            "pm10": live.get("pm10"),
            "no2": live.get("no2"),
            "so2": live.get("so2"),
            "co": live.get("co"),
            "o3": live.get("o3"),
            "aqi": live.get("aqi_value"),
            "cat": live.get("aqi_category"),
            "src": "open_meteo_live",
        },
    )
    session.commit()


def national_summary(map_points: list[dict[str, Any]]) -> dict[str, Any]:
    if not map_points:
        return {}
    aqis = [p["aqi_value"] for p in map_points if p.get("aqi_value") is not None]
    if not aqis:
        return {}
    avg = round(sum(aqis) / len(aqis))
    worst = max(map_points, key=lambda p: p.get("aqi_value") or 0)
    best = min(map_points, key=lambda p: p.get("aqi_value") or 999)
    return {
        "national_avg_aqi": avg,
        "national_avg_category": category_from_aqi(avg),
        "worst_city": worst.get("city_name"),
        "worst_aqi": worst.get("aqi_value"),
        "best_city": best.get("city_name"),
        "best_aqi": best.get("aqi_value"),
        "cities_reporting": len(aqis),
    }

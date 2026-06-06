"""Load sklearn/xgboost models from disk and predict AQI horizons."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import config


def _artifact_path(model_name: str, horizon: int) -> Path:
    return config.MODELS_DIR / f"global_{model_name}_h{horizon}.joblib"


def list_available_models() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not config.MODELS_DIR.exists():
        return out
    for path in sorted(config.MODELS_DIR.glob("global_*_h*.joblib")):
        stem = path.stem  # global_random_forest_h7 or global_xgboost_h7
        if "_h" not in stem:
            continue
        base, horizon_part = stem.rsplit("_", 1)
        if not horizon_part.startswith("h") or not base.startswith("global_"):
            continue
        out.append(
            {
                "model": base[len("global_") :],
                "horizon_days": int(horizon_part[1:]),
                "file": path.name,
            }
        )
    return out


def _feature_frame(session: Session, city_id: int, lookback: int = 14) -> pd.DataFrame | None:
    rows = session.execute(
        text(
            """
            SELECT timestamp, pm25, pm10, no2, so2, co, o3, aqi_value
            FROM AQI_Data
            WHERE city_id = :city_id
            ORDER BY timestamp DESC
            LIMIT :limit
            """
        ),
        {"city_id": city_id, "limit": lookback},
    ).mappings().all()
    if len(rows) < 3:
        return None
    df = pd.DataFrame([dict(r) for r in rows]).sort_values("timestamp")
    for col in ("pm25", "pm10", "no2", "so2", "co", "o3", "aqi_value"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.ffill().bfill()
    return df


def predict(
    session: Session,
    city_id: int,
    model_name: str = "random_forest",
    horizon: int = 7,
) -> dict[str, Any]:
    path = _artifact_path(model_name, horizon)
    if not path.exists():
        return {
            "ok": False,
            "error": f"Model not found: {path.name}. Run scripts/train_models.py on the server.",
            "city_id": city_id,
            "model": model_name,
            "horizon_days": horizon,
        }

    df = _feature_frame(session, city_id)
    if df is None or df.empty:
        return {"ok": False, "error": "Insufficient history for this city.", "city_id": city_id}

    feature_cols = ["pm25", "pm10", "no2", "so2", "co", "o3", "aqi_value"]
    latest = df[feature_cols].iloc[-1].values.reshape(1, -1)
    bundle = joblib.load(path)
    model = bundle["model"] if isinstance(bundle, dict) else bundle
    pred = int(round(float(model.predict(latest)[0])))
    pred = max(0, min(500, pred))

    latest_row = session.execute(
        text("SELECT aqi_value FROM AQI_Data WHERE city_id = :cid ORDER BY timestamp DESC LIMIT 1"),
        {"cid": city_id},
    ).scalar()

    return {
        "ok": True,
        "city_id": city_id,
        "model": model_name,
        "horizon_days": horizon,
        "current_aqi": int(latest_row) if latest_row is not None else None,
        "predicted_aqi": pred,
        "features_used": feature_cols,
    }

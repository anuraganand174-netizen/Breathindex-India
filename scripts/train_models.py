#!/usr/bin/env python3
"""Train global AQI forecast models (RandomForest / XGBoost) from DB history."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sqlalchemy import text
from xgboost import XGBRegressor

from backend.config import config
from backend.db import get_engine

FEATURES = ["pm25", "pm10", "no2", "so2", "co", "o3", "aqi_value"]


def load_dataset() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT city_id, timestamp, pm25, pm10, no2, so2, co, o3, aqi_value
                FROM AQI_Data
                ORDER BY city_id, timestamp
                """
            ),
            conn,
        )
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=FEATURES)
    return df


def build_xy(df: pd.DataFrame, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for _, grp in df.groupby("city_id"):
        g = grp.sort_values("timestamp").reset_index(drop=True)
        for i in range(len(g) - horizon):
            xs.append(g.loc[i, FEATURES].values)
            ys.append(g.loc[i + horizon, "aqi_value"])
    return np.array(xs), np.array(ys)


def train_one(name: str, x: np.ndarray, y: np.ndarray) -> object:
    if name == "random_forest":
        model = RandomForestRegressor(n_estimators=80, random_state=42, n_jobs=-1)
    elif name == "xgboost":
        model = XGBRegressor(
            n_estimators=120,
            max_depth=6,
            learning_rate=0.08,
            random_state=42,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Unknown model: {name}")
    x_tr, x_te, y_tr, y_te = train_test_split(x, y, test_size=0.2, random_state=42)
    model.fit(x_tr, y_tr)
    mae = mean_absolute_error(y_te, model.predict(x_te))
    print(f"  {name} MAE: {mae:.2f}")
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="db", choices=["db"])
    parser.add_argument("--models", default="random_forest,xgboost")
    parser.add_argument("--horizons", default="1,7,30")
    args = parser.parse_args()

    if args.source != "db":
        raise SystemExit("Only --source db is supported.")

    df = load_dataset()
    if df.empty:
        print("No training data. Run generate_and_load_mock_history.py first.")
        sys.exit(1)

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_names = [m.strip() for m in args.models.split(",") if m.strip()]
    horizons = [int(h.strip()) for h in args.horizons.split(",") if h.strip()]

    for horizon in horizons:
        x, y = build_xy(df, horizon)
        if len(x) < 50:
            print(f"Skipping horizon {horizon}: not enough samples ({len(x)}).")
            continue
        print(f"Horizon {horizon}d — samples: {len(x)}")
        for name in model_names:
            model = train_one(name, x, y)
            out = config.MODELS_DIR / f"global_{name}_h{horizon}.joblib"
            joblib.dump(
                {"model": model, "features": FEATURES, "horizon": horizon},
                out,
                compress=("gzip", 9),
            )
            print(f"  saved {out.name}")


if __name__ == "__main__":
    main()

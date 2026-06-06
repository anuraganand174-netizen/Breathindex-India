"""Application configuration from environment variables (12-factor)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: str = "*") -> list[str]:
    raw = os.getenv(name, default).strip()
    if raw == "*":
        return ["*"]
    return [part.strip() for part in raw.split(",") if part.strip()]


class Config:
  """Central config; safe defaults for local dev and Render."""

  ROOT_DIR: Path = _ROOT
  DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(_ROOT / "data"))).resolve()
  MODELS_DIR: Path = Path(os.getenv("MODELS_DIR", str(_ROOT / "models" / "artifacts"))).resolve()

  SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
  FLASK_DEBUG: bool = _bool("FLASK_DEBUG", False)

  USE_SQLITE: bool = _bool("USE_SQLITE", True)
  SQLITE_PATH: Path = Path(
      os.getenv("SQLITE_PATH", str(DATA_DIR / "aqi_local.db"))
  ).resolve()

  # MySQL / managed DB (Render, Railway, PlanetScale, etc.)
  MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
  MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
  MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
  MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
  MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "aqi_india")

  # Optional unified URL: mysql+pymysql://user:pass@host:3306/db
  DATABASE_URL: str | None = os.getenv("DATABASE_URL")

  CORS_ORIGINS: list[str] = _list("CORS_ORIGINS", "*")

  # Optional external AQI API
  OPENAQ_API_KEY: str | None = os.getenv("OPENAQ_API_KEY") or None


config = Config()

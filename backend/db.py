"""Database engine and session helpers (SQLite or MySQL via env)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import config

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def database_url() -> str:
    if config.DATABASE_URL:
        url = config.DATABASE_URL.strip()
        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+pymysql://", 1)
        return url
    if config.USE_SQLITE:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{config.SQLITE_PATH.as_posix()}"
    password = config.MYSQL_PASSWORD
    user = config.MYSQL_USER
    host = config.MYSQL_HOST
    port = config.MYSQL_PORT
    db = config.MYSQL_DATABASE
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        connect_args = {}
        if database_url().startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(
            database_url(),
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping() -> bool:
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return True

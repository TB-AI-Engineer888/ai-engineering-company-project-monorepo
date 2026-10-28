from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine
from tinydb import TinyDB

_API_DIR = Path(__file__).resolve().parent / "api"
load_dotenv(_API_DIR / ".env")

_tinydb: TinyDB | None = None
_engine: Engine | None = None


def tinydb_path() -> Path:
    configured = os.environ.get("TINYDB_PATH", "").strip()
    if configured:
        return Path(configured)
    return _API_DIR / "data" / "tinydb.json"


def get_tinydb() -> TinyDB:
    global _tinydb
    if _tinydb is None:
        path = tinydb_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _tinydb = TinyDB(path)
    return _tinydb


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            database_url(),
            poolclass=NullPool,
            pool_pre_ping=True,
        )
    return _engine


def get_db() -> Generator[Session, None, None]:
    session = Session(get_engine())
    try:
        yield session
    finally:
        session.close()


def init_schema() -> None:
    import models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())

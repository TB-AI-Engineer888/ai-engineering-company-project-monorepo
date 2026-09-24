from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_API_DIR = Path(__file__).resolve().parent
load_dotenv(_API_DIR / ".env")


def signing_secret() -> str:
    secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("SECRET_KEY is not set")
    return secret


def access_token_expire_minutes() -> int:
    raw = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "").strip()
    if not raw:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES is not set")
    return int(raw)


def tinydb_path() -> Path:
    configured = os.environ.get("TINYDB_PATH", "").strip()
    if configured:
        return Path(configured)
    return _API_DIR / "data" / "tinydb.json"

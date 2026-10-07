from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-signing-secret")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("TINYDB_PATH", str(Path(tempfile.mkdtemp()) / "tinydb.json"))

import pytest


@pytest.fixture(autouse=True)
def clear_tables() -> None:
    from db import get_db

    get_db().drop_tables()

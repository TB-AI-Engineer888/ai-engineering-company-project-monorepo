from __future__ import annotations

import sys
from pathlib import Path

from tinydb import TinyDB

_SERVICES_DIR = Path(__file__).resolve().parents[1]
if str(_SERVICES_DIR) not in sys.path:
    sys.path.append(str(_SERVICES_DIR))

from database import get_tinydb


def get_db() -> TinyDB:
    return get_tinydb()


def users_table():
    return get_db().table("users")


def profiles_table():
    return get_db().table("profiles")

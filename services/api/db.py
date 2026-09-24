from __future__ import annotations

from tinydb import TinyDB

from settings import tinydb_path

_db: TinyDB | None = None


def get_db() -> TinyDB:
    global _db
    if _db is None:
        path = tinydb_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _db = TinyDB(path)
    return _db


def users_table():
    return get_db().table("users")


def profiles_table():
    return get_db().table("profiles")

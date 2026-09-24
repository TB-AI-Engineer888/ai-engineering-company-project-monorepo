from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from tinydb import Query

from db import profiles_table, users_table
from security import hash_password


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    user = "user"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_user(email: str, password: str, role: Role = Role.user) -> dict[str, Any]:
    table = users_table()
    if table.get(Query().email == email):
        raise ValueError("email already registered")
    doc_id = table.insert(
        {
            "email": email,
            "hashed_password": hash_password(password),
            "is_active": True,
            "role": role.value,
            "created_at": _now(),
        }
    )
    table.update({"id": doc_id}, doc_ids=[doc_id])
    return get_user_by_id(doc_id)


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    return users_table().get(doc_id=user_id)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    return users_table().get(Query().email == email)


def update_user(user_id: int, changes: dict[str, Any]) -> dict[str, Any] | None:
    table = users_table()
    if table.get(doc_id=user_id) is None:
        return None
    if "email" in changes:
        existing = table.get(Query().email == changes["email"])
        if existing is not None and existing["id"] != user_id:
            raise ValueError("email already registered")
    if "password" in changes:
        changes["hashed_password"] = hash_password(changes.pop("password"))
    table.update(changes, doc_ids=[user_id])
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    removed = users_table().remove(doc_ids=[user_id])
    if not removed:
        return False
    profiles_table().remove(Query().user_id == user_id)
    return True


def public_user(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "email": record["email"],
        "is_active": record["is_active"],
        "role": record["role"],
        "created_at": record["created_at"],
    }

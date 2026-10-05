from __future__ import annotations

from typing import Any

from tinydb import Query

from db import profiles_table


def create_profile(user_id: int, name: str = "", phone: str = "", address: str = "") -> dict[str, Any]:
    table = profiles_table()
    doc_id = table.insert(
        {
            "user_id": user_id,
            "name": name,
            "phone": phone,
            "address": address,
        }
    )
    table.update({"id": doc_id}, doc_ids=[doc_id])
    return get_profile_by_user_id(user_id)


def get_profile_by_user_id(user_id: int) -> dict[str, Any] | None:
    return profiles_table().get(Query().user_id == user_id)


def update_profile(user_id: int, changes: dict[str, Any]) -> dict[str, Any] | None:
    record = get_profile_by_user_id(user_id)
    if record is None:
        return None
    profiles_table().update(changes, doc_ids=[record["id"]])
    return get_profile_by_user_id(user_id)


def public_profile(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "user_id": record["user_id"],
        "name": record["name"],
        "phone": record["phone"],
        "address": record["address"],
    }

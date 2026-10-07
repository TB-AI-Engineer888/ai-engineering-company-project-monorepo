from __future__ import annotations

import pytest
from fastapi import HTTPException

from profiles import create_profile, get_profile_by_user_id
from routers import UserUpdate, _forbid_unless_self_or_admin, list_users, put_user, read_user, remove_user
from users import Role, create_user, delete_user, update_user


def test_list_and_read_return_public_users() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    listed = list_users(user)
    assert listed[0]["email"] == "ada@healthcore.test"
    assert "hashed_password" not in listed[0]
    assert read_user(user["id"], user)["id"] == user["id"]


def test_unknown_user_is_not_found() -> None:
    caller = create_user("ada@healthcore.test", "correct-horse")
    with pytest.raises(HTTPException) as caught:
        read_user(999, caller)
    assert caught.value.status_code == 404


def test_user_cannot_edit_someone_else() -> None:
    owner = create_user("ada@healthcore.test", "correct-horse")
    other = create_user("bea@healthcore.test", "correct-horse")
    with pytest.raises(HTTPException) as caught:
        _forbid_unless_self_or_admin(owner, other["id"])
    assert caught.value.status_code == 403
    with pytest.raises(HTTPException) as denied:
        put_user(other["id"], UserUpdate(email="new@healthcore.test"), owner)
    assert denied.value.status_code == 403


def test_admin_can_change_role_and_password() -> None:
    admin = create_user("admin@healthcore.test", "correct-horse", Role.admin)
    member = create_user("ada@healthcore.test", "correct-horse")
    updated = put_user(member["id"], UserUpdate(role=Role.manager, password="new-horse"), admin)
    assert updated["role"] == "manager"
    from users import authenticate

    assert authenticate("ada@healthcore.test", "new-horse")


def test_member_cannot_change_role() -> None:
    member = create_user("ada@healthcore.test", "correct-horse")
    with pytest.raises(HTTPException) as caught:
        put_user(member["id"], UserUpdate(role=Role.admin), member)
    assert caught.value.status_code == 403


def test_duplicate_email_on_update_is_rejected() -> None:
    ada = create_user("ada@healthcore.test", "correct-horse")
    create_user("bea@healthcore.test", "correct-horse")
    with pytest.raises(ValueError, match="email already registered"):
        update_user(ada["id"], {"email": "bea@healthcore.test"})


def test_update_and_delete_missing_user() -> None:
    assert update_user(999, {"email": "nope@healthcore.test"}) is None
    assert delete_user(999) is False
    admin = create_user("admin@healthcore.test", "correct-horse", Role.admin)
    with pytest.raises(HTTPException) as missing:
        put_user(999, UserUpdate(email="nope@healthcore.test"), admin)
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as removed:
        remove_user(999, admin)
    assert removed.value.status_code == 404


def test_delete_removes_the_profile() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    create_profile(user["id"], "Ada")
    assert remove_user(user["id"], user) == {"status": "deleted"}
    assert get_profile_by_user_id(user["id"]) is None


def test_empty_update_returns_the_current_user() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    same = put_user(user["id"], UserUpdate(), user)
    assert same["email"] == "ada@healthcore.test"

from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from routers import UserCreate, register_user
from users import create_user


def test_register_creates_account_and_profile() -> None:
    account = register_user(
        UserCreate(email="ada@healthcore.test", password="correct-horse", name="Ada", phone="555", address="Austin")
    )
    assert account["email"] == "ada@healthcore.test"
    assert account["role"] == "user"
    assert account["is_active"] is True
    assert "hashed_password" not in account
    assert account["profile"]["name"] == "Ada"
    assert account["profile"]["user_id"] == account["id"]


def test_register_ignores_a_client_supplied_role() -> None:
    account = register_user(
        UserCreate(email="ada@healthcore.test", password="correct-horse", name="Ada")
    )
    assert account["role"] == "user"


def test_duplicate_email_is_rejected() -> None:
    create_user("ada@healthcore.test", "correct-horse")
    with pytest.raises(HTTPException) as caught:
        register_user(UserCreate(email="ada@healthcore.test", password="another-pass", name="Ada"))
    assert caught.value.status_code == 400
    assert caught.value.detail == "email already registered"


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="ada@healthcore.test", password="")

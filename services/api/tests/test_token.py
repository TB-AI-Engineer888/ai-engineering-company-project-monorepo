from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from deps import get_current_user
from profiles import create_profile
from routers import read_me
from security import ALGORITHM, create_access_token, decode_access_token
from settings import signing_secret
from users import create_user, delete_user, get_user_by_id, update_user


def test_valid_token_resolves_to_the_user_and_profile() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    create_profile(user["id"], "Ada", "555", "Austin")
    token = create_access_token(user["id"])
    caller = get_current_user(token)
    account = read_me(caller)
    assert caller["id"] == user["id"]
    assert account["email"] == "ada@healthcore.test"
    assert account["profile"]["name"] == "Ada"


def test_token_without_a_subject_is_rejected() -> None:
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        signing_secret(),
        algorithm=ALGORITHM,
    )
    with pytest.raises(ValueError, match="invalid token"):
        decode_access_token(token)


def test_expired_token_is_rejected() -> None:
    # Signature is valid; only the expiration time makes this token unusable.
    user = create_user("ada@healthcore.test", "correct-horse")
    token = jwt.encode(
        {"sub": str(user["id"]), "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
        signing_secret(),
        algorithm=ALGORITHM,
    )
    with pytest.raises(ValueError, match="invalid token"):
        decode_access_token(token)
    with pytest.raises(HTTPException) as caught:
        get_current_user(token)
    assert caught.value.status_code == 401


def test_malformed_token_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid token"):
        decode_access_token("not-a-token")
    with pytest.raises(HTTPException) as caught:
        get_current_user("not-a-token")
    assert caught.value.status_code == 401


def test_missing_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as caught:
        get_current_user(None)
    assert caught.value.status_code == 401


def test_inactive_or_deleted_user_token_is_rejected() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    token = create_access_token(user["id"])
    update_user(user["id"], {"is_active": False})
    with pytest.raises(HTTPException) as inactive:
        get_current_user(token)
    assert inactive.value.status_code == 401
    update_user(user["id"], {"is_active": True})
    delete_user(user["id"])
    assert get_user_by_id(user["id"]) is None
    with pytest.raises(HTTPException) as removed:
        get_current_user(token)
    assert removed.value.status_code == 401


def test_me_without_a_profile_returns_no_profile() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    account = read_me(get_user_by_id(user["id"]))
    assert account["profile"] is None
    assert account["role"] == "user"

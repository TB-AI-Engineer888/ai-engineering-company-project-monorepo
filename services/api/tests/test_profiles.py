from __future__ import annotations

import pytest
from fastapi import HTTPException

from profiles import create_profile, update_profile
from routers import ProfileUpdate, put_my_profile, read_my_profile
from users import create_user


def test_read_and_update_profile() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    create_profile(user["id"], "Ada", "555", "Austin")
    current = read_my_profile(user)
    assert current["name"] == "Ada"
    saved = put_my_profile(ProfileUpdate(name="Ada Lovelace"), user)
    assert saved["name"] == "Ada Lovelace"
    assert saved["phone"] == "555"


def test_blank_name_can_be_saved() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    create_profile(user["id"], "Ada")
    saved = put_my_profile(ProfileUpdate(name=""), user)
    assert saved["name"] == ""


def test_missing_profile_is_rejected() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    with pytest.raises(HTTPException) as caught:
        read_my_profile(user)
    assert caught.value.status_code == 404
    assert update_profile(user["id"], {"name": "Ada"}) is None
    with pytest.raises(HTTPException) as missing:
        put_my_profile(ProfileUpdate(name="Ada"), user)
    assert missing.value.status_code == 404

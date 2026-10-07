from __future__ import annotations

import pytest

from security import decode_access_token
from users import authenticate, create_user, update_user


def test_login_returns_a_token_for_the_user() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    token = authenticate("ada@healthcore.test", "correct-horse")
    assert decode_access_token(token) == user["id"]


def test_inactive_account_cannot_log_in() -> None:
    user = create_user("ada@healthcore.test", "correct-horse")
    update_user(user["id"], {"is_active": False})
    with pytest.raises(ValueError, match="Incorrect email or password"):
        authenticate("ada@healthcore.test", "correct-horse")


def test_wrong_password_is_rejected() -> None:
    create_user("ada@healthcore.test", "correct-horse")
    with pytest.raises(ValueError, match="Incorrect email or password"):
        authenticate("ada@healthcore.test", "wrong-horse")


def test_unknown_email_is_rejected() -> None:
    with pytest.raises(ValueError, match="Incorrect email or password"):
        authenticate("missing@healthcore.test", "correct-horse")


def test_empty_password_is_rejected() -> None:
    # An empty password is rejected before the stored hash is checked.
    create_user("ada@healthcore.test", "correct-horse")
    with pytest.raises(ValueError, match="Incorrect email or password"):
        authenticate("ada@healthcore.test", "")

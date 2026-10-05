from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from security import decode_access_token
from users import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated") from None
    user = get_user_by_id(user_id)
    if user is None or not user.get("is_active", False):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

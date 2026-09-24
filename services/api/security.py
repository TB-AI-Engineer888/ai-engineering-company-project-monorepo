from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.hash import bcrypt

from settings import access_token_expire_minutes, signing_secret

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=access_token_expire_minutes())
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, signing_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, signing_secret(), algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise JWTError("missing subject")
        return int(subject)
    except (JWTError, ValueError) as exc:
        raise ValueError("invalid token") from exc

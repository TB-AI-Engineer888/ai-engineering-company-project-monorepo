from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import ExpiredSignatureError, JWTError, jwt
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


class InvalidToken(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__("invalid token")
        self.reason = reason


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, signing_secret(), algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise InvalidToken("token_expired") from None
    except JWTError:
        raise InvalidToken("invalid") from None
    subject = payload.get("sub")
    if subject is None:
        raise InvalidToken("invalid")
    try:
        return int(subject)
    except (TypeError, ValueError):
        raise InvalidToken("invalid") from None

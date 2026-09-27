from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import jwt
from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse

_LOCK = threading.Lock()
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TOKEN_TTL_SECONDS = 60 * 60 * 12
_PBKDF2_ROUNDS = 200_000


def _secret() -> str:
    return os.environ.get("AUTH_JWT_SECRET", "healthcore-local-dev-only-secret-key")


def _store_path() -> Path:
    override = os.environ.get("AUTH_STORE_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "data" / "accounts.json"


def _empty_store() -> dict[str, Any]:
    return {"users": {}}


def _read_store() -> dict[str, Any]:
    path = _store_path()
    if not path.is_file():
        return _empty_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_store()
    if not isinstance(payload, dict) or not isinstance(payload.get("users"), dict):
        return _empty_store()
    return payload


def _write_store(payload: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        _PBKDF2_ROUNDS,
    ).hex()
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, digest = stored.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    check = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        int(rounds),
    ).hex()
    return hmac.compare_digest(check, digest)


def _profile_from(raw: dict[str, Any] | None) -> dict[str, str]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "name": str(source.get("name") or ""),
        "phone": str(source.get("phone") or ""),
        "address": str(source.get("address") or ""),
    }


def _public_account(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": account["email"],
        "profile": _profile_from(account.get("profile")),
    }


def _field_error(status: int, message: str, fields: dict[str, str]) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": message, "status": status, "fields": fields},
    )


def _clean_text(value: Any, *, field: str, limit: int, fields: dict[str, str]) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        fields[field] = "Enter text."
        return ""
    text = value.strip()
    if len(text) > limit:
        fields[field] = f"Use {limit} characters or fewer."
    return text


def register_user(body: Any) -> JSONResponse:
    if not isinstance(body, dict):
        return _field_error(400, "Request body must be a JSON object.", {})

    fields: dict[str, str] = {}
    email = body.get("email")
    password = body.get("password")

    if not isinstance(email, str) or not email.strip():
        fields["email"] = "Enter your email."
        normalized = ""
    else:
        normalized = email.strip().lower()
        if not _EMAIL.match(normalized):
            fields["email"] = "Enter a valid email address."

    if not isinstance(password, str) or not password:
        fields["password"] = "Enter a password."
    elif len(password) < 8:
        fields["password"] = "Use at least 8 characters."

    name = _clean_text(body.get("name", ""), field="name", limit=120, fields=fields)
    phone = _clean_text(body.get("phone", ""), field="phone", limit=40, fields=fields)
    address = _clean_text(body.get("address", ""), field="address", limit=200, fields=fields)

    if fields:
        return _field_error(400, "Check the highlighted fields.", fields)

    with _LOCK:
        store = _read_store()
        users: dict[str, Any] = store["users"]
        if normalized in users:
            return _field_error(
                409,
                "An account with this email already exists.",
                {"email": "An account with this email already exists."},
            )
        account = {
            "email": normalized,
            "password_hash": _hash_password(password),
            "profile": {"name": name, "phone": phone, "address": address},
        }
        users[normalized] = account
        _write_store(store)

    return JSONResponse(status_code=201, content=_public_account(account))


def login_user(body: Any) -> JSONResponse:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object.")

    email = body.get("email")
    password = body.get("password")
    normalized = email.strip().lower() if isinstance(email, str) else ""
    candidate = password if isinstance(password, str) else ""

    with _LOCK:
        account = _read_store()["users"].get(normalized)

    if account is None or not _verify_password(candidate, account.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")

    now = int(time.time())
    token = jwt.encode(
        {"sub": account["email"], "iat": now, "exp": now + _TOKEN_TTL_SECONDS},
        _secret(),
        algorithm="HS256",
    )
    return JSONResponse(status_code=200, content={"token": token})


def _account_from_header(authorization: str | None) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid session.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid session.")
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Missing or invalid session.") from exc
    email = payload.get("sub")
    if not isinstance(email, str):
        raise HTTPException(status_code=401, detail="Missing or invalid session.")
    with _LOCK:
        account = _read_store()["users"].get(email)
    if account is None:
        raise HTTPException(status_code=401, detail="Missing or invalid session.")
    return account


def require_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _account_from_header(authorization)


def read_me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return _public_account(_account_from_header(authorization))


def update_profile(body: Any, authorization: str | None = Header(default=None)) -> JSONResponse:
    account = _account_from_header(authorization)
    if not isinstance(body, dict):
        return _field_error(400, "Request body must be a JSON object.", {})

    fields: dict[str, str] = {}
    updates: dict[str, str] = {}
    for key, limit in (("name", 120), ("phone", 40), ("address", 200)):
        if key not in body:
            continue
        updates[key] = _clean_text(body.get(key), field=key, limit=limit, fields=fields)
    if fields:
        return _field_error(400, "Check the highlighted fields.", fields)
    if not updates:
        return _field_error(
            400,
            "Send the profile fields you want to change.",
            {"name": "Include name, phone, or address."},
        )

    with _LOCK:
        store = _read_store()
        current = store["users"].get(account["email"])
        if current is None:
            raise HTTPException(status_code=401, detail="Missing or invalid session.")
        profile = _profile_from(current.get("profile"))
        profile.update(updates)
        current["profile"] = profile
        _write_store(store)
        public = _public_account(current)

    return JSONResponse(status_code=200, content=public)

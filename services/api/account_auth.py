from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

router = APIRouter()

MINIMUM_PASSWORD_LENGTH = 8
RESET_TTL_MS = 30 * 60 * 1000
SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000
API_DIR = Path(__file__).resolve().parent
REPO_ROOT = API_DIR.parents[1]


def load_env_files() -> None:
    for path in (REPO_ROOT / ".env", API_DIR / ".env"):
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _db_path() -> Path:
    configured = os.environ.get("AUTH_DB_PATH", "").strip()
    path = Path(configured) if configured else API_DIR / "data" / "auth.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          password_changed_at INTEGER NOT NULL,
          created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          expires_at INTEGER NOT NULL,
          created_at INTEGER NOT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
          token_hash TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          expires_at INTEGER NOT NULL,
          used_at INTEGER,
          created_at INTEGER NOT NULL,
          FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
    )
    return connection


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${derived.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    scheme, _, remainder = stored.partition("$")
    salt_hex, _, hash_hex = remainder.partition("$")
    if scheme != "scrypt" or not salt_hex or not hash_hex:
        return False
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    return secrets.compare_digest(derived, bytes.fromhex(hash_hex))


def _password_problem(password: str) -> str | None:
    if len(password) < MINIMUM_PASSWORD_LENGTH or len(password) > 200:
        return f"Use at least {MINIMUM_PASSWORD_LENGTH} characters."
    return None


def _public_origin() -> str:
    configured = os.environ.get("APP_URL", "").strip().rstrip("/")
    return configured or "http://127.0.0.1:43123"


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _outbox_path() -> Path:
    configured = os.environ.get("AUTH_OUTBOX_PATH", "").strip()
    return Path(configured) if configured else API_DIR / "data" / "mail-outbox.json"


def deliver_reset_email(recipient: str, reset_url: str) -> None:
    text = "\n".join(
        [
            "Reset your password",
            "",
            "Use the link below to choose a new password. It expires in 30 minutes and works once.",
            "",
            reset_url,
            "",
            "If you did not request this, you can ignore this email.",
        ]
    )
    html = (
        "<!doctype html><html><body style=\"font-family:sans-serif;line-height:1.5\">"
        "<p>Reset your password</p>"
        f"<p><a href=\"{_escape_html(reset_url)}\">Choose a new password</a></p>"
        "<p>This link expires in 30 minutes and works once.</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
        "</body></html>"
    )
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        path = _outbox_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        current = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
        current.append({"to": recipient, "reset_url": reset_url, "text": text})
        path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return
    sender = os.environ.get("RESEND_FROM", "").strip() or "HealthCore <onboarding@resend.dev>"
    payload = json.dumps(
        {
            "from": sender,
            "to": [recipient],
            "subject": "Reset your password",
            "text": text,
            "html": html,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status >= 300:
                raise RuntimeError("reset email was not accepted")
    except urllib.error.HTTPError as exc:
        raise RuntimeError("reset email was not accepted") from exc


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _find_user(connection: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, email, password_hash, password_changed_at FROM users WHERE email = ?",
        (_normalize_email(email),),
    ).fetchone()


def _open_session(connection: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now_ms()
    connection.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (_hash_secret(token), user_id, now + SESSION_TTL_MS, now),
    )
    connection.commit()
    return token


def _read_session(authorization: str | None) -> sqlite3.Row | None:
    token = _bearer(authorization)
    if not token:
        return None
    connection = _connect()
    try:
        row = connection.execute(
            """
            SELECT s.expires_at, u.id AS user_id, u.email, u.password_hash
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (_hash_secret(token),),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= _now_ms():
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_secret(token),))
            connection.commit()
            return None
        return row
    finally:
        connection.close()


async def _json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _error(status: int, error: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": error})


@router.post("/auth/register")
async def register(request: Request) -> JSONResponse:
    body = await _json_body(request)
    email = body.get("email") if isinstance(body.get("email"), str) else ""
    password = body.get("password") if isinstance(body.get("password"), str) else ""
    normalized = _normalize_email(email)
    if "@" not in normalized or len(normalized) > 320:
        return _error(400, "Enter a valid email address.")
    problem = _password_problem(password)
    if problem:
        return _error(400, problem)
    connection = _connect()
    try:
        if _find_user(connection, normalized):
            return _error(409, "An account with that email already exists.")
        now = _now_ms()
        connection.execute(
            "INSERT INTO users (email, password_hash, password_changed_at, created_at) VALUES (?, ?, ?, ?)",
            (normalized, _hash_password(password), now, now),
        )
        connection.commit()
        user = _find_user(connection, normalized)
        if user is None:
            return _error(500, "The account could not be created.")
        token = _open_session(connection, int(user["id"]))
        return JSONResponse({"token": token, "email": user["email"]})
    finally:
        connection.close()


@router.post("/auth/login")
async def login(request: Request) -> JSONResponse:
    body = await _json_body(request)
    email = body.get("email") if isinstance(body.get("email"), str) else ""
    password = body.get("password") if isinstance(body.get("password"), str) else ""
    connection = _connect()
    try:
        user = _find_user(connection, email)
        valid = bool(user) and _verify_password(password, str(user["password_hash"]))
        if not user or not valid:
            return _error(401, "Email or password is incorrect.")
        token = _open_session(connection, int(user["id"]))
        return JSONResponse({"token": token, "email": user["email"]})
    finally:
        connection.close()


@router.post("/auth/logout")
async def logout(authorization: str | None = Header(default=None)) -> JSONResponse:
    token = _bearer(authorization)
    if token:
        connection = _connect()
        try:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_secret(token),))
            connection.commit()
        finally:
            connection.close()
    return JSONResponse({"ok": True})


@router.get("/auth/me")
async def me(authorization: str | None = Header(default=None)) -> JSONResponse:
    session = _read_session(authorization)
    if session is None:
        return _error(401, "Sign in again.")
    return JSONResponse({"email": session["email"]})


@router.post("/auth/forgot-password")
async def forgot_password(request: Request) -> JSONResponse:
    body = await _json_body(request)
    email = body.get("email") if isinstance(body.get("email"), str) else ""
    connection = _connect()
    try:
        user = _find_user(connection, email)
        if user is not None:
            token = secrets.token_urlsafe(32)
            now = _now_ms()
            connection.execute(
                """
                INSERT INTO password_reset_tokens
                  (token_hash, user_id, expires_at, used_at, created_at)
                VALUES (?, ?, ?, NULL, ?)
                """,
                (_hash_secret(token), int(user["id"]), now + RESET_TTL_MS, now),
            )
            connection.commit()
            reset_url = f"{_public_origin()}/reset-password?token={token}"
            try:
                deliver_reset_email(str(user["email"]), reset_url)
            except Exception:
                pass
    finally:
        connection.close()
    return JSONResponse({"ok": True})


@router.post("/auth/reset-password")
async def reset_password(request: Request) -> JSONResponse:
    body = await _json_body(request)
    token = body.get("token") if isinstance(body.get("token"), str) else ""
    new_password = body.get("new_password") if isinstance(body.get("new_password"), str) else ""
    problem = _password_problem(new_password)
    if not token or problem:
        return _error(400, problem or "This reset link is invalid or has expired.")
    token_hash = _hash_secret(token)
    password_hash = _hash_password(new_password)
    now = _now_ms()
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT t.user_id, t.expires_at, t.used_at, t.created_at, u.password_changed_at
            FROM password_reset_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if (
            row is None
            or row["used_at"] is not None
            or row["expires_at"] <= now
            or row["password_changed_at"] > row["created_at"]
        ):
            connection.rollback()
            return _error(400, "This reset link is invalid or has expired.")
        connection.execute(
            "UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?",
            (password_hash, now, int(row["user_id"])),
        )
        connection.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
            (now, int(row["user_id"])),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return JSONResponse({"ok": True})


@router.post("/auth/change-password")
async def change_password(
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    session = _read_session(authorization)
    if session is None:
        return _error(401, "Sign in again to change your password.")
    body = await _json_body(request)
    current_password = (
        body.get("current_password") if isinstance(body.get("current_password"), str) else ""
    )
    new_password = body.get("new_password") if isinstance(body.get("new_password"), str) else ""
    problem = _password_problem(new_password)
    if problem:
        return _error(400, problem)
    if not _verify_password(current_password, str(session["password_hash"])):
        return _error(400, "Current password is incorrect.")
    now = _now_ms()
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE users SET password_hash = ?, password_changed_at = ? WHERE id = ?",
            (_hash_password(new_password), now, int(session["user_id"])),
        )
        connection.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
            (now, int(session["user_id"])),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return JSONResponse({"ok": True})

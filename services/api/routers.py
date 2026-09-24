from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db import users_table
from deps import get_current_user
from profiles import create_profile, get_profile_by_user_id, public_profile, update_profile
from security import create_access_token, verify_password
from users import Role, create_user, delete_user, get_user_by_email, get_user_by_id, public_user, update_user

users_router = APIRouter(prefix="/users", tags=["users"])
profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=1)
    name: str = ""
    phone: str = ""
    address: str = ""


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    role: Role | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


def _forbid_unless_self_or_admin(caller: dict[str, Any], user_id: int) -> None:
    if caller["id"] == user_id or caller["role"] == Role.admin.value:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


@users_router.post("", status_code=201)
def register_user(body: UserCreate) -> dict[str, Any]:
    try:
        user = create_user(body.email, body.password, Role.user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    profile = create_profile(user["id"], body.name, body.phone, body.address)
    return {**public_user(user), "profile": public_profile(profile)}


@users_router.get("")
def list_users(_: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    return [public_user(record) for record in users_table().all()]


@users_router.get("/{user_id}")
def read_user(user_id: int, _: dict = Depends(get_current_user)) -> dict[str, Any]:
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return public_user(user)


@users_router.put("/{user_id}")
def put_user(user_id: int, body: UserUpdate, caller: dict = Depends(get_current_user)) -> dict[str, Any]:
    _forbid_unless_self_or_admin(caller, user_id)
    if body.role is not None and caller["role"] != Role.admin.value:
        raise HTTPException(status_code=403, detail="Forbidden")
    changes: dict[str, Any] = {}
    if body.email is not None:
        changes["email"] = body.email
    if body.password is not None:
        changes["password"] = body.password
    if body.role is not None:
        changes["role"] = body.role.value
    if not changes:
        user = get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return public_user(user)
    try:
        updated = update_user(user_id, changes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return public_user(updated)


@users_router.delete("/{user_id}")
def remove_user(user_id: int, caller: dict = Depends(get_current_user)) -> dict[str, str]:
    _forbid_unless_self_or_admin(caller, user_id)
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "deleted"}


@profiles_router.get("/me")
def read_my_profile(caller: dict = Depends(get_current_user)) -> dict[str, Any]:
    profile = get_profile_by_user_id(caller["id"])
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return public_profile(profile)


@profiles_router.put("/me")
def put_my_profile(body: ProfileUpdate, caller: dict = Depends(get_current_user)) -> dict[str, Any]:
    changes = body.model_dump(exclude_none=True)
    profile = update_profile(caller["id"], changes)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return public_profile(profile)


@auth_router.post("/login")
async def login(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = LoginRequest.model_validate(await request.json())
        email = body.email
        password = body.password
    else:
        form = await request.form()
        email = str(form.get("email") or form.get("username") or "")
        password = str(form.get("password") or "")
    user = get_user_by_email(email)
    if user is None or not user.get("is_active", False) or not password:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user["id"]), "token_type": "bearer"}


@auth_router.get("/me")
def read_me(caller: dict = Depends(get_current_user)) -> dict[str, Any]:
    profile = get_profile_by_user_id(caller["id"])
    return {
        "email": caller["email"],
        "role": caller["role"],
        "profile": public_profile(profile) if profile else None,
    }

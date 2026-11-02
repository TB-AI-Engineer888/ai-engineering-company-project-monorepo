from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from db import users_table
from deps import get_current_user
from profiles import create_profile, get_profile_by_user_id, public_profile, update_profile
from response_schemas import (
    DeleteStatus,
    LoginRequest,
    MeResponse,
    ProfileRead,
    ProfileUpdate,
    TokenResponse,
    UserCreate,
    UserCreatedResponse,
    UserListItem,
    UserPublic,
    UserUpdate,
)
from users import Role, authenticate, create_user, delete_user, ensure_user_uuid, get_user_by_id, public_user, update_user

users_router = APIRouter(prefix="/users", tags=["users"])
profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _forbid_unless_self_or_admin(caller: dict[str, Any], user_id: int) -> None:
    if caller["id"] == user_id or caller["role"] == Role.admin.value:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _user_public(record: dict[str, Any]) -> UserPublic:
    safe = public_user(ensure_user_uuid(record) or record)
    return UserPublic.model_validate(safe)


def _profile_read(record: dict[str, Any]) -> ProfileRead:
    return ProfileRead.model_validate(public_profile(record))


@users_router.post("", status_code=201, response_model=UserCreatedResponse)
def register_user(body: UserCreate) -> UserCreatedResponse:
    try:
        user = create_user(body.email, body.password, Role.user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    profile = create_profile(user["id"], body.name, body.phone, body.address)
    return UserCreatedResponse(
        id=user["id"],
        role=user["role"],
        is_active=user["is_active"],
        profile=_profile_read(profile),
    )


@users_router.get("", response_model=list[UserListItem])
def list_users(_: dict = Depends(get_current_user)) -> list[UserListItem]:
    items: list[UserListItem] = []
    for record in users_table().all():
        safe = public_user(ensure_user_uuid(record) or record)
        items.append(
            UserListItem(
                id=safe["id"],
                role=safe["role"],
                uuid=str(safe.get("uuid") or ""),
            )
        )
    return items


@users_router.get("/{user_id}", response_model=UserPublic)
def read_user(user_id: int, _: dict = Depends(get_current_user)) -> UserPublic:
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_public(user)


@users_router.put("/{user_id}", response_model=UserPublic)
def put_user(user_id: int, body: UserUpdate, caller: dict = Depends(get_current_user)) -> UserPublic:
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
        return _user_public(user)
    try:
        updated = update_user(user_id, changes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_public(updated)


@users_router.delete("/{user_id}", response_model=DeleteStatus)
def remove_user(user_id: int, caller: dict = Depends(get_current_user)) -> DeleteStatus:
    _forbid_unless_self_or_admin(caller, user_id)
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return DeleteStatus(status="deleted")


@profiles_router.get("/me", response_model=ProfileRead)
def read_my_profile(caller: dict = Depends(get_current_user)) -> ProfileRead:
    profile = get_profile_by_user_id(caller["id"])
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_read(profile)


@profiles_router.put("/me", response_model=ProfileRead)
def put_my_profile(body: ProfileUpdate, caller: dict = Depends(get_current_user)) -> ProfileRead:
    changes = body.model_dump(exclude_none=True)
    profile = update_profile(caller["id"], changes)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_read(profile)


@auth_router.post("/login", response_model=TokenResponse)
async def login(request: Request) -> TokenResponse:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = LoginRequest.model_validate(await request.json())
        email = body.email
        password = body.password
    else:
        form = await request.form()
        email = str(form.get("email") or form.get("username") or "")
        password = str(form.get("password") or "")
    try:
        token = authenticate(email, password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Incorrect email or password") from exc
    return TokenResponse(access_token=token, token_type="bearer")


@auth_router.get("/me", response_model=MeResponse)
def read_me(caller: dict = Depends(get_current_user)) -> MeResponse:
    profile = get_profile_by_user_id(caller["id"])
    safe = public_user(ensure_user_uuid(caller) or caller)
    return MeResponse(
        id=safe["id"],
        email=safe["email"],
        role=safe["role"],
        uuid=safe.get("uuid"),
        profile=_profile_read(profile) if profile else None,
    )

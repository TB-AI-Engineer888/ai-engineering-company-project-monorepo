from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from users import Role


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


class ProfileRead(BaseModel):
    id: int
    user_id: int
    name: str
    phone: str
    address: str


class UserCreatedResponse(BaseModel):
    """Register confirmation. Email stays off the body (task 9 / 17)."""

    id: int
    role: Literal["admin", "manager", "user"]
    is_active: bool
    profile: ProfileRead


class UserListItem(BaseModel):
    """List projection used by inventory tests to recover the TinyDB uuid."""

    id: int
    role: Literal["admin", "manager", "user"]
    uuid: str


class UserPublic(BaseModel):
    """Authenticated user detail / write confirmation. No password fields."""

    id: int
    email: str
    is_active: bool
    role: Literal["admin", "manager", "user"]
    created_at: str
    uuid: str | None = None


class DeleteStatus(BaseModel):
    status: Literal["deleted"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: str
    role: Literal["admin", "manager", "user"]
    uuid: str | None = None
    profile: ProfileRead | None = None


class HealthStatus(BaseModel):
    status: str
    service: str


class ServiceInfo(BaseModel):
    service: str
    analyze: str
    export: str


class InvalidIncidentRecord(BaseModel):
    row_number: int
    incident_id: str
    reasons: list[str]
    details: list[str]


class AnalysisResultRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str
    total_rows: int
    valid_count: int
    invalid_count: int
    by_category: dict[str, int]
    by_status: dict[str, int]
    by_country: dict[str, int]
    invalid_by_reason: dict[str, int]
    avg_satisfaction_closed: float | None
    satisfaction_sample_size: int
    closed_valid_count: int
    satisfaction_by_score: dict[str, int]
    invalid_records: list[InvalidIncidentRecord]


CSV_FILE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            "text/csv": {
                "schema": {"type": "string", "format": "binary"},
            }
        },
        "description": "CSV file download. Not a JSON ORM dump.",
    }
}

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker
from sqlalchemy import text

from database import get_engine

_CATALOGUE = Path(__file__).resolve().parents[1] / "docs" / "telemetry" / "event-schemas.json"
_FORMAT = FormatChecker()

_ERROR_TYPES = {"client_exception_captured"}
_WARN_TYPES = {
    "login_failed",
    "session_expired",
    "outbound_order_rejected",
    "inventory_validation_failed",
    "direct_stock_edit_rejected",
    "supply_expiry_flagged",
    "stock_threshold_triggered",
}
_VALUE_KEYS = (
    "quantity",
    "duration_ms",
    "row_count",
    "days_to_expiry",
    "time_on_form_seconds",
    "value",
)

_DDL = """
CREATE TABLE IF NOT EXISTS telemetry_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp timestamptz NOT NULL,
    service text NOT NULL,
    event_type text NOT NULL,
    level text NOT NULL DEFAULT 'info',
    value numeric NULL,
    message text NULL,
    tags jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT telemetry_events_level_check CHECK (level IN ('info', 'warn', 'error'))
);
CREATE INDEX IF NOT EXISTS telemetry_events_timestamp_idx ON telemetry_events (timestamp);
CREATE INDEX IF NOT EXISTS telemetry_events_event_type_idx ON telemetry_events (event_type);
CREATE INDEX IF NOT EXISTS telemetry_events_tags_idx ON telemetry_events USING GIN (tags);
"""

_INSERT = text(
    """
    INSERT INTO telemetry_events (timestamp, service, event_type, level, value, message, tags)
    VALUES (
        :timestamp,
        :service,
        :event_type,
        :level,
        :value,
        :message,
        CAST(:tags AS jsonb)
    )
    """
)

_validators: dict[str, Draft7Validator] | None = None
_descriptions: dict[str, str] | None = None
_table_ready = False


def _catalogue() -> dict[str, Any]:
    return json.loads(_CATALOGUE.read_text())


def _load() -> tuple[dict[str, Draft7Validator], dict[str, str]]:
    global _validators, _descriptions
    if _validators is None or _descriptions is None:
        events = _catalogue()["events"]
        _validators = {
            name: Draft7Validator(spec["schema"], format_checker=_FORMAT) for name, spec in events.items()
        }
        _descriptions = {name: spec.get("description", "") for name, spec in events.items()}
    return _validators, _descriptions


def matches_plan(raw: dict[str, Any]) -> bool:
    event_type = raw.get("event_type")
    if not isinstance(event_type, str):
        return False
    validators, _descriptions = _load()
    validator = validators.get(event_type)
    if validator is None:
        return False
    return validator.is_valid(raw)


def _level(event_type: str) -> str:
    if event_type in _ERROR_TYPES:
        return "error"
    if event_type in _WARN_TYPES:
        return "warn"
    return "info"


def _value(properties: dict[str, Any]) -> int | float | None:
    for key in _VALUE_KEYS:
        number = properties.get(key)
        if isinstance(number, bool):
            continue
        if isinstance(number, (int, float)):
            return number
    return None


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def row_for_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not matches_plan(raw):
        return None
    properties = raw["properties"]
    if not isinstance(properties, dict):
        return None
    _validators, descriptions = _load()
    message = descriptions.get(raw["event_type"], "").strip() or None
    return {
        "timestamp": _timestamp(raw["timestamp"]),
        "service": "backoffice",
        "event_type": raw["event_type"],
        "level": _level(raw["event_type"]),
        "value": _value(properties),
        "message": message,
        "tags": json.dumps(properties),
    }


def ensure_telemetry_table() -> None:
    global _table_ready
    if _table_ready:
        return
    statements = [statement.strip() for statement in _DDL.split(";") if statement.strip()]
    with get_engine().begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    _table_ready = True


def insert_telemetry_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    ensure_telemetry_table()
    with get_engine().begin() as connection:
        connection.execute(_INSERT, rows)

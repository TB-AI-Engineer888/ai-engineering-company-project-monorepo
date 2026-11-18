from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import telemetry_storage
from settings import telemetry_endpoint

logger = logging.getLogger("healthcore.telemetry")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(_handler)
logger.propagate = False

telemetry_router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: str = Field(min_length=36, max_length=36)
    timestamp: str = Field(min_length=20, max_length=40)
    sessionId: str | None = None
    userId: str | None = None
    event_type: str = Field(min_length=1, max_length=80)
    schemaVersion: int
    requestId: str = Field(min_length=36, max_length=36)
    properties: dict[str, Any]


class TelemetryIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[Any]


@telemetry_router.post("/events")
def receive_events(body: TelemetryIngest) -> dict[str, int]:
    # Read the configured sink. This phase stores the batch instead of forwarding it.
    _configured = telemetry_endpoint()
    accepted: list[dict[str, Any]] = []
    rejected = 0
    for raw in body.events:
        if not isinstance(raw, dict):
            rejected += 1
            continue
        try:
            TelemetryEvent.model_validate(raw)
        except ValidationError:
            rejected += 1
            continue
        row = telemetry_storage.row_for_event(raw)
        if row is None:
            rejected += 1
            continue
        accepted.append(row)
    if accepted:
        telemetry_storage.insert_telemetry_rows(accepted)
    logger.info(
        "telemetry batch received=%s stored=%s rejected=%s types=%s endpoint_configured=%s",
        len(body.events),
        len(accepted),
        rejected,
        [row["event_type"] for row in accepted],
        bool(_configured),
    )
    return {"received": len(body.events), "stored": len(accepted), "rejected": rejected}

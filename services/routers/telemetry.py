from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

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


class TelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[TelemetryEvent]


@telemetry_router.post("/events")
def receive_events(body: TelemetryBatch) -> dict[str, int]:
    # Read the configured sink now. This phase accepts the batch here and does not forward it.
    _configured = telemetry_endpoint()
    logger.info(
        "telemetry batch received=%s types=%s endpoint_configured=%s",
        len(body.events),
        [event.event_type for event in body.events],
        bool(_configured),
    )
    return {"received": len(body.events)}

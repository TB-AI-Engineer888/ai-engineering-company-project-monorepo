from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from sqlalchemy import bindparam, text

from database import get_engine

_VOLUME_TYPES = (
    "inbound_order_created",
    "outbound_order_created",
    "stock_threshold_triggered",
    "direct_stock_edit_rejected",
    "supply_expiry_flagged",
    "product_registered",
    "incident_analysis_completed",
    "login_succeeded",
    "login_failed",
    "user_login_succeeded",
    "user_login_failed",
    "session_expired",
    "account_registered",
    "outbound_order_rejected",
    "inventory_validation_failed",
    "client_exception_captured",
    "api_latency_recorded",
    "inventory_cache_summarised",
    "backoffice_section_viewed",
    "backoffice_flow_abandoned",
)

_FAILURE_TYPES = (
    "outbound_order_rejected",
    "inventory_validation_failed",
    "client_exception_captured",
)

_AUTH_TYPES = (
    "login_failed",
    "login_succeeded",
    "user_login_failed",
    "user_login_succeeded",
)

_FAILED_LOGIN_TYPES = ("login_failed", "user_login_failed")


def _load(start_date: datetime, end_date: datetime, event_types: tuple[str, ...]) -> pd.DataFrame:
    statement = text(
        """
        SELECT timestamp, event_type, level, value, tags
        FROM telemetry_events
        WHERE timestamp >= :start_date
          AND timestamp < :end_date
          AND event_type IN :event_types
        """
    ).bindparams(bindparam("event_types", expanding=True))
    return pd.read_sql(
        statement,
        get_engine(),
        params={
            "start_date": start_date,
            "end_date": end_date,
            "event_types": list(event_types),
        },
    )


def _with_tags(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "tags" not in frame.columns:
        return frame.drop(columns=["tags"], errors="ignore")
    tags = frame["tags"]
    present = tags.dropna()
    if not present.empty and isinstance(present.iloc[0], str):
        tags = tags.map(json.loads)
    expanded = pd.json_normalize(tags.tolist())
    expanded.index = frame.index
    return frame.drop(columns=["tags"]).join(expanded)


def _with_timestamp(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["date"] = frame["timestamp"].dt.date
    return frame


def events_per_day(start_date: datetime, end_date: datetime) -> list[dict]:
    frame = _load(start_date, end_date, _VOLUME_TYPES)
    frame = frame.dropna(subset=["event_type"])
    if frame.empty:
        return []
    frame = _with_timestamp(frame)
    grouped = frame.groupby(["date", "event_type"], as_index=False).agg(event_count=("event_type", "count"))
    grouped = grouped.sort_values(["date", "event_type"])
    grouped["date"] = grouped["date"].astype(str)
    grouped["event_count"] = grouped["event_count"].astype(int)
    return grouped.reset_index(drop=True).to_dict(orient="records")


def error_rate_by_type(start_date: datetime, end_date: datetime) -> list[dict]:
    frame = _load(start_date, end_date, _VOLUME_TYPES)
    frame = frame.dropna(subset=["event_type"])
    if frame.empty:
        return []
    frame = frame.copy()
    frame["is_error"] = (
        (frame["level"] == "error") | frame["event_type"].isin(_FAILURE_TYPES)
    ).astype(int)
    frame = _with_timestamp(frame)
    grouped = frame.groupby("event_type", as_index=False).agg(
        events=("event_type", "count"),
        errors=("is_error", "sum"),
    )
    grouped["error_rate"] = (grouped["errors"] / grouped["events"]).round(4)
    grouped = grouped.sort_values(["error_rate", "event_type"], ascending=[False, True])
    grouped["events"] = grouped["events"].astype(int)
    grouped["errors"] = grouped["errors"].astype(int)
    grouped["error_rate"] = grouped["error_rate"].astype(float)
    return grouped.reset_index(drop=True).to_dict(orient="records")


def latency_per_day(start_date: datetime, end_date: datetime) -> list[dict]:
    frame = _load(start_date, end_date, ("api_latency_recorded",))
    frame = _with_tags(frame)
    if "duration_ms" not in frame.columns or "route_template" not in frame.columns:
        return []
    frame = frame.dropna(subset=["duration_ms", "route_template"])
    if frame.empty:
        return []
    frame = frame.copy()
    frame["duration_ms"] = pd.to_numeric(frame["duration_ms"])
    frame = _with_timestamp(frame)
    grouped = frame.groupby(["date", "route_template"], as_index=False).agg(
        samples=("duration_ms", "count"),
        mean_duration_ms=("duration_ms", "mean"),
    )
    grouped = grouped.sort_values(["date", "route_template"])
    grouped["date"] = grouped["date"].astype(str)
    grouped["samples"] = grouped["samples"].astype(int)
    grouped["mean_duration_ms"] = grouped["mean_duration_ms"].round(1).astype(float)
    return grouped.reset_index(drop=True).to_dict(orient="records")


def auth_failure_rate(start_date: datetime, end_date: datetime) -> list[dict]:
    frame = _load(start_date, end_date, _AUTH_TYPES)
    frame = frame.dropna(subset=["event_type"])
    if frame.empty:
        return []
    frame = frame.copy()
    frame["is_failed"] = frame["event_type"].isin(_FAILED_LOGIN_TYPES).astype(int)
    frame = _with_timestamp(frame)
    grouped = frame.groupby("date", as_index=False).agg(
        failed=("is_failed", "sum"),
        attempts=("is_failed", "count"),
    )
    grouped["auth_failure_rate"] = (grouped["failed"] / grouped["attempts"]).round(4)
    grouped = grouped.sort_values("date")
    grouped["date"] = grouped["date"].astype(str)
    grouped["failed"] = grouped["failed"].astype(int)
    grouped["attempts"] = grouped["attempts"].astype(int)
    grouped["auth_failure_rate"] = grouped["auth_failure_rate"].astype(float)
    return grouped.reset_index(drop=True).to_dict(orient="records")

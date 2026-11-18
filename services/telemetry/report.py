from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from telemetry import analysis

TTL_SECONDS = 60

_CACHE: dict[tuple[str, str], tuple[float, dict]] = {}


class PeriodError(ValueError):
    pass


def clear_cache() -> None:
    _CACHE.clear()


def _parse_bound(value: str) -> datetime:
    text_value = value.strip()
    if text_value.endswith("Z"):
        text_value = text_value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text_value)
    except ValueError as exc:
        raise PeriodError("start_date and end_date must be ISO 8601 timestamps") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_period(start_date: str | None, end_date: str | None) -> tuple[datetime, datetime]:
    if (start_date is None) != (end_date is None):
        raise PeriodError("Provide both start_date and end_date, or omit both")
    if start_date is None or end_date is None:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)
        return start, end
    start = _parse_bound(start_date)
    end = _parse_bound(end_date)
    if start >= end:
        raise PeriodError("start_date must be earlier than end_date")
    return start, end


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_report(start_date: datetime, end_date: datetime) -> dict:
    return {
        "period": {"from": _iso(start_date), "to": _iso(end_date)},
        "metrics": {
            "events_per_day": analysis.events_per_day(start_date, end_date),
            "error_rate_by_type": analysis.error_rate_by_type(start_date, end_date),
            "latency_per_day": analysis.latency_per_day(start_date, end_date),
            "auth_failure_rate": analysis.auth_failure_rate(start_date, end_date),
        },
    }


def cached_report(start_date: datetime, end_date: datetime) -> dict:
    key = (_iso(start_date), _iso(end_date))
    found = _CACHE.get(key)
    now = time.monotonic()
    if found is not None and now - found[0] < TTL_SECONDS:
        return found[1]
    payload = build_report(start_date, end_date)
    _CACHE[key] = (time.monotonic(), payload)
    return payload

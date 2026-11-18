"""Clinic-month KPI math for the HealthCore supply performance pipeline.

The destination grain is one row per clinic per month. Department stays on the
source event. It is not a column of the reporting table.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

CLINICS: tuple[dict[str, str], ...] = (
    {"clinic_id": "1", "country": "US", "region": "Texas", "currency": "USD"},
    {"clinic_id": "2", "country": "US", "region": "Texas", "currency": "USD"},
    {"clinic_id": "3", "country": "US", "region": "Texas", "currency": "USD"},
    {"clinic_id": "4", "country": "US", "region": "Florida", "currency": "USD"},
    {"clinic_id": "5", "country": "US", "region": "Florida", "currency": "USD"},
    {"clinic_id": "6", "country": "US", "region": "Florida", "currency": "USD"},
    {"clinic_id": "7", "country": "US", "region": "Georgia", "currency": "USD"},
    {"clinic_id": "8", "country": "US", "region": "Georgia", "currency": "USD"},
    {"clinic_id": "9", "country": "US", "region": "Georgia", "currency": "USD"},
    {"clinic_id": "10", "country": "UK", "region": "London", "currency": "GBP"},
    {"clinic_id": "11", "country": "UK", "region": "London", "currency": "GBP"},
    {"clinic_id": "12", "country": "UK", "region": "Manchester", "currency": "GBP"},
)

SUPPLY_EVENT_TYPES = (
    "inbound_order_created",
    "outbound_order_created",
    "stock_threshold_triggered",
    "supply_expiry_flagged",
)

_BY_ID = {clinic["clinic_id"]: clinic for clinic in CLINICS}


def previous_month_start(today: date | None = None) -> date:
    current = today or datetime.now(timezone.utc).date()
    first = current.replace(day=1)
    return (first - timedelta(days=1)).replace(day=1)


def parse_month_start(value: str | date | None) -> date:
    if value is None or value == "":
        return previous_month_start()
    if isinstance(value, datetime):
        return value.date().replace(day=1)
    if isinstance(value, date):
        return value.replace(day=1)
    text = str(value).strip()
    parsed = date.fromisoformat(text[:10])
    return parsed.replace(day=1)


def clinic_directory() -> list[dict[str, str]]:
    """The 12 clinics from the telemetry plan.

    Prefect block ``healthcore-clinic-directory`` holds this same list when it
    is registered. The flow uses this list so a run does not depend on a block
    that has not been saved yet.
    """

    return [dict(clinic) for clinic in CLINICS]


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        try:
            number = float(str(value).strip())
        except ValueError:
            return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def dedup_events(rows: list[dict]) -> tuple[list[dict], int]:
    """Keep the earliest timestamp for each event_id. Rows with no id are rejected."""

    kept: dict[str, dict] = {}
    rejected = 0
    for row in rows:
        event_id = _text(row.get("event_id"))
        if not event_id:
            rejected += 1
            continue
        current = kept.get(event_id)
        if current is None or row["timestamp"] < current["timestamp"]:
            kept[event_id] = row
    return list(kept.values()), rejected


def build_clinic_month(events: list[dict], month_start: date, previous_consumption: dict[str, int] | None = None) -> dict:
    """Aggregate deduped events into 12 clinic rows and the run counts."""

    directory = clinic_directory()
    previous = previous_consumption or {}
    measures = {
        clinic["clinic_id"]: {
            "clinic_id": clinic["clinic_id"],
            "country": clinic["country"],
            "currency": clinic["currency"],
            "total_supply_cost": 0.0,
            "supply_consumption_count": 0,
            "critical_stockout_count": 0,
            "expiry_risk_count": 0,
        }
        for clinic in directory
    }
    rejected = 0
    cost_missing = 0
    sessions: set[str] = set()
    requests: set[str] = set()
    clinics_seen: set[str] = set()

    for event in events:
        event_id = _text(event.get("event_id"))
        request_id = _text(event.get("request_id"))
        session_id = _text(event.get("session_id"))
        clinic_id = _text(event.get("clinic_id"))
        country = _text(event.get("country")).upper()
        clinic = _BY_ID.get(clinic_id)
        if not event_id or clinic is None or country != clinic["country"]:
            rejected += 1
            continue
        if request_id:
            requests.add(request_id)
        if session_id:
            sessions.add(session_id)
        clinics_seen.add(clinic_id)
        kind = event.get("event_type")
        row = measures[clinic_id]
        if kind == "inbound_order_created":
            cost = _number(event.get("total_cost"))
            if cost is None:
                cost_missing += 1
            else:
                row["total_supply_cost"] += cost
        elif kind == "outbound_order_created":
            row["supply_consumption_count"] += 1
        elif kind == "stock_threshold_triggered":
            row["critical_stockout_count"] += 1
        elif kind == "supply_expiry_flagged":
            row["expiry_risk_count"] += 1
        else:
            rejected += 1

    clinics_reporting = len(clinics_seen)
    silent: list[str] = []
    if clinics_reporting > 0:
        for clinic in directory:
            clinic_id = clinic["clinic_id"]
            if measures[clinic_id]["supply_consumption_count"] == 0 and previous.get(clinic_id, 0) > 0:
                silent.append(clinic_id)

    rows = []
    for clinic in directory:
        item = measures[clinic["clinic_id"]]
        item["total_supply_cost"] = round(item["total_supply_cost"], 2)
        rows.append(item)

    return {
        "month_start": month_start.isoformat(),
        "clinics": rows,
        "records_extracted": len(events),
        "records_rejected": rejected,
        "records_loaded": len(rows),
        "cost_missing_count": cost_missing,
        "distinct_session_count": len(sessions),
        "clinics_reporting_count": clinics_reporting,
        "distinct_request_count": len(requests),
        "silent_clinic_ids": ",".join(silent),
    }

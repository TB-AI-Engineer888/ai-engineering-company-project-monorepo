"""HealthCore monthly clinic supply performance flow.

From the monorepo root, with DATABASE_URL set:

    python data/pipelines/pipeline.py
    python data/pipelines/pipeline.py 2026-11-01

The first command computes the previous UTC month. The second computes that month.
Schedule: 06:00 UTC on day 1 of each month.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from prefect import flow, task
from prefect.states import State
from sqlalchemy import text

from data.pipelines import monthly_clinic_supply_performance as impl
from data.process.clinic_supply_kpis import (
    critical_stockout_frequency as critical_stockout_frequency_for,
    expiry_risk_count as expiry_risk_count_for,
    supply_consumption_volume as supply_consumption_volume_for,
    supply_cost_per_clinic as supply_cost_per_clinic_for,
)


def clinic_month_cache_key(_context: object, parameters: dict) -> str:
    # The key is the month plus a digest of the deduped events.
    # It stays valid for one hour. A new or corrected event changes the digest.
    extracted = parameters.get("extracted") or {}
    body = json.dumps(extracted, sort_keys=True, default=str)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"clinic-month-{extracted.get('month_start')}-{digest}"


# Three attempts, ten seconds apart. Extract and load talk to Postgres.
# A Supabase pooler timeout usually clears on the next try. A fourth try would
# mean the outage is no longer transient.
@task(name="extract_supply_events", retries=impl.DB_RETRIES, retry_delay_seconds=impl.DB_RETRY_DELAY_SECONDS)
def extract_supply_events(month_start_iso: str, run_id: str) -> dict:
    return impl.extract_supply_events(month_start_iso, run_id)


@task(name="supply_cost_per_clinic")
def supply_cost_per_clinic(events: list[dict]) -> dict[str, float]:
    return supply_cost_per_clinic_for(events)


@task(name="supply_consumption_volume")
def supply_consumption_volume(events: list[dict]) -> dict[str, int]:
    return supply_consumption_volume_for(events)


@task(name="critical_stockout_frequency")
def critical_stockout_frequency(events: list[dict]) -> dict[str, int]:
    return critical_stockout_frequency_for(events)


@task(name="expiry_risk_count")
def expiry_risk_count(events: list[dict]) -> dict[str, int]:
    return expiry_risk_count_for(events)


@task(
    name="transform_clinic_month_kpis",
    cache_key_fn=clinic_month_cache_key,
    cache_expiration=timedelta(hours=1),
)
def transform_clinic_month_kpis(extracted: dict) -> dict:
    events = extracted["events"]
    supply_cost_per_clinic(events)
    supply_consumption_volume(events)
    critical_stockout_frequency(events)
    expiry_risk_count(events)
    return impl.transform_clinic_month_kpis(extracted)


@task(
    name="load_monthly_clinic_supply_performance",
    retries=impl.DB_RETRIES,
    retry_delay_seconds=impl.DB_RETRY_DELAY_SECONDS,
)
def load_task(result: dict, run_id: str) -> dict:
    return impl.load_monthly_clinic_supply_performance(result, run_id)


@task(name="publish_eval_snapshot")
def publish_eval_snapshot(result: dict) -> str:
    return impl.publish_eval_snapshot(result)


@flow(name="extract_monthly_clinic_supply_events")
def extract_monthly_clinic_supply_events(month_start_iso: str, run_id: str) -> dict:
    return extract_supply_events(month_start_iso, run_id)


@flow(name="transform_monthly_clinic_supply_kpis")
def transform_monthly_clinic_supply_kpis(extracted: dict) -> dict:
    return transform_clinic_month_kpis(extracted)


@flow(name="load_monthly_clinic_supply_performance")
def load_monthly_clinic_supply_performance(result: dict, run_id: str) -> dict:
    return load_task(result, run_id)


@flow(name="publish_clinic_supply_eval_snapshot")
def publish_clinic_supply_eval_snapshot(result: dict) -> str:
    return publish_eval_snapshot(result)


@flow(name="monthly_clinic_supply_performance")
def monthly_clinic_supply_performance(month_start: str | None = None, trigger: str = "schedule") -> str:
    target = impl.parse_month_start(month_start)
    run_id = impl._open_run(target, trigger)
    phase = "extract"
    try:
        extracted = extract_monthly_clinic_supply_events(target.isoformat(), run_id)
        phase = "transform"
        with impl.get_engine().begin() as connection:
            connection.execute(
                text("UPDATE reporting.pipeline_runs SET phase = 'transform' WHERE run_id = :run_id"),
                {"run_id": run_id},
            )
        result = transform_monthly_clinic_supply_kpis(extracted)
        snapshot: State = publish_clinic_supply_eval_snapshot(result, return_state=True)
        if snapshot.is_failed():
            phase = "load"
        phase = "load"
        load_monthly_clinic_supply_performance(result, run_id)
    except Exception as exc:
        impl._fail_run(run_id, phase, str(exc))
        raise
    return run_id


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    month = args[0] if args else None
    monthly_clinic_supply_performance(month_start=month, trigger="schedule")


if __name__ == "__main__":
    main()

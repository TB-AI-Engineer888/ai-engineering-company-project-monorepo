"""Reporting endpoints for the clinic supply performance pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parents[2]
_SERVICES = _ROOT / "services"
_API = _SERVICES / "api"
for _path in (str(_ROOT), str(_SERVICES), str(_API)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from deps import get_current_user

reporting_router = APIRouter(prefix="/reporting", tags=["reporting"])


class ManualRun(BaseModel):
    month_start: str | None = None


def _pipeline():
    from data.pipelines.monthly_clinic_supply_performance import (
        PipelineAlreadyRunning,
        latest_run_status,
        query_monthly_clinic_supply_performance,
        trigger_monthly_clinic_supply_performance,
    )

    return (
        PipelineAlreadyRunning,
        latest_run_status,
        query_monthly_clinic_supply_performance,
        trigger_monthly_clinic_supply_performance,
    )


@reporting_router.get("/pipeline-runs/latest")
def latest_pipeline_run(_user: dict = Depends(get_current_user)) -> dict:
    _already, latest_run_status, _query, _trigger = _pipeline()
    row = latest_run_status()
    if row is None:
        raise HTTPException(status_code=404, detail="No pipeline run has been recorded.")
    return row


@reporting_router.post("/pipeline-runs", status_code=201)
def start_pipeline_run(body: ManualRun | None = None, _user: dict = Depends(get_current_user)) -> dict:
    already, _latest, _query, trigger = _pipeline()
    month_start = None if body is None else body.month_start
    try:
        return trigger(month_start)
    except already as exc:
        raise HTTPException(status_code=409, detail=f"A run is already in progress: {exc}") from exc


@reporting_router.get("/monthly-clinic-supply-performance")
def monthly_clinic_supply_performance(
    month_start: str | None = None,
    _user: dict = Depends(get_current_user),
) -> dict:
    _already, _latest, query, _trigger = _pipeline()
    return query(month_start)

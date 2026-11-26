from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from celery import Celery
from celery.result import AsyncResult
from celery.signals import worker_init
from dotenv import load_dotenv

logger = logging.getLogger("healthcore.tasks")
logger.setLevel(logging.INFO)

_SERVICES_DIR = Path(__file__).resolve().parent
_API_DIR = _SERVICES_DIR / "api"
_REPO_ROOT = _SERVICES_DIR.parent
load_dotenv(_API_DIR / ".env")

ORDER_LIST_REFERENCE = "inventory:orders"
_STATUS = {
    "PENDING": "pending",
    "STARTED": "started",
    "RETRY": "pending",
    "SUCCESS": "success",
    "FAILURE": "failure",
}


def redis_url() -> str:
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        raise RuntimeError("REDIS_URL is not set")
    return url


def retry_countdown(retries: int) -> int:
    return 2**retries


_configured_url = os.environ.get("REDIS_URL", "").strip() or None
celery_app = Celery("healthcore", broker=_configured_url, backend=_configured_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    broker_connection_retry_on_startup=True,
)


def configure() -> None:
    url = redis_url()
    celery_app.conf.broker_url = url
    celery_app.conf.result_backend = url


@worker_init.connect
def _configure_worker(**_kwargs: object) -> None:
    configure()


def _prepare_path() -> None:
    for path in (str(_REPO_ROOT), str(_SERVICES_DIR), str(_API_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)


def _inventory_module():
    _prepare_path()
    loaded = sys.modules.get("healthcore_inventory_router")
    if loaded is not None:
        return loaded
    import importlib.util

    path = _SERVICES_DIR / "routers" / "inventory.py"
    spec = importlib.util.spec_from_file_location("healthcore_inventory_router", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load services/routers/inventory.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_order_rows() -> list[dict]:
    load_order_rows = _inventory_module().load_order_rows
    from database import get_db

    generator = get_db()
    session = next(generator)
    try:
        return [row.model_dump(mode="json") for row in load_order_rows(session)]
    finally:
        generator.close()


def _record_dead_letter(task_id: str, attempt_number: int, error: str) -> None:
    _prepare_path()
    from database import get_engine, init_schema
    from models import DeadLetterTask
    from sqlmodel import Session

    init_schema()
    with Session(get_engine()) as session:
        session.add(
            DeadLetterTask(
                task_id=task_id,
                attempt_number=attempt_number,
                error=error,
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.commit()


def _log_outcome(task_id: str, attempt: int, status: str, started: float, error: str | None = None) -> None:
    duration_ms = (time.perf_counter() - started) * 1000
    if error is None:
        logger.info(
            "task_id=%s attempt=%s status=%s duration_ms=%.1f",
            task_id,
            attempt,
            status,
            duration_ms,
        )
        return
    logger.error(
        "task_id=%s attempt=%s status=%s duration_ms=%.1f error=%s",
        task_id,
        attempt,
        status,
        duration_ms,
        error,
    )


@celery_app.task(
    bind=True,
    name="inventory.load_orders",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=300,
    time_limit=330,
)
def load_inventory_orders(self, reference: str) -> list[dict]:
    configure()
    started = time.perf_counter()
    attempt = self.request.retries + 1
    try:
        if reference != ORDER_LIST_REFERENCE:
            raise ValueError(f"Unknown reference: {reference}")
        rows = _load_order_rows()
    except Exception as exc:
        error = traceback.format_exc()
        _log_outcome(self.request.id, attempt, "failure", started, error)
        if self.request.retries >= self.max_retries:
            _record_dead_letter(self.request.id, attempt, error)
            raise
        countdown = retry_countdown(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    _log_outcome(self.request.id, attempt, "success", started)
    return rows


def enqueue_order_list() -> str:
    configure()
    return load_inventory_orders.delay(ORDER_LIST_REFERENCE).id


def read_task(task_id: str) -> dict:
    configure()
    result = AsyncResult(task_id, app=celery_app)
    state = result.state
    payload = result.result if state == "SUCCESS" else None
    return {
        "task_id": task_id,
        "status": _STATUS.get(state, state.lower()),
        "result": payload,
    }

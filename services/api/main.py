from __future__ import annotations

import importlib.util
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

_API_DIR = Path(__file__).resolve().parent
_SERVICES_DIR = _API_DIR.parent
_ROOT = _API_DIR.parents[1]
for _path in (str(_ROOT / "shared"), str(_SERVICES_DIR), str(_API_DIR)):
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlmodel import Session

from incident_analyzer import AnalysisError, AnalysisResult, analyze_csv_bytes, metrics_to_csv

from database import get_engine, init_schema
from deps import get_current_user
from routers import auth_router, profiles_router, users_router
from seed_inventory import seed_inventory


def _load_inventory_router():
    path = _SERVICES_DIR / "routers" / "inventory.py"
    spec = importlib.util.spec_from_file_location("healthcore_inventory_router", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load services/routers/inventory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inventory_router


inventory_router = _load_inventory_router()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.environ.get("DATABASE_URL", "").strip():
        init_schema()
        with Session(get_engine()) as session:
            seed_inventory(session)
    yield


app = FastAPI(title="HealthCore Incident Analyzer API", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(inventory_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:43123",
        "http://localhost:43123",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_LAST_RESULT: AnalysisResult | None = None
_LAST_CSV: str | None = None
_ROOT = Path(__file__).resolve().parents[2]
_SAMPLE_CSV = _ROOT / "scripts" / "incidents-healthcore.csv"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "healthcore-incident-api"}


@app.get("/api/incidents/sample", dependencies=[Depends(get_current_user)])
def sample_csv() -> FileResponse:
    if not _SAMPLE_CSV.is_file():
        raise HTTPException(status_code=404, detail="Sample CSV is not available.")
    return FileResponse(
        path=_SAMPLE_CSV,
        filename="incidents-healthcore.csv",
        media_type="text/csv",
    )


@app.post("/api/incidents/analyze", dependencies=[Depends(get_current_user)])
async def analyze_incidents(file: UploadFile = File(...)) -> JSONResponse:
    global _LAST_RESULT, _LAST_CSV

    filename = file.filename or "upload.csv"
    suffix = Path(filename).suffix.lower()
    if suffix and suffix not in {".csv", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Incorrect format: '{filename}' is not a CSV file. "
                "Export the incident extract as .csv and try again."
            ),
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="The file is empty. Upload a CSV with a header row and incident records.",
        )

    try:
        result = analyze_csv_bytes(raw, source_name=filename)
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc

    _LAST_RESULT = result
    _LAST_CSV = metrics_to_csv(result)
    return JSONResponse(result.to_dict())


@app.get("/api/incidents/results/export", dependencies=[Depends(get_current_user)])
def export_results() -> Response:
    if _LAST_CSV is None or _LAST_RESULT is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis is available yet. Upload a CSV to POST /api/incidents/analyze first.",
        )
    headers = {
        "Content-Disposition": 'attachment; filename="results.csv"',
    }
    return Response(content=_LAST_CSV, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/api/incidents/results", dependencies=[Depends(get_current_user)])
def last_results() -> dict[str, Any]:
    if _LAST_RESULT is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis is available yet. Upload a CSV to POST /api/incidents/analyze first.",
        )
    return _LAST_RESULT.to_dict()


@app.get("/", dependencies=[Depends(get_current_user)])
def root() -> dict[str, str]:
    return {
        "service": "HealthCore Incident Analyzer API",
        "analyze": "POST /api/incidents/analyze",
        "export": "GET /api/incidents/results/export",
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "status": exc.status_code})

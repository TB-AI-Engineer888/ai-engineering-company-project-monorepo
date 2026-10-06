from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

logger = logging.getLogger("healthcore.api")

from incident_analyzer import AnalysisError, AnalysisResult, analyze_csv_bytes, metrics_to_csv

from deps import get_current_user
from routers import auth_router, profiles_router, users_router

app = FastAPI(title="HealthCore Incident Analyzer API", version="1.0.0")
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)

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

    try:
        raw = await file.read()
    except Exception:
        logger.exception("Upload read failed")
        raise HTTPException(
            status_code=400,
            detail="The file could not be read. Export the incident extract as a CSV and try again.",
        ) from None

    if not raw:
        raise HTTPException(
            status_code=400,
            detail="The file is empty. Upload a CSV with a header row and incident records.",
        )

    try:
        result = analyze_csv_bytes(raw, source_name=filename)
    except AnalysisError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail=_public_detail(exc.message, exc.http_status),
        ) from None
    except Exception:
        logger.exception("Incident analysis failed")
        raise HTTPException(
            status_code=500,
            detail="The file could not be analysed. Check that it is a HealthCore incident CSV and try again.",
        ) from None

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


def _public_detail(detail: object, status_code: int) -> str:
    if isinstance(detail, str):
        text = detail.strip()
        lowered = text.lower()
        leaked = ("traceback", "secret", "pat-", "/home/", "/workspace/", "sqlite", "postgresql://")
        if text and not any(marker in lowered for marker in leaked):
            return text
    if status_code == 401:
        return "Sign in to continue."
    if status_code == 403:
        return "You do not have access to that action."
    if status_code == 404:
        return "The requested item is not available."
    if status_code in {400, 422}:
        return "The request could not be processed. Check the information and try again."
    return "The request could not be completed. Try again, or contact HealthCore support."


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    message = _public_detail(exc.detail, exc.status_code)
    return JSONResponse(status_code=exc.status_code, content={"error": message, "status": exc.status_code})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "The request is missing required information. Check it and try again.",
            "status": 422,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Something went wrong while processing the request. Try again, or contact HealthCore support if it continues.",
            "status": 500,
        },
    )

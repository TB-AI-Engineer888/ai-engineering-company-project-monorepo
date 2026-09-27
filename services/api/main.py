from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from auth_session import login_user, read_me, register_user, require_user, update_profile
from incident_analyzer import AnalysisError, AnalysisResult, analyze_csv_bytes, metrics_to_csv

app = FastAPI(title="HealthCore Incident Analyzer API", version="1.0.0")

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


@app.post("/users")
async def create_user(request: Request) -> JSONResponse:
    return register_user(await _json_body(request))


@app.post("/auth/login")
async def auth_login(request: Request) -> JSONResponse:
    return login_user(await _json_body(request))


@app.get("/auth/me")
def auth_me(account: dict[str, Any] = Depends(read_me)) -> dict[str, Any]:
    return account


@app.put("/profiles/me")
async def profiles_me(
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    return update_profile(await _json_body(request), authorization)


@app.get("/api/incidents/sample")
def sample_csv(_account: dict[str, Any] = Depends(require_user)) -> FileResponse:
    if not _SAMPLE_CSV.is_file():
        raise HTTPException(status_code=404, detail="Sample CSV is not available.")
    return FileResponse(
        path=_SAMPLE_CSV,
        filename="incidents-healthcore.csv",
        media_type="text/csv",
    )


@app.post("/api/incidents/analyze")
async def analyze_incidents(
    file: UploadFile = File(...),
    _account: dict[str, Any] = Depends(require_user),
) -> JSONResponse:
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


@app.get("/api/incidents/results/export")
def export_results(_account: dict[str, Any] = Depends(require_user)) -> Response:
    if _LAST_CSV is None or _LAST_RESULT is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis is available yet. Upload a CSV to POST /api/incidents/analyze first.",
        )
    headers = {
        "Content-Disposition": 'attachment; filename="results.csv"',
    }
    return Response(content=_LAST_CSV, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/api/incidents/results")
def last_results(_account: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if _LAST_RESULT is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis is available yet. Upload a CSV to POST /api/incidents/analyze first.",
        )
    return _LAST_RESULT.to_dict()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "HealthCore Incident Analyzer API",
        "analyze": "POST /api/incidents/analyze",
        "export": "GET /api/incidents/results/export",
    }


async def _json_body(request: Request) -> Any:
    try:
        return await request.json()
    except Exception:
        return None


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "status": exc.status_code})

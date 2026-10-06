#!/usr/bin/env python3
"""Run the HealthCore incident API on an uncommon port."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "shared"
API_DIR = Path(__file__).resolve().parent
for path in (str(SHARED), str(API_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

def main() -> int:
    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn is not installed. Install the API requirements and try again.", file=sys.stderr)
        return 1

    try:
        uvicorn.run("main:app", host="0.0.0.0", port=43180, reload=False)
    except OSError as exc:
        reason = exc.strerror or "the port could not be opened"
        print(f"ERROR: The API could not start ({reason}).", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: The API could not start.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

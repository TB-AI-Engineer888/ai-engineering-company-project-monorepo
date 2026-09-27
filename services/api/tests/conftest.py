from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("AUTH_STORE_PATH", str(Path(tempfile.mkdtemp()) / "accounts.json"))
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "services" / "api"))

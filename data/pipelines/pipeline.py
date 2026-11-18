"""Run the HealthCore monthly clinic supply performance flow.

From the monorepo root, with DATABASE_URL set:

    python data/pipelines/pipeline.py
    python data/pipelines/pipeline.py 2026-11-01

The first command computes the previous UTC month. The second computes that month.
Schedule: 06:00 UTC on day 1 of each month.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.pipelines.monthly_clinic_supply_performance import monthly_clinic_supply_performance


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    month_start = args[0] if args else None
    monthly_clinic_supply_performance(month_start=month_start, trigger="schedule")


if __name__ == "__main__":
    main()

# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## `nightly_export.py`

Exports one UTC day of `telemetry_events` to `data/raw/telemetry_YYYY-MM-DD.csv` when that file is not already there, then runs `python data/pipelines/pipeline.py YYYY-MM-DD`. The run is recorded in `job_runs`. Status moves pending, then processing, then completed or failed. A processing row is the lock: a second process exits without doing the work. A completed row for the same job and day is not repeated.

```bash
python scripts/nightly_export.py
TARGET_DATE=2026-11-22 python scripts/nightly_export.py
```

`DATABASE_URL` must be set. The script does not start the API. The schedule is the operating-system crontab in `nightly_export.cron`: `15 6 * * *` (06:15 UTC).

> _Spanish version: [README.es.md](./README.es.md)._

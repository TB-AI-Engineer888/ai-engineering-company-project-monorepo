# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## `nightly_export.py`

Exporta un día UTC de `telemetry_events` a `data/raw/telemetry_YYYY-MM-DD.csv` si ese archivo no existe, y después ejecuta `python data/pipelines/pipeline.py YYYY-MM-DD`. El resultado queda en `job_runs`. El estado pasa de pending a processing y termina en completed o failed. Una fila en processing es el bloqueo: un segundo proceso sale sin hacer el trabajo. Una fila completed para el mismo trabajo y el mismo día no se repite.

```bash
python scripts/nightly_export.py
TARGET_DATE=2026-11-22 python scripts/nightly_export.py
```

`DATABASE_URL` tiene que estar definido. El script no arranca la API. El horario es el crontab del sistema en `nightly_export.cron`: `15 6 * * *` (06:15 UTC).

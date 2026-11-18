FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_SYSTEM_PYTHON=1

WORKDIR /app/services

# Dependencies already live in services/api/requirements.txt.
COPY api/requirements.txt ./requirements.txt
RUN uv pip install -r requirements.txt

COPY . /app/services

WORKDIR /app/services/api
ENV PYTHONPATH=/app/shared:/app/services:/app/services/api

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/services", "--reload-dir", "/app/shared"]

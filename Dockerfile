FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv \
 && adduser --system --no-create-home --uid 1000 appuser

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock* /app/backend/
RUN cd /app/backend && uv sync --frozen --no-dev || uv sync --no-dev

COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend

ENV DATA_DIR=/data
VOLUME ["/data"]

RUN mkdir -p /data && chown appuser /data
USER appuser

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

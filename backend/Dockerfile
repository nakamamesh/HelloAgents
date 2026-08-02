FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    INGEST_ROOT=/ingest

RUN pip install --no-cache-dir uv

# Build context = monorepo root (fly deploy -c backend/fly.toml from repo root)
COPY backend/pyproject.toml backend/uv.lock backend/alembic.ini ./
COPY backend/app ./app
COPY ingest /ingest

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

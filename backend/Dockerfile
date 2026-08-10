# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.11.17 AS uv

FROM python:3.12-slim AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim AS runtime
ARG RELEASE_SHA=development
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHAN_QUANT_RELEASE_SHA=$RELEASE_SHA
RUN groupadd --system chanquant \
    && useradd --system --gid chanquant --home-dir /app --no-create-home chanquant
WORKDIR /app
COPY --from=builder --chown=chanquant:chanquant /app/.venv ./.venv
USER chanquant
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"]
CMD ["uvicorn", "chan_quant.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]

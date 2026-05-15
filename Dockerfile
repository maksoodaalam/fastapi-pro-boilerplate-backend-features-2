# syntax=docker/dockerfile:1
# Production-oriented image: non-root, slim Python base, healthcheck.
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    APP_PORT=8080

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /usr/sbin/nologin --create-home app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY --chown=app:app . .

USER app

EXPOSE 8080

# Honors APP_PORT from runtime env (must match gunicorn bind port).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${APP_PORT}/api/v1/health" || exit 1'

# WEB_CONCURRENCY: override per host size (e.g. 2× vCPUs, cap ~8).
CMD ["/bin/sh", "-c", "exec gunicorn main:app \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:${APP_PORT:-8080} \
    --workers ${WEB_CONCURRENCY:-2} \
    --threads ${GUNICORN_THREADS:-1} \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-30} \
    --access-logfile - \
    --error-logfile - \
    --capture-output"]

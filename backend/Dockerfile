# ---- Base stage ----
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed for psycopg2 and Pillow (future)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ---- Builder stage ----
FROM base AS builder

COPY requirements/base.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r base.txt

# ---- Dev stage (used by docker-compose) ----
FROM base AS dev

RUN addgroup --system django && adduser --system --ingroup django django \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R django:django /app/media /app/staticfiles


COPY --from=builder /wheels /wheels
COPY requirements/ /tmp/requirements/
RUN pip install --no-cache-dir /wheels/* -r /tmp/requirements/dev.txt

COPY . .
USER django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
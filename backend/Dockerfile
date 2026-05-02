# fundamentals-ai backend
#
# Single-stage python:3.12-slim. The whole project's dependency footprint
# (yfinance + pandas + pdfplumber + ...) makes the image roughly 600 MB; that
# is acceptable for a showcase repo. Multi-stage / uv can be revisited if
# build time becomes a problem.

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# `curl` is required by the container HEALTHCHECK below. We do *not* install
# build-essential — every Python dep we use ships a manylinux wheel for
# CPython 3.12 / amd64 + arm64. If a future dep needs gcc, add it here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --upgrade pip \
    && pip install .

RUN useradd --uid 1000 --create-home --shell /bin/bash fundamentals \
    && chown -R fundamentals:fundamentals /app
USER fundamentals

EXPOSE 8000

# /health is intentionally cheap — does not touch DB or Redis. /ready is the
# expensive readiness probe.
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

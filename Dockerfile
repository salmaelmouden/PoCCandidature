# Deployment image (Railway / any container host).
#
# Local development does NOT use this file: docker-compose mounts the source and a
# host-built .venv, because installing from PyPI inside a container fails behind the
# corporate TLS proxy. A normal network has no such problem, so the deployed image
# installs normally.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# psycopg[binary] and every other dependency ship wheels for slim, so no compiler
# toolchain is needed — keep the image small and the build fast.
COPY pyproject.toml README.md ./
COPY app ./app
COPY dashboard ./dashboard
RUN pip install .

COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

# Streamlit's usage telemetry is off by default here: this page is shared with
# third parties and should phone home as little as possible.
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8080

# FastAPI/Uvicorn server (default for Railway deployment).
# $PORT is injected by the platform; 8080 is the local fallback.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]


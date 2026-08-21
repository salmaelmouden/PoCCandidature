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

# Deliberately no EXPOSE. The listening port is decided at runtime by $PORT, and
# every start command below honours it. A hardcoded EXPOSE is worse than none
# here: Railway reads it when choosing the target port for a generated domain, so
# a stale value silently routes the public URL at a port nothing is listening on
# and the edge returns "Application failed to respond" while the container is
# perfectly healthy. Set PORT explicitly on the service instead — see
# docs/guides/deploy-railway.md.

# The dashboard service. The API and the refresher run this same image with a
# different start command (see docs/guides/deploy-railway.md).
# $PORT is injected by the platform; 8501 is the local fallback.
CMD ["sh", "-c", "alembic upgrade head && exec streamlit run dashboard/Home.py --server.port ${PORT:-8501} --server.address 0.0.0.0 --server.headless true"]

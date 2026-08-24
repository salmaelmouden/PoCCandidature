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

# psycopg needs libpq. The psycopg[binary] wheel bundles its own copy, so in
# theory nothing is needed here — but that wheel does not reliably land: a deploy
# installed psycopg without psycopg_binary and the container crash-looped on
#
#   ImportError: no pq wrapper available.
#     - couldn't import psycopg 'binary' implementation: No module named 'psycopg_binary'
#     - couldn't import psycopg 'python' implementation: libpq library not found
#
# libpq5 is the runtime library on its own (356 KB), which lets the pure-Python
# implementation work whenever the binary wheel is absent. Note it is NOT
# libpq-dev + build-essential: no compiler toolchain is needed to install these
# dependencies, and an earlier image that carried one was ~110 MB larger for no
# benefit. Keep this to the runtime library.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY dashboard ./dashboard
RUN pip install .

# Fail the build rather than the deploy. Without this, a broken psycopg install
# surfaces much later as a healthcheck timeout, with the real cause buried in a
# restart loop — which is exactly how the failure above presented.
RUN python -c "from psycopg import pq; print('psycopg pq impl:', pq.__impl__)"

COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

# Streamlit reads `$CWD/.streamlit/config.toml`, and WORKDIR is where the start
# command runs — so the theme has to be copied explicitly. This image copies
# named paths rather than the whole context, which is why a new top-level
# directory does not arrive on its own. Kept after `pip install .` so editing the
# theme does not invalidate the dependency layer.
COPY .streamlit ./.streamlit

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

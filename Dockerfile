FROM python:3.12-slim

# Install system dependencies required for psycopg and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Run migrations and start app
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080


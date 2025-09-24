FROM python:3.13.7-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install Python dependencies with uv
COPY ./pyproject.toml ./uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Install development-specific dependencies
RUN uv add \
    django-debug-toolbar \
    django-extensions \
    ipython \
    ipdb \
    watchdog

# Copy application (will be overridden by volume mount)
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/static /app/media /app/logs

# Development server runs as root (simplified for dev)
EXPOSE 8000

# This will be overridden by docker-compose command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
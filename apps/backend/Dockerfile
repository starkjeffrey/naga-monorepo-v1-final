
# Naga Backend Dockerfile
# Multi-stage build for production Django application

# =====================================
# BUILDER STAGE
# =====================================
FROM python:3.13.7-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# =====================================
# PRODUCTION STAGE
# =====================================
FROM python:3.13.7-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    gettext \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r django && useradd -r -g django django

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Set proper permissions
RUN chown -R django:django /app

# Switch to non-root user
USER django

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health/', timeout=10)" || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# syntax=docker/dockerfile:1
FROM docker.io/python:3.13.7-slim-trixie AS python

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Python build stage
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

# Install build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev

# Python run stage
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BUILD_ENV=${BUILD_ENVIRONMENT} \
    DJANGO_SETTINGS_MODULE=config.settings.local \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

WORKDIR ${APP_HOME}

# Install runtime dependencies and create user in one layer
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install --no-install-recommends -y \
    bash-completion \
    ca-certificates \
    curl \
    gettext \
    git \
    gnupg \
    libpq-dev \
    nano \
    postgresql-client \
    ssh \
    sudo \
    wait-for-it && \
    # Install Node.js 22.x from NodeSource  
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install --no-install-recommends -y nodejs && \
    # Create dev user with sudo access
    groupadd --gid 1000 dev-user && \
    useradd --uid 1000 --gid dev-user --shell /bin/bash --create-home dev-user && \
    echo dev-user ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/dev-user && \
    chmod 0440 /etc/sudoers.d/dev-user && \
    # Clean up
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/* && \
    # Create static and media directories
    mkdir -p ${APP_HOME}/staticfiles/ ${APP_HOME}/mediafiles/ && \
    chown -R dev-user:dev-user ${APP_HOME}

# Install dependencies
COPY ./pyproject.toml ./uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    rm -rf build dist *.egg-info && \
    uv sync --frozen --extra dev

# Copy scripts and make them executable
COPY ./compose/local/django/entrypoint /entrypoint
COPY ./compose/local/django/start /start
COPY ./compose/local/django/dramatiq/start /start-dramatiq
RUN chmod +x /entrypoint /start*

# Copy application code
COPY . ${APP_HOME}

# Use dev-user for local development
USER dev-user

ENTRYPOINT ["/entrypoint"]

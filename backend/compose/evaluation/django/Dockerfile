# syntax=docker/dockerfile:1
FROM docker.io/python:3.13.7-slim-trixie AS python

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# Python build stage
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=evaluation
ARG APP_HOME=/app

# Install build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev

# Python run stage
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=evaluation
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BUILD_ENV=${BUILD_ENVIRONMENT} \
    DJANGO_SETTINGS_MODULE=config.settings.evaluation

WORKDIR ${APP_HOME}

# Install runtime dependencies - hybrid approach combining local debugging with production stability
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install --no-install-recommends -y \
    # Production essentials
    postgresql-client \
    libpq-dev \
    wait-for-it \
    gettext \
    curl \
    ca-certificates \
    gnupg \
    tini \
    # Local debugging tools for evaluation environment
    git \
    nano \
    htop \
    less \
    tree \
    tcpdump \
    strace \
    procps \
    # Node.js for monorepo tooling and schema generation
    && \
    # Install Node.js 18.x from NodeSource
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install --no-install-recommends -y nodejs && \
    # Create evaluation user (more secure than dev-user, but with some debugging capabilities)
    groupadd --gid 1000 evaluation && \
    useradd --uid 1000 --gid evaluation --shell /bin/bash --create-home evaluation && \
    # Clean up
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/* && \
    # Create static and media directories
    mkdir -p ${APP_HOME}/staticfiles/ && \
    mkdir -p ${APP_HOME}/mediafiles/ && \
    mkdir -p ${APP_HOME}/logs/ && \
    chown -R evaluation:evaluation ${APP_HOME}

# Install dependencies with both production and dev dependencies for evaluation
COPY ./pyproject.toml ./uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    rm -rf build dist *.egg-info && \
    uv pip install --system -e ".[prod,monitoring,dev]"

# Copy scripts and make them executable
COPY ./compose/evaluation/django/entrypoint /entrypoint
COPY ./compose/evaluation/django/start /start
COPY ./compose/evaluation/django/dramatiq/start /start-dramatiq
RUN chmod +x /entrypoint /start*

# Copy application code
COPY --chown=evaluation:evaluation . ${APP_HOME}

# Skip message compilation for evaluation (translations not critical)
# RUN DATABASE_URL="" \
#     DJANGO_SETTINGS_MODULE="config.settings.evaluation" \
#     python manage.py compilemessages

# Create evaluation-specific log directory and set permissions
RUN mkdir -p /var/log/naga-evaluation && \
    chown -R evaluation:evaluation /var/log/naga-evaluation

USER evaluation

ENTRYPOINT ["tini", "--", "/entrypoint"]
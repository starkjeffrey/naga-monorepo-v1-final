# Simple Python container for documentation
FROM docker.io/python:3.13.7-slim-trixie

ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    USE_DOCKER=no \
    DATABASE_URL=sqlite:///docs.db \
    DJANGO_SETTINGS_MODULE=config.settings.local

WORKDIR ${APP_HOME}

# Install system dependencies and Tectonic for PDF output
RUN apt-get update && apt-get install --no-install-recommends -y \
    make \
    libpq-dev \
    gettext \
    curl \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Install Tectonic (modern, lightweight LaTeX engine)
# Auto-detect architecture and install appropriate binary
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        TECTONIC_URL="https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-unknown-linux-musl.tar.gz"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        TECTONIC_URL="https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-aarch64-unknown-linux-musl.tar.gz"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl -L "$TECTONIC_URL" | tar -xz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/tectonic

# Install Python dependencies
COPY ./pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY . ${APP_HOME}

COPY ./compose/local/docs/start /start-docs
RUN sed -i 's/\r$//g' /start-docs
RUN chmod +x /start-docs

WORKDIR /docs

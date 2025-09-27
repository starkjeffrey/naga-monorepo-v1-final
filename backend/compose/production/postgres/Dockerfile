FROM docker.io/postgres:18

# Install additional tools for production monitoring and maintenance
RUN apt-get update && apt-get install -y \
    postgresql-contrib \
    postgresql-16-pg-stat-statements \
    curl \
    wget \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy maintenance scripts
COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
# Move all executable files to /usr/local/bin and recursively remove the entire maintenance directory
RUN find /usr/local/bin/maintenance -type f -executable -exec mv {} /usr/local/bin/ \; \
    && rm -rf /usr/local/bin/maintenance

# Copy production PostgreSQL configuration
COPY ./compose/production/postgres/postgresql.conf /etc/postgresql/postgresql.conf
COPY ./compose/production/postgres/pg_hba.conf /etc/postgresql/pg_hba.conf

# Copy initialization scripts
COPY ./compose/production/postgres/init-scripts/ /docker-entrypoint-initdb.d/

# Create directories for backups and logs
RUN mkdir -p /backups /var/log/postgresql && \
    chown -R postgres:postgres /backups /var/log/postgresql

# Copy health check script
COPY ./compose/production/postgres/health-check.sh /usr/local/bin/health-check.sh
RUN chmod +x /usr/local/bin/health-check.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD /usr/local/bin/health-check.sh

# Set environment variables for production optimization
ENV POSTGRES_INITDB_ARGS="--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
ENV POSTGRES_HOST_AUTH_METHOD=md5

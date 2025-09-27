FROM docker.io/postgres:18

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
# Move all executable files to /usr/local/bin and recursively remove the entire maintenance directory
RUN find /usr/local/bin/maintenance -type f -executable -exec mv {} /usr/local/bin/ \; \
    && rm -rf /usr/local/bin/maintenance

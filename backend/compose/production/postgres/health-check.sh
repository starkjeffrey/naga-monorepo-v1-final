#!/bin/bash
# PostgreSQL Health Check Script for Staff-Web V2 Production

set -e

# Check if PostgreSQL is accepting connections
pg_isready -h localhost -p 5432 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t 5

# Check if we can perform a simple query
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -p 5432 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT 1;" > /dev/null

# Check database size and connections
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -p 5432 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c "
SELECT
    CASE
        WHEN count(*) > 180 THEN 'WARN: High connection count: ' || count(*)::text
        ELSE 'OK: Connection count: ' || count(*)::text
    END
FROM pg_stat_activity
WHERE state = 'active';" 2>/dev/null || echo "Could not check connection count"

# Check for long-running queries (over 5 minutes)
LONG_QUERIES=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -p 5432 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c "
SELECT count(*)
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '5 minutes';" 2>/dev/null || echo "0")

if [ "${LONG_QUERIES}" -gt "0" ]; then
    echo "WARN: ${LONG_QUERIES} long-running queries detected"
fi

# Check replication lag (if applicable)
# PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -p 5432 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c "
# SELECT CASE
#     WHEN pg_is_in_recovery() THEN
#         CASE
#             WHEN (extract(epoch from now()) - extract(epoch from pg_last_xact_replay_timestamp())) > 300
#             THEN 'WARN: Replication lag: ' || (extract(epoch from now()) - extract(epoch from pg_last_xact_replay_timestamp()))::int || ' seconds'
#             ELSE 'OK: Replication lag: ' || (extract(epoch from now()) - extract(epoch from pg_last_xact_replay_timestamp()))::int || ' seconds'
#         END
#     ELSE 'OK: Primary server'
# END;" 2>/dev/null || echo "Could not check replication status"

echo "PostgreSQL health check passed"
exit 0
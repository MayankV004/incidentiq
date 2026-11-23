# Runbook: Orders Database Connection Pool Exhaustion

## Metadata
- Service: orders
- Category: db_pool_exhaustion
- Severity: P0 / Critical

## Symptoms
- HTTP 500 Internal Server Errors spike on `POST /orders` and `/checkout`.
- Metric `db_pool_in_use` reaches 100% of `MAX_DB_POOL_SIZE` (e.g. 10/10).
- Log lines contain: `FATAL: remaining connection slots are reserved for non-replication superuser connections` or `Database connection pool exhausted: too many connections`.

## Diagnosis Steps
1. Query `db_pool_in_use` metric over the last 30 minutes to verify if pool usage hit maximum capacity.
2. Inspect `orders` logs for unclosed connection leaks or unhandled transaction exceptions.
3. Check if downstream traffic spiked or if connections are hanging due to slow locks.

## Remediation
- **Immediate action:** Execute `review_config` to double the `MAX_DB_POOL_SIZE` or execute `restart_service` on `orders` to purge leaked connection handles.
- **Dry-run command:** `review_config(service="orders", parameter="MAX_DB_POOL_SIZE", proposed_value="20")`.

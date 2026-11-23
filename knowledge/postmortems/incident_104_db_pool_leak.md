# Postmortem: Incident #104 - Orders Database Connection Exhaustion

## Incident Summary
- Date: 2026-10-14
- Impact: 28% of customer checkouts failed with HTTP 500 over a 22-minute window.
- Root Cause: A newly deployed checkout retry handler failed to release database connection handles on socket timeouts, exhausting the 10-connection pool on the orders service.

## Key Indicators
- `db_pool_in_use` pegged at 10.
- Log message: `FATAL: remaining connection slots are reserved for non-replication superuser connections`.

## Recovery Actions
- Restarted orders service pods to immediately terminate leaked connections.
- Increased connection pool limit from 10 to 25.

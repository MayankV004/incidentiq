# Postmortem: Incident #108 - Orders Cache Failure & Postgres Stampede

## Incident Summary
- Date: 2026-10-28
- Impact: Order query latency spiked from 35ms to 2400ms across 100% of read traffic for 18 minutes.
- Root Cause: Redis connection limit was exhausted during a background backup, causing orders service connections to be rejected. Uncached read requests flooded PostgreSQL, driving database CPU to 96%.

## Key Indicators
- Metric `cache_hit_rate` dropped instantly from 0.92 to 0.00.
- Application logs reported: `ConnectionRefusedError: [Errno 111] Connection refused connecting to redis:6379`.
- Secondary metric `db_pool_in_use` jumped from 3 to 10 within 60 seconds.

## Recovery Actions
- Restored Redis container connectivity and flushed stale client pool handles.
- Executed `review_config` on orders service to enable temporary rate limiting on non-critical queries.
- Added circuit-breaker fallback to gracefully serve stale cached data rather than hammering PostgreSQL.

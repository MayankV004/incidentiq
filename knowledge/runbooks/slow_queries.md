# Runbook: Slow Database Queries and Index Degradation

## Metadata
- Service: orders
- Category: slow_db_query
- Severity: P2 / Medium

## Symptoms
- Latency p95 degrades significantly (> 3.0s) without high error rates.
- Metric `latency_p95` on `orders` elevated, but `error_rate` remains near 0.
- Logs report `slow_query_execution` with query durations exceeding 3000ms.

## Diagnosis Steps
1. Inspect query logs for missing indexes or sequential table scans on `orders`.
2. Check `db_pool_in_use` to confirm the pool is not exhausted.

## Remediation
- Add missing B-tree index on queried columns (`order_id`, `created_at`).
- Cache frequent lookup queries in Redis.

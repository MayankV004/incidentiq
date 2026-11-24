# Runbook: Redis Cache Failure and Eviction Storm

## Metadata
- Service: orders
- Category: cache_failure
- Severity: P1 / High

## Symptoms
- Metric `cache_hit_rate` drops abruptly from normal levels (>0.85) to near 0.00.
- Latency `latency_p95` elevates across read-heavy endpoints due to backend database cache stampede.
- Application logs contain: `redis.exceptions.ConnectionError`, `ConnectionRefusedError: [Errno 111] Connection refused`, or `Redis cache unreachable; falling back to direct database reads`.
- Secondary symptoms: Database pool utilization (`db_pool_in_use`) climbs as uncached traffic directly hits PostgreSQL.

## Diagnosis Steps
1. Query `cache_hit_rate` metric over the last 30 minutes to confirm an instantaneous collapse.
2. Check `orders` container logs for Redis connection pool timeouts or connection refusal errors.
3. Verify Redis container process health, memory saturation (OOM), or eviction policy exhaustion.

## Remediation
- **Immediate action:** Execute `restart_service` on `orders` to recreate stale Redis client connection pools, or execute `review_config` to enable degraded database bypass.
- **Dry-run command:** `review_config(service="orders", parameter="CACHE_ENABLED", proposed_value="false")`.

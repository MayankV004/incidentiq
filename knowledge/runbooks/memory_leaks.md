# Runbook: Container Memory Leak and OOMKilled Restarts

## Metadata
- Service: gateway
- Category: memory_leak
- Severity: P1 / High

## Symptoms
- Metric `memory_mb` demonstrates monotonic linear growth over time.
- Periodic service restarts with exit code 137 (SIGKILL / OOMKilled).
- Logs show `high_memory_watermark` and `Out of memory (OOMKilled)`.

## Diagnosis Steps
1. Query `memory_mb` over 60 minutes to confirm upward staircase pattern.
2. Inspect heap allocations and object retention in middleware.

## Remediation
- Immediate: Execute `restart_service` to reset memory footprint.
- Permanent: Patch memory retention leak in request contextvars.

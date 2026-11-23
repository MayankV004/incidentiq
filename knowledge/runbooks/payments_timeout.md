# Runbook: Third-Party Payment Gateway Dependency Timeout

## Metadata
- Service: payments
- Category: dependency_timeout
- Severity: P1 / High

## Symptoms
- HTTP 504 Gateway Timeout on checkout requests.
- Metric `latency_p95` on `payments` service spikes above 5.0 seconds.
- Log lines contain: `external_payment_timeout` or `ReadTimeout after 5000ms calling fake_external:8004`.

## Diagnosis Steps
1. Verify if `payments` latency correlates with external API response times.
2. Check external payment provider status page or error logs.
3. Determine if circuit breaker has tripped.

## Remediation
- **Immediate action:** Enable downstream circuit breaker, fail over to backup payment provider, or execute `review_config` to adjust client request timeouts.
- **Dry-run command:** `review_config(service="payments", parameter="PAYMENTS_TIMEOUT_SEC", proposed_value="2.5")`.

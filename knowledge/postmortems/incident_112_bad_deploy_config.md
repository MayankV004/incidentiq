# Postmortem: Incident #112 - Payments Bad Deployment Config CrashLoop

## Incident Summary
- Date: 2026-11-02
- Impact: 100% of checkout payments failed with HTTP 502 Bad Gateway for 12 minutes following Release v2.5.1.
- Root Cause: A newly merged PR added a required environment variable `PAYMENTS_PROVIDER_SECRET` to the application Pydantic config settings. The production Kubernetes deployment manifest was not updated, causing pods to crash immediately upon boot.

## Key Indicators
- Payments container crashed on startup with exit code 1.
- Log message: `pydantic_core.ValidationError: 1 validation error for Settings: PAYMENTS_PROVIDER_SECRET Field required`.
- Gateway ingress logged: `HTTP 502 Bad Gateway: Upstream payments service connection refused`.

## Recovery Actions
- Automated triage triggered an emergency rollback to stable image tag `v2.4.0` via `rollback_deploy`.
- Service restored to full health within 90 seconds of rollback execution receipt.
- Added CI pre-flight automated check verifying that all Pydantic required fields exist in production secret templates.

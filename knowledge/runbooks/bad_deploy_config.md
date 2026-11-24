# Runbook: Bad Deployment Configuration and CrashLoops

## Metadata
- Service: payments
- Category: bad_deploy_config
- Severity: P0 / Critical

## Symptoms
- Service pods enter `CrashLoopBackOff` or terminate with exit code 1 / 2 immediately following a deployment.
- HTTP 502 Bad Gateway or 503 Service Unavailable across all service endpoints.
- Error logs display initialization failures: `pydantic_core.ValidationError`, `KeyError: 'STRIPE_API_KEY'`, `Missing required environment variable`, or `ConfigurationError: invalid database URL`.
- Deployment marker logs contain recent release tags or commit hashes (e.g. `release_v2.5.1`, `commit_sha`).

## Diagnosis Steps
1. Inspect container startup logs for unhandled configuration parsing exceptions.
2. Cross-reference the latest deployment event / git commit hash against production environment variables.
3. Verify if newly required secrets or config keys are missing from the environment or ConfigMap.

## Remediation
- **Immediate action:** Execute `rollback_deploy` to immediately restore the preceding stable container image release tag.
- **Dry-run command:** `rollback_deploy(service="payments", target_version="v2.4.0")`.

# IncidentIQ Remediation Log (`FIX_LOG.md`)

This log tracks every finding verified, reproduced, and remediated on the `fix/audit-remediation` branch against the specifications in `docs/` and the reports in `reports/AUDIT_REPORT.md` and `reports/CODE_REVIEW_REPORT.md`.

---

## Baseline State (Phase 0)

- **Branch Created:** `fix/audit-remediation`
- **Pytest Output:**
  ```
  collected 6 items
  tests/unit/test_core.py ..... [83%]
  tests/unit/test_db.py .       [100%]
  6 passed in 1.10s
  ```
- **Ruff Check Output:**
  ```
  All checks passed!
  ```
- **Ruff Format Check Output:**
  ```
  19 files would be reformatted, 23 files already formatted
  ```
- **Mypy Baseline Output:**
  `mypy` was not previously installed. Installed `mypy>=1.15.0` and configured `[tool.mypy]` in `pyproject.toml`.
  Initial type-check baseline across 29 source files (`incidentiq`, `mcp_servers`, `shop`, `evals`, `tests`):
  **Total type errors found: 13 errors in 7 files** (to be resolved on touched files during subsequent phases and Phase 6).

---

## Remediation Entries

| Finding ID | Title | Reproduced? | Root Cause | Fix Summary | Test Added | Commit Hash |
|---|---|---|---|---|---|---|
| **CR-09** | Missing mypy configuration & type checker | Yes (executable not found) | No mypy dependency or config in `pyproject.toml` | Installed `mypy` and configured `[tool.mypy]` | Baseline mypy check recorded (13 errors across repo) | `0365dee` |
| **AUD-01** | Remediation capability token authorization bypass | Yes (forged prefix passed, replayed successfully) | `verify_approval_token` checked prefix `appr_` and ignored `APPROVAL_TOKEN_SECRET` | Implemented HMAC-SHA256 capability tokens bound to incident, action, target, 15m TTL, and single-use nonces | `tests/unit/test_security_tokens.py` (8 unit tests) | `f10e43a` |
| **AUD-02** | Capability token leaked in plaintext via SSE and REST API | Yes (raw token present in SSE event and GET endpoint) | Raw capability token stored in state and emitted over SSE / REST | UI only receives `approval_id`; capability tokens kept strictly server-side and hashed at rest | `test_raw_token_never_exposed_in_sse_or_rest` | `f10e43a` |
| **AUD-03** | Public endpoints lack auth, rate limits, and use wildcard CORS | Yes (unauthenticated requests succeeded, no rate limits) | Missing auth middleware and rate limiting on `/v1/*`; CORS wildcard origins | Added `SecurityAndRateLimitMiddleware` with `X-API-Key` constant-time check, sliding-window rate limits, daily budget cap, explicit CORS origins, and unauthenticated `/healthz`/`/readyz` | `tests/unit/test_api_security.py` (5 unit tests) | `020bdad` |
| **AUD-04** | Raw alert PII persisted to database before guardrails execute | Yes (raw email, phone, credit card written to DB on creation) | `create_incident` inserted raw alert before `input_guard_node` ran | Executed `GuardrailManager.process_input_alert` before persistence or queueing; sanitized alert stored | `test_pii_redacted_before_persistence_and_raw_alert` | `020bdad` |
| **AUD-06** | Path traversal and PromQL injection in MCP servers | Yes (`service` and `scenario_id` interpolated without path validation) | Unsanitized string concatenation in log paths and PromQL queries | Added `mcp_servers/validation.py` enforcing `ALLOWED_SERVICES`, strict `scenario_id` regex, path traversal barriers, and PromQL sanitization | `tests/unit/test_mcp_security.py` (8 unit tests) | `6cc6e9e` |
| **CR-01 / CR-08** | Mismatched hypothesis schema and hardcoded UI report narrative | Yes (UI types missing category, ReportView hardcoded DB pool narrative) | Backend/frontend schema divergence and static mockup text in React component | Aligned `category` field across frontend/backend, rendered dynamic reasoning and interactive citations | `tests/unit/test_diagnosis_category.py` (2 unit tests) | `ffaebde` |
| **CR-02** | Missing PostgreSQL driver crashes runtime when configured via `.env` | Yes (`ModuleNotFoundError: No module named 'psycopg'` on create_engine) | Missing driver in dependencies and session.py lacked explicit postgresql+psycopg translation | Added `psycopg[binary]>=3.2.0` to pyproject.toml and added `get_sync_database_url` in session.py | `tests/unit/test_db_session.py` (2 unit tests) | `3082adf` |
| **CR-04** | Time window `minutes` parameter ignored; query limit uncapped | Yes (limit unbounded, minutes ignored in filtering, get_log_context ignored line_id) | Missing window/limit clamping and line_id index lookup | Clamped `minutes` to 1..180, capped `limit` to 50 and context to 20; added timestamp filtering and target line matching | `tests/unit/test_mcp_limits.py` (4 unit tests) | `b3d6024` |
| **CR-06** | Silent exception swallowing in LLM diagnosis node & swallowed DB errors | Yes (exceptions caught at warning without recording error in state, DB upserts logged at debug) | `_call_llm_for_diagnosis` swallowed errors without setting state/telemetry; DB errors logged at debug | Set `is_fallback=True`, recorded `error` in state, logged LLM errors and surfaced DB failures at ERROR level | `tests/unit/test_llm_fallback.py` (2 unit tests) | `[CR-06]` |

---

## Needs Decision (Phase 5 Proposals)

---

## Docs to Update

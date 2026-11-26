# API Specification: IncidentIQ

Base URL: `/v1`. JSON over HTTP. Streaming via Server-Sent Events (SSE). Auth for the public demo: a static API key header `X-API-Key` verified with constant-time comparison (`hmac.compare_digest`), rate limits keyed on trusted-proxy client IP, and fail-fast startup enforcement (`API_KEY` and `APPROVAL_TOKEN_SECRET` must be set). FastAPI generates the OpenAPI document at `/docs`.

## 0. Browser Proxy Architecture & Implementation Alignment
- **Next.js Server-Side BFF Proxy (`/api/v1/[...path]`):** All browser calls go same-origin to `/api/v1/*` on the Next.js server, which injects `X-API-Key` from server environment (`API_KEY`), forwards upstream to `API_INTERNAL_URL`, and streams `text/event-stream` directly without ever exposing `API_KEY` to the browser.
- **Standard Error Envelope:** HTTP `400`, `401`, `403`, `404`, `409`, `422` (`VALIDATION_ERROR`), `429` (`RATE_LIMIT_EXCEEDED` / `BUDGET_EXCEEDED`), and `500` (`INTERNAL_ERROR`) all return `{ "error": { "code", "message", "details" } }`.
- **Input Validation (`POST /v1/incidents`):** Rejects unknown services outside `ALLOWED_SERVICES`, traversal payloads in `scenario_id`, empty/oversized `symptom`, and `window_end <= window_start` with HTTP `400`.
- **Stream Endpoint & Approvals:** Live SSE endpoint is `GET /v1/incidents/{id}/stream` (terminating cleanly on `completed`, `awaiting_approval`, `abstained`, `budget_exceeded`, `failed`, `remediation_executed`, and `rejected_by_human`). `POST /v1/incidents/{id}/approval` accepts `approval_id` and `decision` (`"approve"` | `"reject"`), keeping raw capability tokens strictly server-side.
- **Outcome Feedback (`POST /v1/incidents/{id}/feedback`):** Accepts `{ "verdict": "correct_root_cause" | "wrong_root_cause" | "good_abstention" | "false_alarm", "corrected_category"?: str, "notes"?: str, "submitted_by"?: str }`, scrubs PII before saving to `incident_feedback`, feeds `memory_agent` episodic recall and `evals/score_live.py`, and surfaces `"feedback"` on `GET /v1/incidents/{id}`.
- **Readiness (`/readyz`):** Probes SQLite (`SELECT 1`) and (when `MCP_MODE=http`) connectivity to `mcp-metrics`, `mcp-logs`, and `mcp-remediation`, returning HTTP `503` if any dependency is unavailable.

## 1. Conventions

- IDs are UUIDs unless stated.
- Timestamps are ISO 8601 UTC.
- Errors use one shape:

```json
{ "error": { "code": "validation_error", "message": "window_end must be after window_start", "details": {} } }
```

- **Error envelope codes implemented in `incidentiq/api/main.py` and `security.py`:**

| HTTP | `code` | Meaning |
|---|---|---|
| 400 | `INVALID_INPUT` | Bad input (`service`, `scenario_id`, empty/oversized `symptom`, bad window) |
| 401 | `UNAUTHORIZED` | Missing or wrong `X-API-Key` |
| 403 | `FORBIDDEN` | Invalid/mismatched `approval_id` or consumed approval token |
| 404 | `NOT_FOUND` | Unknown incident ID |
| 409 | `STATE_CONFLICT` | State conflict (e.g. approving when status is not `awaiting_approval`) |
| 422 | `VALIDATION_ERROR` | Pydantic request validation failed or invalid `feedback` verdict |
| 429 | `RATE_LIMIT_EXCEEDED` / `BUDGET_EXCEEDED` | IP rate limit (`5/min` create, `30/min` read) or `DAILY_COST_CAP_USD` exceeded |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

## 2. Incidents & Scenarios

### GET /v1/scenarios
Lists available benchmark scenarios loaded from `scenarios/0*` (`id`, `number`, `title`, `service`, `symptom`, `expected_root_cause`, `expected_action`, `window_start`, `window_end`).

### POST /v1/incidents
Create and queue an investigation. (Note: `DATA_MODE=live|replay` controls MCP server mode; passing `scenario_id` targets a replay scenario per call. There is no `source` field on `CreateIncidentRequest`.)

Request:
```json
{
  "service": "orders",
  "symptom": "p95 latency 4s, error rate 12%",
  "window_start": "2026-11-20T14:00:00Z",
  "window_end": "2026-11-20T14:30:00Z",
  "scenario_id": null
}
```

Response `202`:
```json
{ "incident_id": "inc_b7e1...", "status": "queued", "message": "Incident investigation launched" }
```

### GET /v1/incidents/{id}
Returns incident record (`incident_id`, `scenario_id`, `alert`, `status`, `hypothesis`, `evidence`, `cost_usd`, `latency_ms`, `steps`, `guardrail_flags`, `approval`, `events`, `langfuse_trace_url`, `error`, `created_at`, `completed_at`, and optional `feedback`; server-side `token_hash` and `approval_token` are stripped).

```json
{
  "incident_id": "inc_b7e1...",
  "status": "completed",
  "hypothesis": {
    "category": "db_pool_exhaustion",
    "service": "orders",
    "confidence": 0.87,
    "reasoning": "Errors began when db_pool_in_use reached max; logs show 'too many connections'.",
    "evidence_ids": ["ev_metric_db_pool_in_use", "ev_log_err_1", "ev_kb_doc_runbook_db_pool_sec_1"],
    "suggested_action": { "type": "review_config", "target": "orders", "detail": "increase pool size, check leaked connections" },
    "abstained": false,
    "groundedness": 0.95
  },
  "evidence": [ { "id": "ev_metric_db_pool_in_use", "kind": "metric", "summary": "db_pool_in_use at max", "source_ref": "mcp:metrics_server:query_metric:db_pool_in_use" } ],
  "cost_usd": 0.0041,
  "latency_ms": 6120,
  "guardrail_flags": []
}
```

### GET /v1/incidents
Lists recent incidents sorted newest-first (`incident_id`, `service`, `symptom`, `status`, `cost_usd`, `latency_ms`, `created_at`, `category`, `root_cause`, `confidence`, `langfuse_trace_url`). *(Pagination params `status`, `limit`, `cursor` are Planned / Future work.)*

### GET /v1/incidents/{id}/stream  (SSE)
Streams progress events (`text/event-stream`). Replays past stored events immediately, then streams live updates until `done` or terminal status (`completed`, `awaiting_approval`, `abstained`, `budget_exceeded`, `failed`, `remediation_executed`, `rejected_by_human`). Note: the route is `/stream` (there is no `/events` route).

Implemented event `type` values emitted in SSE JSON payloads:

| `type` | Node / Description |
|---|---|
| `incident_started` | `system` — investigation initialized with redacted alert |
| `guardrail_executed` | `input_guard` / `output_guard` — PII/injection or groundedness/leakage scan |
| `supervisor_planned` | `supervisor` — specialist plan list |
| `evidence_found` | `metrics_agent` / `logs_agent` / `runbook_agent` / `memory_agent` — extracted `evidence[]` |
| `hypothesis_synthesized` | `root_cause_agent` — structured `Hypothesis` |
| `approval_required` | `human_approval` — `approval_id`, `status`, `action` |
| `agent_finished` | generic node completion fallback |
| `done` | `system` — terminal status (`completed`, `awaiting_approval`, `abstained`, `budget_exceeded`, `failed`), cost, latency, `langfuse_trace_url` |

## 3. Approvals & Feedback

### POST /v1/incidents/{id}/approval
Request:
```json
{ "approval_id": "appr_req_a1...", "decision": "approve" }
```
Response `200` (approve): `{ "status": "approved_and_executed", "result": { ... } }`  
Response `200` (reject): `{ "status": "rejected", "message": "Remediation action rejected by engineer" }`

Rules: only valid when incident status is `awaiting_approval`. Verifies `approval_id`, consumes (or re-issues after server restart) the server-side single-use HMAC capability token bound to incident/action/target, and invokes `remediation_server` in **dry-run only** mode. (Any `decision` whose lowercase value is not `"reject"` follows the approve path.)

### Approval Value Mapping

| Layer | Approve Path | Reject Path |
|---|---|---|
| API request `decision` (`POST /approval`) | `"approve"` (sent by UI; any non-`"reject"` accepted) | `"reject"` |
| API response `status` | `"approved_and_executed"` | `"rejected"` |
| DB `approvals.decision` | `"approved"` | `"rejected"` |
| DB `incidents.status` | `"remediation_executed"` | `"rejected_by_human"` |

### POST /v1/incidents/{id}/feedback
Accepts `{ "verdict": "correct_root_cause" | "wrong_root_cause" | "good_abstention" | "false_alarm", "corrected_category"?: str, "notes"?: str, "submitted_by"?: str }`, scrubs PII before writing to `incident_feedback`, updates the in-memory record, and returns `{ "status": "recorded", "feedback": {...} }`.

## 4. Evaluation and Red Team (Implemented Read Endpoints)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/evals` | Returns committed benchmark JSON artifacts from `evals/results/*.json` keyed by filename |
| `GET` | `/v1/redteam` | Returns adversarial cases from `evals/redteam/cases.json`, total count, and `blocked_rate` |

## 5. Operations

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` / `/healthz` | Liveness check (`{"status": "ok", "service": "incidentiq_api"}`) |
| `GET` | `/readyz` | Probes DB (`SELECT 1`) and, when `MCP_MODE=http`, TCP reachability of `mcp-metrics`, `mcp-logs`, and `mcp-remediation` (`503` if degraded; does not check Redis) |

## 6. Rate limits and cost caps

- Per IP: `30` requests/minute on `GET /v1/*` read endpoints, `5` incident creations/minute on `POST /v1/incidents` (keyed on right-to-left `X-Forwarded-For` parsing for `TRUSTED_PROXY_IPS`).
- Global daily LLM spend cap (`DAILY_COST_CAP_USD`, default `2.00`): beyond it, `POST /v1/incidents` returns HTTP `429` (`BUDGET_EXCEEDED`).
- Per-incident budget & step caps (`INCIDENT_BUDGET_USD`, `MAX_AGENT_STEPS`).

## 7. Planned / Future work (Endpoints not implemented on `incidentiq-api` in v1)

- **Knowledge base admin & search:** `POST /v1/kb/ingest`, `GET /v1/kb/search`, `GET /v1/kb/documents` (currently KB is loaded into memory by `incidentiq/rag/engine.py`).
- **API-triggered eval & red-team runs / comparison:** `POST /v1/evals/runs`, `GET /v1/evals/runs`, `GET /v1/evals/runs/{id}`, `GET /v1/evals/compare`, `POST /v1/redteam/runs`, `GET /v1/redteam/runs/{id}` (currently executed via CLI `evals/run_evals.py` and `evals/redteam/run_redteam.py`).
- **Control-plane shop fault proxy & API metrics:** `GET /v1/shop/faults`, `POST /v1/shop/faults/{fault}/inject`, `POST /v1/shop/faults/reset`, and API `GET /metrics` (`shop/` containers expose chaos endpoints and `/metrics` directly on internal ports; API `/metrics` is reserved in `deploy/Caddyfile` with basic auth).
- **Cursor pagination & filtering:** `status`, `limit`, `cursor` query parameters on `GET /v1/incidents`.

# API Specification: IncidentIQ

Base URL: `/v1`. JSON over HTTP. Streaming via Server-Sent Events (SSE). Auth for the public demo: a static API key header `X-API-Key` (basic protection, plus rate limits). FastAPI generates the OpenAPI document at `/docs`.

## 1. Conventions

- IDs are UUIDs unless stated.
- Timestamps are ISO 8601 UTC.
- Errors use one shape:

```json
{ "error": { "code": "validation_error", "message": "window_end must be after window_start", "details": {} } }
```

| HTTP | code | Meaning |
|---|---|---|
| 400 | validation_error | Bad input |
| 401 | unauthorized | Missing or wrong key |
| 404 | not_found | Unknown id |
| 409 | invalid_state | e.g. approving a completed incident |
| 422 | guardrail_blocked | Input rejected by guard |
| 429 | rate_limited | Too many requests or daily cost cap hit |
| 500 | internal_error | Unexpected |

## 2. Incidents

### POST /v1/incidents
Create and start an investigation.

Request:
```json
{
  "service": "orders",
  "symptom": "p95 latency 4s, error rate 12%",
  "window_start": "2026-11-20T14:00:00Z",
  "window_end": "2026-11-20T14:30:00Z",
  "source": "live",
  "scenario_id": null
}
```
`source` is `live` or `replay`; `scenario_id` is required for `replay`.

Response `202`:
```json
{ "incident_id": "b7e1...", "status": "queued", "stream_url": "/v1/incidents/b7e1.../events" }
```

### GET /v1/incidents/{id}
Returns incident, status, hypothesis, evidence list, cost and latency.

```json
{
  "id": "b7e1...",
  "status": "completed",
  "hypothesis": {
    "category": "db_pool_exhaustion",
    "service": "orders",
    "confidence": 0.87,
    "reasoning": "Errors began when db_pool_in_use reached max; logs show 'too many connections'.",
    "evidence_ids": ["ev_metric_001", "ev_log_004", "ev_rb_002"],
    "suggested_action": { "type": "review_config", "target": "orders", "detail": "increase pool size, check leaked connections" },
    "abstained": false,
    "groundedness": 0.95
  },
  "evidence": [ { "id": "ev_metric_001", "kind": "metric", "summary": "db_pool_in_use at max from 14:02", "source_ref": "tc_17" } ],
  "cost_usd": 0.0041,
  "latency_ms": 6120,
  "guardrail_events": []
}
```

### GET /v1/incidents
Query params: `status`, `limit` (default 20), `cursor`. Returns a page of incident summaries.

### GET /v1/incidents/{id}/events  (SSE)
Streams progress events. Content type `text/event-stream`.

Event types:
| event | data |
|---|---|
| `status` | `{ "status": "running" }` |
| `agent_started` | `{ "agent": "logs", "at": "..." }` |
| `tool_call` | `{ "agent": "logs", "server": "logs", "tool": "get_error_clusters", "args": {...} }` |
| `evidence` | `{ "id": "ev_log_004", "kind": "log", "summary": "..." }` |
| `agent_finished` | `{ "agent": "logs", "latency_ms": 1800, "cost_usd": 0.0004 }` |
| `guardrail` | `{ "type": "injection", "action": "quarantined", "stage": "tool_output" }` |
| `hypothesis` | full hypothesis object |
| `approval_required` | `{ "approval_id": "...", "action": {...} }` |
| `done` | `{ "status": "completed", "cost_usd": 0.0041, "latency_ms": 6120 }` |

## 3. Approvals

### POST /v1/incidents/{id}/approval
Request:
```json
{ "approval_id": "a1...", "decision": "approved", "decided_by": "mayank" }
```
Response `200`: `{ "status": "completed", "executed": "dry_run", "result": { ... } }`

Rules: only valid when status is `awaiting_approval`; decision resumes the LangGraph run from its checkpoint. Execution is always dry-run in v1.

## 4. Knowledge base

| Method | Path | Purpose |
|---|---|---|
| POST | /v1/kb/ingest | Re-ingest `knowledge/` (admin) |
| GET | /v1/kb/search?q=...&k=5 | Debug retrieval, returns chunks with scores |
| GET | /v1/kb/documents | List indexed docs |

## 5. Evaluation and red team

| Method | Path | Purpose |
|---|---|---|
| POST | /v1/evals/runs | Start a benchmark run `{ "name": "v2-optimized", "repeats": 3, "scenario_ids": null }` |
| GET | /v1/evals/runs | List runs with summary |
| GET | /v1/evals/runs/{id} | Per-scenario results |
| GET | /v1/evals/compare?a={id}&b={id} | Metric deltas between two runs |
| POST | /v1/redteam/runs | Run all attack cases |
| GET | /v1/redteam/runs/{id} | Outcomes and block rate |

Eval summary shape:
```json
{
  "accuracy": 0.83, "evidence_recall": 0.78, "groundedness": 0.92,
  "abstention_quality": 0.75, "tool_use_correctness": 0.95,
  "cost_per_incident_usd": 0.0041, "latency_p50_ms": 4300, "latency_p95_ms": 7800
}
```

## 6. Demo shop control (demo only)

| Method | Path | Purpose |
|---|---|---|
| GET | /v1/shop/faults | List available faults |
| POST | /v1/shop/faults/{fault}/inject | Inject a fault `{ "variant": 2 }` |
| POST | /v1/shop/faults/reset | Return shop to healthy state |

## 7. Operations

| Method | Path | Purpose |
|---|---|---|
| GET | /healthz | Liveness |
| GET | /readyz | Checks DB, Redis, MCP servers |
| GET | /metrics | Prometheus metrics for IncidentIQ |

## 8. Rate limits and cost caps

- Per IP: 30 requests/minute on read endpoints, 5 incident creations/minute.
- Global daily LLM spend cap (env `DAILY_COST_CAP_USD`); beyond it, `POST /v1/incidents` returns 429 `rate_limited` with a clear message.
- Per-incident budget (env `INCIDENT_BUDGET_USD`, `MAX_AGENT_STEPS`).

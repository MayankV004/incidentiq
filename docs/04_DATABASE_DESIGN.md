# Database Design: IncidentIQ

## Deployed Demo Implementation (Single-Worker SQLite)
- **Active Storage Engine:** Single-worker Uvicorn (`WORKERS=1`) backed by SQLite (`sqlite:///incidentiq.db` locally, `sqlite:////data/incidentiq.db` in Docker Compose via persistent volume `iiq_data`). PostgreSQL (`postgresql+psycopg://`), `pgvector`, and Redis are deferred out of the public cost-capped demo.
- **Additive Alembic Migrations:** `0001_incidents` creates `incidents`, `451ef2dd7538` creates `approvals`, `guardrail_events`, `llm_calls`, `tool_calls`, `eval_runs`, and `eval_results`, and `a7c4e1b9d203` creates `incident_feedback`. `alembic upgrade head` is idempotent on both clean and pre-initialized SQLite databases.
- **Runtime Telemetry & Episodic Memory:** Replay and live workflows populate `incidents`, `approvals`, `llm_calls`, `tool_calls` (with capability tokens redacted), `guardrail_events`, and `incident_feedback`. `memory_agent` recalls verified past incidents backed by `incident_feedback` or `approvals` decisions (`ENABLE_AGENT_MEMORY=true`), while daily spend caps query persisted `IncidentRecord.cost_usd` directly so limits survive restarts.
- **Backups:** Hot online SQLite backups and restores are supported via `scripts/backup_sqlite.sh` (using Python `sqlite3.Connection.backup`).

---

IncidentIQ also keeps PostgreSQL 16 compatibility (`postgresql+psycopg://`) in SQLAlchemy models and migrations for optional multi-node expansion.

## 1. Implemented Database Architecture & ER Diagram

The database manages both the core incident lifecycle and detailed telemetry/eval records:

```mermaid
erDiagram
  incidents ||--o{ approvals : requires
  incidents ||--o{ guardrail_events : triggers
  incidents ||--o{ llm_calls : tracks
  incidents ||--o{ tool_calls : audits
  incidents ||--o{ incident_feedback : verified_by
  eval_runs ||--o{ eval_results : aggregates
```

### Table Inventory (Implemented in Code & Alembic Migrations)

| Table Name | Target Dialects | Primary Key | Purpose |
|---|---|---|---|
| `incidents` | SQLite & Postgres | `id` (VARCHAR 64) | Core incident lifecycle, alert metadata, status, JSON evidence, hypotheses, and execution timeline |
| `approvals` | SQLite & Postgres | `id` (VARCHAR 36 UUID) | Cryptographic capability token nonces, approval request IDs, action proposals, and human decisions |
| `guardrail_events` | SQLite & Postgres | `id` (VARCHAR 36 UUID) | Audit trail of PII redactions, prompt injection interceptions, and groundedness drop flags |
| `llm_calls` | SQLite & Postgres | `id` (VARCHAR 36 UUID) | Granular model call telemetry: model name, purpose, token usage, cost, and latency |
| `tool_calls` | SQLite & Postgres | `id` (VARCHAR 36 UUID) | MCP tool audit log: server name, tool name, arguments, output, allowlist verification status |
| `incident_feedback` | SQLite & Postgres | `id` (VARCHAR 36 UUID) | Human verification verdicts (`correct_root_cause`, `wrong_root_cause`, `good_abstention`, `false_alarm`) powering episodic memory and live evals |
| `eval_runs` | SQLite & Postgres | `id` (VARCHAR 36 UUID) | IncidentBench evaluation run summary metrics (accuracy, cost, latency, split, repeats) |
| `eval_results` | SQLite & Postgres | `id` (VARCHAR 36 UUID) | Per-scenario evaluation scores and hypothesis outcomes within an evaluation run |


## 2. Implemented Schema (SQLAlchemy Models & Alembic Migrations)

Defined in `incidentiq/db/models.py` and created across three Alembic revisions (`0001_incidents`, `451ef2dd7538`, `a7c4e1b9d203`). Evidence, hypothesis, guardrail flags, approval summary, and SSE event timeline are stored as `JSON` columns on `incidents` alongside normalized telemetry tables:

- **`incidents`**: `id` (VARCHAR 64 PK), `scenario_id`, `service`, `symptom`, `window_start`, `window_end`, `status` (VARCHAR 32: `queued`, `running`, `awaiting_approval`, `completed`, `abstained`, `budget_exceeded`, `failed`, `remediation_executed`, `rejected_by_human`), `cost_usd` (Float), `latency_ms` (Float), `steps` (Integer), `hypothesis` (JSON), `evidence` (JSON), `guardrail_flags` (JSON), `approval` (JSON), `events` (JSON), `langfuse_trace_url`, `error`, `created_at` (Float epoch), `completed_at` (Float epoch).
- **`approvals`**: `id` (VARCHAR 36 UUID PK), `approval_id`, `incident_id` (FK -> `incidents.id`), `action` (JSON), `decision` (`approved`, `rejected`, `expired`), `decided_by`, `token_hash`, `requested_at`, `decided_at`.
- **`llm_calls`**: `id` (UUID PK), `agent_run_id`, `incident_id` (FK -> `incidents.id`), `model`, `purpose`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `cache_hit`, `error`, `created_at`.
- **`tool_calls`**: `id` (UUID PK), `agent_run_id`, `incident_id` (FK -> `incidents.id`), `server`, `tool_name`, `arguments` (JSON), `result` (JSON), `allowed` (Boolean), `error`, `latency_ms`, `created_at`.
- **`guardrail_events`**: `id` (UUID PK), `incident_id` (FK -> `incidents.id`), `phase`, `flag_type`, `detail`, `raw_input`, `sanitized_output`, `created_at`.
- **`eval_runs`**: `id` (UUID PK), `run_name`, `split`, `repeats`, `total_scenarios`, `total_runs`, `accuracy_pct`, `groundedness_pct`, `abstention_correct_pct`, `action_safety_pct`, `mean_cost_usd`, `latency_p50_ms`, `latency_p95_ms`, `code_path`, `notes`, `created_at`.
- **`eval_results`**: `id` (UUID PK), `eval_run_id` (FK -> `eval_runs.id`), `scenario_id`, `repeat_index`, `accuracy`, `groundedness`, `abstention_correct`, `cost_usd`, `latency_ms`, `steps`, `hypothesis` (JSON), `error`, `created_at`.
- **`incident_feedback`**: `id` (UUID PK), `incident_id` (FK -> `incidents.id`), `verdict` (`correct_root_cause`, `wrong_root_cause`, `good_abstention`, `false_alarm`), `corrected_category`, `notes`, `submitted_by`, `created_at`.

### Approval & Status Terminology Mapping

| Stage | Approve Path | Reject Path | Timeout / Unapproved |
|---|---|---|---|
| API request (`POST /v1/incidents/{id}/approval` `decision`) | `"approve"` (note: any string != `"reject"` enters approve path) | `"reject"` | — |
| HTTP response `status` | `"approved_and_executed"` | `"rejected"` | — |
| DB `approvals.decision` | `"approved"` | `"rejected"` | `"expired"` (schema value; 15m token TTL) |
| DB `incidents.status` | `"remediation_executed"` | `"rejected_by_human"` | `"awaiting_approval"` |

## 3. Data & Operational Notes

- `DATABASE_URL` defaults to `sqlite:///incidentiq.db` (`incidentiq/db/session.py`); URLs prefixed with `postgresql+asyncpg://` or `postgresql://` are translated to synchronous `postgresql+psycopg://`.
- Scenario raw data (metrics, logs) stays in files under `scenarios/`, not in the DB.
- Alerts are sanitized by `GuardrailManager.process_input_alert` before persistence on `incidents`.
- Demo incidents can be rotated or truncated via SQLite maintenance; `evals/results/*.json` preserves committed benchmark history.

## 4. Planned / Future work

- Normalizing `agent_runs`, `evidence`, `hypotheses`, `scenarios`, `redteam_cases`/`redteam_runs`/`redteam_results`, and `audit_log` into PostgreSQL tables.
- Storing markdown KB chunks and embeddings (`kb_documents`, `kb_chunks` with `pgvector` HNSW + `tsvector` GIN) in Postgres.

---

## Appendix: Target schema (not implemented)

The original PostgreSQL 16 + `pgvector` design DDL and hybrid retrieval query are preserved below as the target multi-node expansion schema. None of `pgvector`, `kb_documents`, `kb_chunks`, `agent_runs`, `evidence`, `hypotheses`, `scenarios`, `redteam_*`, or `audit_log` exist in the current migrations.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ===== Core incident data =====
CREATE TABLE incidents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source        TEXT NOT NULL CHECK (source IN ('live','replay','eval')),
  scenario_id   TEXT,                       -- set in replay/eval
  service       TEXT NOT NULL,
  symptom       TEXT NOT NULL,
  window_start  TIMESTAMPTZ NOT NULL,
  window_end    TIMESTAMPTZ NOT NULL,
  raw_alert     JSONB NOT NULL,             -- after PII redaction
  status        TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','awaiting_approval','completed','abstained','failed','budget_exceeded')),
  cost_usd      NUMERIC(10,6) DEFAULT 0,
  latency_ms    INTEGER,
  code_version  TEXT,                       -- git sha
  created_at    TIMESTAMPTZ DEFAULT now(),
  completed_at  TIMESTAMPTZ
);
CREATE INDEX idx_incidents_status ON incidents(status, created_at DESC);
CREATE INDEX idx_incidents_scenario ON incidents(scenario_id);

CREATE TABLE agent_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id   UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  agent_name    TEXT NOT NULL,              -- supervisor, metrics, logs, runbook, root_cause, guard
  status        TEXT NOT NULL,              -- running, ok, error, skipped
  started_at    TIMESTAMPTZ DEFAULT now(),
  finished_at   TIMESTAMPTZ,
  output        JSONB,                      -- structured agent output
  langfuse_trace_id TEXT
);
CREATE INDEX idx_agent_runs_incident ON agent_runs(incident_id);

CREATE TABLE evidence (
  id            TEXT PRIMARY KEY,           -- e.g. 'ev_metric_003', stable citation id
  incident_id   UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL CHECK (kind IN ('metric','log','runbook','postmortem')),
  source_ref    TEXT NOT NULL,              -- tool call id, log line range, or kb chunk id
  summary       TEXT NOT NULL,
  data          JSONB,                      -- compact raw evidence (capped)
  created_by    TEXT NOT NULL,              -- agent name
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_evidence_incident ON evidence(incident_id);

CREATE TABLE hypotheses (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id   UUID UNIQUE NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  category      TEXT,                       -- e.g. db_pool_exhaustion; NULL if abstained
  service       TEXT,
  confidence    REAL CHECK (confidence BETWEEN 0 AND 1),
  reasoning     TEXT,
  evidence_ids  TEXT[] NOT NULL DEFAULT '{}',
  suggested_action JSONB,
  abstained     BOOLEAN NOT NULL DEFAULT FALSE,
  abstain_reason TEXT,
  groundedness  REAL,                       -- guard score
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE approvals (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id   UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  action        JSONB NOT NULL,             -- proposed remediation (dry-run)
  decision      TEXT CHECK (decision IN ('approved','rejected','expired')),
  decided_by    TEXT,
  token_hash    TEXT,                       -- hash of approval token issued to remediation MCP
  requested_at  TIMESTAMPTZ DEFAULT now(),
  decided_at    TIMESTAMPTZ
);

-- ===== LLM and tool telemetry =====
CREATE TABLE llm_calls (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id  UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
  incident_id   UUID REFERENCES incidents(id) ON DELETE CASCADE,
  model         TEXT NOT NULL,
  purpose       TEXT,                       -- route, summarize, reason, judge
  prompt_tokens INTEGER, completion_tokens INTEGER,
  cost_usd      NUMERIC(10,6),
  latency_ms    INTEGER,
  cache_hit     BOOLEAN DEFAULT FALSE,
  error         TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_llm_calls_incident ON llm_calls(incident_id);

CREATE TABLE tool_calls (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id  UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
  incident_id   UUID REFERENCES incidents(id) ON DELETE CASCADE,
  server        TEXT NOT NULL,              -- metrics, logs, remediation
  tool          TEXT NOT NULL,
  arguments     JSONB,
  result_size   INTEGER,
  allowed       BOOLEAN NOT NULL,           -- allow-list decision
  error         TEXT,
  latency_ms    INTEGER,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE guardrail_events (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id   UUID REFERENCES incidents(id) ON DELETE CASCADE,
  stage         TEXT NOT NULL,              -- input, tool_output, output
  type          TEXT NOT NULL,              -- pii, injection, ungrounded, budget, forbidden_tool
  action        TEXT NOT NULL,              -- redacted, quarantined, removed, blocked, abstained
  detail        JSONB,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- ===== Knowledge base / RAG =====
CREATE TABLE kb_documents (
  id            TEXT PRIMARY KEY,           -- e.g. 'runbook_db_pool'
  doc_type      TEXT NOT NULL CHECK (doc_type IN ('runbook','postmortem')),
  title         TEXT NOT NULL,
  path          TEXT NOT NULL,
  tags          TEXT[] DEFAULT '{}',
  content_hash  TEXT NOT NULL,              -- re-ingest only on change
  updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE kb_chunks (
  id            TEXT PRIMARY KEY,           -- e.g. 'runbook_db_pool#3'
  document_id   TEXT NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
  section_title TEXT,
  content       TEXT NOT NULL,
  token_count   INTEGER,
  embedding     vector(384),                -- bge-small = 384 dims; use 768 for bge-base
  tsv           tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);
CREATE INDEX idx_chunks_vec ON kb_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_tsv ON kb_chunks USING gin (tsv);

-- ===== Evaluation =====
CREATE TABLE scenarios (
  id            TEXT PRIMARY KEY,           -- '003_db_pool_exhaustion'
  fault_type    TEXT NOT NULL,
  difficulty    TEXT CHECK (difficulty IN ('easy','medium','hard','ambiguous')),
  label         JSONB NOT NULL,             -- ground truth (see label.json)
  path          TEXT NOT NULL
);

CREATE TABLE eval_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,              -- 'v1-baseline', 'v2-optimized'
  code_version  TEXT NOT NULL,
  config        JSONB NOT NULL,             -- models, thresholds, router settings
  repeats       INTEGER DEFAULT 3,
  started_at    TIMESTAMPTZ DEFAULT now(),
  finished_at   TIMESTAMPTZ,
  summary       JSONB                       -- aggregate metrics
);

CREATE TABLE eval_results (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  eval_run_id   UUID NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
  scenario_id   TEXT NOT NULL REFERENCES scenarios(id),
  repeat_idx    INTEGER NOT NULL,
  incident_id   UUID REFERENCES incidents(id),
  correct       BOOLEAN,
  evidence_recall REAL,
  groundedness  REAL,
  tool_use_ok   BOOLEAN,
  abstain_ok    BOOLEAN,
  cost_usd      NUMERIC(10,6),
  latency_ms    INTEGER,
  notes         TEXT
);
CREATE INDEX idx_eval_results_run ON eval_results(eval_run_id);

-- ===== Red team =====
CREATE TABLE redteam_cases (
  id            TEXT PRIMARY KEY,           -- 'rt_007'
  category      TEXT NOT NULL,              -- poisoned_log, poisoned_runbook, prompt_leak, forbidden_tool, indirect
  payload       JSONB NOT NULL,
  expected      TEXT NOT NULL               -- 'blocked'
);

CREATE TABLE redteam_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  code_version  TEXT NOT NULL,
  started_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE redteam_results (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  redteam_run_id UUID NOT NULL REFERENCES redteam_runs(id) ON DELETE CASCADE,
  case_id       TEXT NOT NULL REFERENCES redteam_cases(id),
  outcome       TEXT NOT NULL CHECK (outcome IN ('blocked','partial','succeeded')),
  evidence      TEXT
);

-- ===== Audit =====
CREATE TABLE audit_log (
  id            BIGSERIAL PRIMARY KEY,
  actor         TEXT NOT NULL,              -- agent or user
  event         TEXT NOT NULL,
  detail        JSONB,
  created_at    TIMESTAMPTZ DEFAULT now()
);
```

-- Note: the implemented SQLite/Postgres schema uses string UUID/IDs and adds `incident_feedback` + `remediation_executed`/`rejected_by_human` statuses (see Section 2).

### Target hybrid retrieval query (not implemented in v1 BM25 demo)

```sql
-- vector candidates
SELECT id, 1 - (embedding <=> :qvec) AS score
FROM kb_chunks ORDER BY embedding <=> :qvec LIMIT 20;

-- keyword candidates
SELECT id, ts_rank(tsv, websearch_to_tsquery('english', :q)) AS score
FROM kb_chunks WHERE tsv @@ websearch_to_tsquery('english', :q)
ORDER BY score DESC LIMIT 20;
```

Merge both lists with reciprocal rank fusion in Python, rerank the top 20 with the cross-encoder, return the top 5 (embedding dimension must match model: 384 for `bge-small`, 768 for `bge-base`).

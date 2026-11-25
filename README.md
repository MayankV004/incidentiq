# IncidentIQ

IncidentIQ is an AI on-call triage assistant for small engineering and SRE teams.
When a service alert fires, it checks metrics, logs, and runbooks in parallel.
It then writes a short root-cause report with evidence IDs, or abstains if telemetry looks healthy.
You approve or reject any fix through a web dashboard, and all actions run in dry-run mode only.

---

## 1. What It Is

When production breaks, engineers waste time opening dashboards, searching logs, and hunting for runbooks.
IncidentIQ automates that first investigation step.

What makes it different from a plain chatbot:
* **Cited answers only:** A guardrail removes claims without an evidence ID (`ev_metric_*`, `ev_log_*`, or `ev_kb_*`).
* **Honest abstention:** If telemetry looks normal or evidence is weak, the assistant stops and says so.
* **No silent production changes:** Remediation tools require a signed approval token and only return dry-run receipts.
* **Works offline too:** If you do not configure an LLM API key, a rule-based fallback handles demo scenarios.

---

## 2. How It Works

```mermaid
flowchart TD
  Alert([Alert POST /v1/incidents]) --> InputGuard[1. Input Guardrail: PII and Injection Scan]
  InputGuard --> Supervisor[2. Supervisor: Pick Investigation Steps]

  Supervisor --> MetricsAgent[3a. Metrics Agent -> Metrics MCP]
  Supervisor --> LogsAgent[3b. Logs Agent -> Logs MCP]
  Supervisor --> RunbookAgent[3c. Runbook Agent -> BM25 Knowledge Search]

  MetricsAgent --> RootCause[4. Root-Cause Agent: LLM or Rule Fallback]
  LogsAgent --> RootCause
  RunbookAgent --> RootCause

  RootCause --> OutputGuard[5. Output Guardrail: Check Citations and Confidence]
  OutputGuard -->|Healthy or Weak Evidence| Abstain[6a. Honest Abstention]
  OutputGuard -->|Suggested Action| Approval[6b. Human Approval Gate in UI]
  Approval -->|Approve| DryRun[7. Remediation MCP: Dry-Run Receipt Only]
  Approval -->|Reject| Rejected[7b. Mark Rejected in SQLite]

  RootCause --> SQLite[(SQLite Database)]
  RootCause -.->|Optional| Langfuse[(Langfuse Cloud)]
```

### Step-by-Step Flow

1. **Receive an alert:** Your team (or the UI) sends a service alert to `POST /v1/incidents`.
2. **Scan the input:** The input guardrail masks emails, phones, SSNs, card numbers, and API keys. It also flags common prompt-injection phrases.
3. **Plan the checks:** A fixed rule planner (`supervisor_node`) dispatches three specialist agents. It makes zero LLM calls.
4. **Gather evidence in parallel:**
   * The **Metrics Agent** queries `mcp_servers/metrics` (`PROMETHEUS_URL` in live mode, or `scenarios/` files in replay mode) and checks Z-score spikes.
   * The **Logs Agent** queries `mcp_servers/logs` for grouped error patterns and wraps log lines in `<untrusted_data>` tags.
   * The **Runbook Agent** searches markdown files in `knowledge/` using in-memory keyword scoring (**BM25** and Jaccard overlap).
5. **Synthesize a report:** The Root-Cause Agent sends gathered evidence to your configured LLM via LiteLLM. If no LLM key is set, a built-in rule engine runs instead.
6. **Verify claims:** The output guardrail drops unknown citations. It forces **abstention** if confidence falls below `ABSTAIN_THRESHOLD` (`0.50`) or groundedness falls below `GROUND_THRESHOLD` (`0.85`).
7. **Wait for human approval:** When the agent suggests an action (`review_config`, `restart_service`, `rollback_deploy`, or `scale_up`), it pauses. You then approve or reject it in the UI.
8. **Run dry-run receipt:** When you click Approve, the server checks a single-use **HMAC** capability token and returns a dry-run receipt. No real infrastructure changes.

### UI Screenshots

**Live Triage & Multi-Agent Timeline**
![IncidentIQ Live Triage Timeline](docs/screenshots/live-triage-timeline.png)

**Grounded Diagnosis & Dry-Run Approval Gate**
![IncidentIQ Grounded Report and Dry-Run Approval](docs/screenshots/live-triage-approval.png)

**Calibrated Honest Abstention**
![IncidentIQ Calibrated Honest Abstention](docs/screenshots/honest-abstention.png)

**Incidents History**
![IncidentIQ Incidents History](docs/screenshots/incidents-history.png)

**Evaluation Suite**
![IncidentIQ Evaluation Suite](docs/screenshots/evaluation-suite.png)

**Security Matrix**
![IncidentIQ Security Matrix](docs/screenshots/security-matrix.png)

---

## 3. Quick Start (Local Demo)

### Prerequisites

* Python 3.12+ and `uv`
* Node.js 22+ and `pnpm`

### Verified Setup Steps

1. **Clone the repo and install dependencies:**
   ```bash
   git clone https://github.com/MayankV004/incidentiq.git
   cd incidentiq
   uv sync --frozen
   cd ui && CI=true pnpm install --frozen-lockfile && cd ..
   ```

2. **Create `.env` for local SQLite replay mode:**
   The default `.env.example` template lists a Postgres URL and `DATA_MODE=live`. For a local quick start without Postgres or Prometheus, switch `.env` to SQLite and `replay` mode, and set two non-empty secrets:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to set at least these values:
   ```ini
   DATABASE_URL=sqlite:///incidentiq.db
   DATA_MODE=replay
   API_KEY=replace-with-random-api-key
   APPROVAL_TOKEN_SECRET=replace-with-random-hmac-secret
   ```
   *(Leave LLM keys empty to run the offline deterministic fallback. To test with a live LLM such as Groq, also set `LLM_API_KEY_PRIMARY` or `GROQ_API_KEY` and `MODEL_STRONG`.)*

3. **Run database migrations and start the FastAPI backend (Terminal 1):**
   `alembic` reads `DATABASE_URL` from shell environment variables, so export `.env` first:
   ```bash
   set -a && source .env && set +a
   uv run alembic upgrade head
   uv run uvicorn incidentiq.api.main:app --port 8000 --workers 1
   ```
   Wait until `http://127.0.0.1:8000/healthz` returns `200`.

4. **Start the Next.js UI (Terminal 2):**
   ```bash
   set -a && source .env && set +a
   cd ui && API_INTERNAL_URL=http://127.0.0.1:8000 pnpm dev
   ```
   Open `http://localhost:3000` in your browser.
   The UI sends browser requests to same-origin `/api/v1/*`, and the Next.js server attaches `X-API-Key` from `API_KEY`.

5. **Run the verification suites (optional, offline):**
   ```bash
   set -a && source .env && set +a
   uv run pytest
   PYTHONPATH=. uv run python evals/redteam/run_redteam.py
   PYTHONPATH=. uv run python evals/run_evals.py --name v2-local-check
   ```

### Important Environment Variables

| Variable | Default in Code | Required | Purpose |
|---|---|---|---|
| `API_KEY` | none (fails fast) | Yes | Shared secret checked in `X-API-Key` for `/v1/*` API calls |
| `APPROVAL_TOKEN_SECRET` | none (fails fast) | Yes | HMAC-SHA256 signing key for 15-minute approval tokens |
| `DATABASE_URL` | `sqlite:///incidentiq.db` | No | SQLite path (`.env.example` sets Postgres URL; use SQLite locally) |
| `DATA_MODE` | `replay` (in MCP/API; `live` in `.env.example`) | No | `replay` reads `scenarios/`; `live` queries `PROMETHEUS_URL` and `logs/` |
| `PROMETHEUS_URL` | `http://localhost:9090` | No | Prometheus base URL when `DATA_MODE=live` |
| `MCP_MODE` | in-process (`""`) | No | Set to `http` in Compose to call MCP containers on ports `9101–9103` |
| `DAILY_COST_CAP_USD` | `2.00` | No | Daily USD limit summed from SQLite across restarts |
| `INCIDENT_BUDGET_USD` | `0.05` | No | Per-incident USD cost limit |
| `MAX_AGENT_STEPS` | `12` | No | Max LangGraph steps per incident |
| `ABSTAIN_THRESHOLD` | `0.50` | No | Confidence cutoff below which the agent abstains |
| `GROUND_THRESHOLD` | `0.85` | No | Minimum ratio of valid evidence IDs required |
| `WORKERS` | `1` | No | Must stay `1`; API exits if > `1` |
| `API_INTERNAL_URL` | `http://incidentiq-api:8000` | UI server | Upstream FastAPI URL used by `ui/app/api/v1/[...path]/route.ts` |
| `NEXT_PUBLIC_API_URL` | `""` (empty) | UI build | Keep empty so browser requests stay same-origin |

---

## 4. Results

Every figure below comes from committed result files in `evals/results/`.
Replay scenarios are 8 synthetic outage files in `scenarios/`, not real production outages.

| Metric | Value | Status | Source |
|---|---|---|---|
| Root-cause accuracy (`v2-live`, Groq `openai/gpt-oss-120b`, 24 runs) | 100.0% (±0.0%) | measured (replay telemetry) | [evals/results/v2-live.json](evals/results/v2-live.json) |
| Claim groundedness (`v2-live`, 24 runs) | 100.0% | measured (replay telemetry) | [evals/results/v2-live.json](evals/results/v2-live.json) |
| Abstention precision (`v2-live`, 24 runs) | 100.0% | measured (replay telemetry) | [evals/results/v2-live.json](evals/results/v2-live.json) |
| Action safety (`v2-live`, 24 runs) | 100.0% | measured | [evals/results/v2-live.json](evals/results/v2-live.json) |
| Latency p50 / p95 (`v2-live`, 24 runs) | 1468.7ms / 3058.1ms | measured | [evals/results/v2-live.json](evals/results/v2-live.json) |
| Mean cost per incident (`v2-live`, 24 runs) | `$0.0033` (±`$0.0007`) | measured | [evals/results/v2-live.json](evals/results/v2-live.json) |
| Root-cause accuracy (`v2-optimized`, offline fallback, 8 runs) | 87.5% | simulated | [evals/results/v2-optimized.json](evals/results/v2-optimized.json) |
| Abstention precision (`v2-optimized`, 8 runs) | 87.5% | simulated | [evals/results/v2-optimized.json](evals/results/v2-optimized.json) |
| Latency p50 / p95 (`v2-optimized`, 8 runs) | 7.9ms / 12.4ms | simulated | [evals/results/v2-optimized.json](evals/results/v2-optimized.json) |
| Mean cost per incident (`v2-optimized`, 8 runs) | `$0.0045` | simulated | [evals/results/v2-optimized.json](evals/results/v2-optimized.json) |
| Adversarial red-team block rate (20 vectors) | 100.0% (20/20) | measured (offline test cases) | [evals/results/redteam_summary.json](evals/results/redteam_summary.json) |
| Runbook retrieval Hit@3 / MRR (20 queries) | 100.0% (20/20) / 0.9750 | measured (offline queries) | [evals/results/retrieval_summary.json](evals/results/retrieval_summary.json) |
| Live production triage accuracy on real outages | not measured yet | not measured yet | — |
| Live remediation execution latency | not measured yet | not measured yet | — |

See [`evals/README.md`](evals/README.md) for the per-scenario breakdown and formulas.

---

## 5. Safety and Limits

Read these limits before deploying or sharing access to IncidentIQ:

* **Remediation is dry-run only:** Tools in `mcp_servers/remediation/server.py` return `[DRY RUN]` JSON receipts and make zero changes to containers or configs.
* **No user accounts:** Only `API_KEY`, per-IP rate limits (`5` creates/min, `30` reads/min), and cost caps (`DAILY_COST_CAP_USD`, `INCIDENT_BUDGET_USD`) control access. Approver names are not authenticated (`decided_by` defaults to `"on_call_engineer"` in SQLite).
* **Single-worker SQLite demo:** Both local dev and `deploy/docker-compose.yml` run one Uvicorn worker (`WORKERS=1`) with SQLite (`sqlite:///incidentiq.db` locally, `/data/incidentiq.db` in Compose), fronted by Caddy in Compose. Postgres drivers are installed in `pyproject.toml`, and Redis is not used at runtime.
* **Simulated demo services and faults:** The `shop/` microservices are a small test app. Their order store and cache use in-memory Python dicts, not real Postgres or Redis servers.
* **Keyword retrieval only:** `incidentiq/rag/engine.py` uses Okapi BM25 plus Jaccard token overlap and a fixed service title boost (`+2.5`). It uses no embeddings or vector database.
* **Small benchmark:** `IncidentBench-mini` has only 8 curated scenarios (`6` dev, `2` held-out) across one demo app.
* **Guardrails are not guarantees:** Input and output checks rely on regex patterns, `<untrusted_data>` delimiters, tool allowlists, and single-use HMAC tokens. They reduce prompt-injection risk, but cannot guarantee safety against all attacks.

---

## 6. Project Layout

```text
incidentiq/
├── incidentiq/         # FastAPI API, LangGraph agents, SQLite models, guardrails, BM25 RAG
├── mcp_servers/        # Metrics, logs, and dry-run remediation FastMCP servers -> mcp_servers/README.md
├── ui/                 # Next.js 16 dashboard and /api/v1 BFF auth proxy -> ui/README.md
├── knowledge/          # Markdown runbooks and postmortems -> knowledge/README.md
├── scenarios/          # 8 replay outage datasets (alert, label, metrics, logs)
├── shop/               # Simulated 4-service e-commerce demo target -> shop/README.md
├── evals/              # Benchmark runner, retrieval eval, red-team suite -> evals/README.md
├── deploy/             # Dockerfiles, Caddyfile, and Docker Compose config
├── migrations/         # Alembic SQLite/SQLAlchemy schema migrations
├── docs/               # Design specifications and UI screenshots -> docs/00_README.md
└── tests/              # Pytest unit and HTTP MCP contract tests
```

---

## 7. Future Work

* **Real remediation execution:** Wiring `mcp_servers/remediation` to Docker, Kubernetes, or GitOps PR tools is future work. It needs its own security review for credentials, RBAC, and blast-radius limits.
* **Larger benchmark:** Expanding `scenarios/` beyond 8 scenarios.
* **Multi-worker scaling:** Moving state, rate limits, and approval nonces out of process memory into Postgres and Redis.
* **Real log sink adapter:** Connecting `mcp_servers/logs` to Loki, Elasticsearch, or Cloud Logging.

---

## 8. License

Distributed under the MIT License. See [LICENSE](LICENSE).

---

## 9. Glossary

* **MCP (Model Context Protocol):** A standard JSON/HTTP interface for agents to call tools safely.
* **RAG (Retrieval-Augmented Generation):** Searching local documents first so the AI reads real runbooks before answering.
* **BM25:** A classic keyword search formula that scores documents by rare matching words.
* **SSE (Server-Sent Events):** A one-way HTTP stream that pushes live agent steps to the browser.
* **Guardrail:** Code checks that scrub PII, flag prompt injections, and block unverified outputs.
* **Groundedness:** Checking that every claim in an AI report points to real gathered evidence IDs.
* **Abstain:** Refusing to guess a root cause when telemetry is normal or too weak.
* **Capability token:** A short-lived, single-use signed key tied to one incident, action, and target service.

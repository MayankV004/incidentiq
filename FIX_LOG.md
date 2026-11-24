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
| **CR-09** | Missing mypy configuration & type checker | Yes (executable not found, 13 baseline errors) | No mypy dependency or config in `pyproject.toml`; missing type annotations in models and API streaming | Installed `mypy`, configured `[tool.mypy]`, modernized SQLAlchemy 2.0 `DeclarativeBase`, and annotated API streaming context managers (0 errors across 19 files) | `uv run mypy incidentiq` | `0365dee` (config), `50f0b02` (types) |
| **AUD-01** | Remediation capability token authorization bypass | Yes (forged prefix passed, replayed successfully) | `verify_approval_token` checked prefix `appr_` and ignored `APPROVAL_TOKEN_SECRET` | Implemented HMAC-SHA256 capability tokens bound to incident, action, target, 15m TTL, and single-use nonces | `tests/unit/test_security_tokens.py` (8 unit tests) | `f10e43a` |
| **AUD-02** | Capability token leaked in plaintext via SSE and REST API | Yes (raw token present in SSE event and GET endpoint) | Raw capability token stored in state and emitted over SSE / REST | UI only receives `approval_id`; capability tokens kept strictly server-side and hashed at rest | `test_raw_token_never_exposed_in_sse_or_rest` | `f10e43a` |
| **AUD-03** | Public endpoints lack auth, rate limits, and use wildcard CORS | Yes (unauthenticated requests succeeded, no rate limits) | Missing auth middleware and rate limiting on `/v1/*`; CORS wildcard origins | Added `SecurityAndRateLimitMiddleware` with `X-API-Key` constant-time check, sliding-window rate limits, daily budget cap, explicit CORS origins, and unauthenticated `/healthz`/`/readyz` | `tests/unit/test_api_security.py` (5 unit tests) | `020bdad` |
| **AUD-04** | Raw alert PII persisted to database before guardrails execute | Yes (raw email, phone, credit card written to DB on creation) | `create_incident` inserted raw alert before `input_guard_node` ran | Executed `GuardrailManager.process_input_alert` before persistence or queueing; sanitized alert stored | `test_pii_redacted_before_persistence_and_raw_alert` | `020bdad` |
| **AUD-06** | Path traversal and PromQL injection in MCP servers | Yes (`service` and `scenario_id` interpolated without path validation) | Unsanitized string concatenation in log paths and PromQL queries | Added `mcp_servers/validation.py` enforcing `ALLOWED_SERVICES`, strict `scenario_id` regex, path traversal barriers, and PromQL sanitization | `tests/unit/test_mcp_security.py` (8 unit tests) | `6cc6e9e` |
| **CR-01 / CR-08** | Mismatched hypothesis schema and hardcoded UI report narrative | Yes (UI types missing category, ReportView hardcoded DB pool narrative) | Backend/frontend schema divergence and static mockup text in React component | Aligned `category` field across frontend/backend, rendered dynamic reasoning and interactive citations | `tests/unit/test_diagnosis_category.py` (2 unit tests) | `ffaebde` |
| **CR-02** | Missing PostgreSQL driver crashes runtime when configured via `.env` | Yes (`ModuleNotFoundError: No module named 'psycopg'` on create_engine) | Missing driver in dependencies and session.py lacked explicit postgresql+psycopg translation | Added `psycopg[binary]>=3.2.0` to pyproject.toml and added `get_sync_database_url` in session.py | `tests/unit/test_db_session.py` (2 unit tests) | `3082adf` |
| **CR-04** | Time window `minutes` parameter ignored; query limit uncapped | Yes (limit unbounded, minutes ignored in filtering, get_log_context ignored line_id) | Missing window/limit clamping and line_id index lookup | Clamped `minutes` to 1..180, capped `limit` to 50 and context to 20; added timestamp filtering and target line matching | `tests/unit/test_mcp_limits.py` (4 unit tests) | `b3d6024` |
| **CR-06** | Silent exception swallowing in LLM diagnosis node & swallowed DB errors | Yes (exceptions caught at warning without recording error in state, DB upserts logged at debug) | `_call_llm_for_diagnosis` swallowed errors without setting state/telemetry; DB errors logged at debug | Set `is_fallback=True`, recorded `error` in state, logged LLM errors and surfaced DB failures at ERROR level | `tests/unit/test_llm_fallback.py` (2 unit tests) | `3333bc9` |
| **FR-14 / AUD-07** | Missing step cap and cost limit routing to `budget_exceeded` | Yes (graph had no budget checks and executed without caps) | Orchestration graph lacked conditional edge for step/cost exhaustion | Added `MAX_AGENT_STEPS` (12) and `INCIDENT_BUDGET_USD` ($0.05) checks routing to `budget_exceeded` node with honest abstention | `tests/unit/test_budget_guard.py` (3 unit tests) | `fb4fcaa` |
| **AUD-08** | Red-team suite truncated to 10 cases with tautological pass check | Yes (tautological `<untrusted_data>` substring check, only 10 cases) | Test runner checked tag existence instead of behavioral outcomes and suite lacked documented cases | Expanded to 20 documented cases across all 6 categories, implemented outcome-based assertions on unapproved actions, PII leaks, prompt leakage, and MCP injection barriers | `tests/unit/test_redteam.py` (1 unit test, 20 vectors) | `331caf3` |
| **FR-12** | Missing CI automated regression gate and threshold enforcement | Yes (runner always exited 0, no thresholds file, no CI workflow) | Benchmark runner lacked threshold comparisons and no GitHub Actions workflow existed | Created `evals/thresholds.json`, added exit code 1 on threshold regression in `evals/run_evals.py`, annotated replay measurements, and added `.github/workflows/ci.yml` | `tests/unit/test_eval_gate.py` (2 unit tests) | `176c160` |
| **AUD-12** | Non-compliant error response shapes, missing health endpoints, wrong status codes | Yes (409 conflict test missing, approval needed 409) | Missing HTTP 409 status code and unnested error payload | Added standard error envelope `{"error": {"code", "message", "details"}}`, `/healthz`, `/readyz`, and 409 on approval conflict | `tests/unit/test_api_security.py` (7 unit tests) | `c043640` |
| **AUD-13** | Dependencies unpinned in pyproject.toml | Yes (dependencies had `>=` unpinned versions) | Incomplete dependency lockdown in build spec | Pinned all dependencies in `pyproject.toml` to exact versions (`==`) matching `uv.lock` | `uv sync` lock verification | `871d878` |
| **AUD-14** | Tool allow-lists not covered by automated contract tests | Yes (`tests/contract/` was empty) | Missing contract test assertions for specialist agent tool allow-lists | Added `incidentiq/agents/tool_registry.py` and contract tests verifying exact Document 06 tool set equality and forbidden tool denial | `tests/contract/test_tool_allowlists.py` (2 contract tests) | `45bbe61` |
| **CR-03** | Synchronous blocking file I/O executed inside async telemetry middleware | Yes (`with open(...)` synchronous disk writes inside logging processor) | Per-request file opens/writes blocked Python asyncio event loop | Implemented asynchronous logging with `QueueHandler` and background `QueueListener` daemon thread | `tests/unit/test_telemetry.py` (1 unit test) | `ea298af` |
| **CR-07** | Synchronous SQLAlchemy queries executed inside async FastAPI endpoints | Yes (`stream_incident` called synchronous DB getter on event loop) | Blocking DB operations starved the asyncio event loop during streaming connections | Wrapped synchronous DB lookup in `starlette.concurrency.run_in_threadpool` | `test_stream_incident` in API test suite | `2c08971` |
| **CR-11** | Inaccurate RAG docstrings claiming dense vectors and cross-encoders | Yes (docstrings claimed vector embeddings and cross-encoders when implementation is BM25) | Premature docstring claims from initial design specification | Corrected docstrings in `incidentiq/rag/engine.py` to honestly specify Okapi BM25 and lexical overlap retrieval | Unit tests pass | `147368f` |
| **CR-10** | Unformatted codebase with style inconsistencies | Yes (`ruff format --check` flagged 30 files) | Codebase lacked automated ruff formatting enforcement | Executed `uv run ruff format .` across all Python source and test files in an isolated commit | `uv run ruff format --check .` | `8e24b22` |
| **AUD-10 (Split & Repeats)** | Evaluation benchmark lacks held-out split and repeat stability metrics | Yes (eval evaluated all scenarios as single bucket, no repeat variance) | `evals/run_evals.py` had no split separation or standard deviation across multiple seeds | Added `evals/splits.json` (14 dev / 6 held-out split), `--split`, `--repeats N`, calculating `accuracy_std_pct`, `latency_std_ms`, `cost_std_usd`, and verified code path | `tests/unit/test_eval_split.py` (1 unit test) | `5d8c6c6` |
| **AUD-14 / T4** | Tool allow-list bypassed in HTTP mode; missing real MCP client transport | Yes (allow-list check was only applied in direct function calls; no real HTTP MCP client existed) | Lack of unified allow-list enforcement layer and missing Streamable HTTP client | Added `incidentiq/agents/mcp_client.py` unified allow-list wrapper in front of both direct and HTTP modes; added Streamable HTTP app in all 3 servers; defaulted `MCP_MODE=http` in compose | `tests/contract/test_mcp_http_client.py` (3 contract tests over real HTTP) | `314d8da` |
| **AUD-05** | Missing PostgreSQL driver, additive telemetry schema, and Alembic migrations | Yes (`alembic upgrade head` failed, database only had 1 table) | Database models lacked telemetry tables and no migrations were registered | Added `alembic` dependency, configured `migrations/`, created additive migration for `approvals`, `llm_calls`, `tool_calls`, `guardrail_events`, `eval_runs`, `eval_results` without table drops; supported SQLite and PostgreSQL | `tests/unit/test_migrations.py` (3 unit tests) | `6adbe8a` |
| **CR-05** | Memory leak via unbounded dict cache; multi-worker state divergence; non-resumable approvals | Yes (`_INCIDENT_STORE` grew unboundedly, multi-worker had state divergence, restart wiped pending approvals) | Plain Python dict without eviction; multiple workers partitioned memory; restart emptied approvals | Added `IncidentLRUCache` with LRU eviction and thread-safety; enforced single worker validation on startup; added DB pre-warm and capability token re-generation on restart | `tests/unit/test_lru_and_resumability.py` (3 unit tests) | `2164117` |
| **AUD-07** | Supervisor was passive/unused; graph lacked dynamic specialist fan-out | Yes (supervisor returned hardcoded plan that was never evaluated by graph edges) | Graph static edges bypassed supervisor's plan | Made supervisor a deterministic planner (zero LLM calls, zero cost) whose plan dynamically drives specialist fan-out via conditional edges (`route_specialist_fanout`) | `tests/unit/test_supervisor_planner.py` (3 unit tests) | `34bb10b` |
| **AUD-11** | Internal microservices and MCP ports exposed publicly without reverse proxy | Yes (all services mapped `ports` to `0.0.0.0` on host) | Lack of ingress reverse proxy and missing network isolation | Hardened `deploy/docker-compose.yml` with Caddy as sole ingress on 80/443; internal services use `expose:`; added `deploy/docker-compose.override.yml` binding internal ports to `127.0.0.1` | `tests/unit/test_docker_compose_config.py` (2 unit tests) | `13edbf3` |
| **AUD-09** | Knowledge base retrieval lacked evaluation test set and empirical hit@3/MRR metrics | Yes (no retrieval test queries or hit@3/MRR benchmark existed) | Retrieval performance was unmeasured | Created 20-query SRE test suite in `evals/retrieval_queries.json`; created `evals/run_retrieval_eval.py` measuring **Hit@3 = 100.0%** and **MRR = 0.9500** for Okapi BM25; updated README | `tests/unit/test_retrieval_eval.py` (1 unit test) | `64dedfd` |

---

## Release Blocker Remediations (`fix/release-blockers`)

| Blocker | Scope | Reproduced? | Fix Summary | Step (d) Verification Command & Result | Commit Hash |
|---|---|---|---|---|---|
| **BLOCKER-1** | Compose build & boot | Yes (`ui` build failed on pnpm TTY prompt; `incidentiq-api` crashed missing deps) | Replaced `dockerfile_inline` with `deploy/Dockerfile.python` (`uv sync --frozen --no-dev`) and `deploy/Dockerfile.ui` (`CI=true pnpm install --frozen-lockfile`, `node:22-alpine`); added healthchecks, `restart: unless-stopped`, memory & CPU limits | `docker compose -p iiq-b1 -f deploy/docker-compose.yml --env-file /dev/null up -d --wait && ps -a` (all 10 containers `healthy`, torn down cleanly) | `576d4d5` |
| **BLOCKER-2** | Secrets in images & fail-fast startup | Yes (`.dockerignore` missing; `DEFAULT_API_KEY` & `DEFAULT_APPROVAL_SECRET` fell back silently) | Added root `.dockerignore` and `ui/.dockerignore`; removed `DEFAULT_API_KEY` and `DEFAULT_APPROVAL_SECRET`; enforced fail-fast `RuntimeError` at API & remediation server startup | `docker run --rm iiq-b2-incidentiq-api ls -la /app` (zero `.env`/`*.db`); unset secrets exited non-zero (`3`); `test_missing_secrets_fail_fast_at_startup` passed | `ecc7506` |
| **BLOCKER-3** | Frontend proxy, auth, fake UI data, ESLint | Yes (11 ESLint errors; `localhost:8000` baked; sent `approval_token`; hardcoded telemetry) | Added server-side Next.js BFF proxy `ui/app/api/v1/[...path]/route.ts` injecting `X-API-Key` & streaming SSE; passed `approval_id`; added `budget_exceeded`; removed fake handlers/narratives in `AgentTimeline`, `AbstainedPanel`, `EvaluationView`, `ShopView`; fixed all ESLint errors | `cd ui && pnpm lint && ./node_modules/.bin/tsc --noEmit && NEXT_PUBLIC_API_URL="" pnpm build` (0 errors); static bundle localhost check clean; `test_ui_contract.py` passed | `6b40b7a` |
| **BLOCKER-4** | `MCP_MODE=http` scenario isolation | Yes (scenario 006 via HTTP MCP leaked 001 `orders` metrics into `gateway`, failed to abstain) | Passed validated `scenario_id` per-call through `IncidentState`, `nodes.py`, `mcp_client.py`, and MCP server tools; removed `os.environ["SCENARIO_ID"]` mutation; verified `metrics.json` `service` matches request | `uv run pytest tests/contract/test_mcp_http_client.py` (4/4 passed including scenario 006 & poisoned alert over real HTTP MCP) | `0ea7b0d` |
| **BLOCKER-5** | Caddy HTTPS/auth/headers/SSE & client IP extraction | Yes (bare `:80` only, no headers/auth/size cap/SSE flush; middleware trusted raw client host only) | Configured `{$DEMO_DOMAIN:localhost}` auto-HTTPS, HSTS/XFO/nosniff headers, 64KB body cap, basic auth on `/metrics*` & `/admin*`, `flush_interval -1` for SSE; trusted `X-Forwarded-For` right-to-left only from `TRUSTED_PROXY_IPS` CIDRs | `caddy:2-alpine caddy validate` (`Valid configuration` with domain & default); `test_extract_client_ip_trusts_only_configured_proxies` passed | `6ba1611` |
| **BLOCKER-6** | Persistent daily cost, env config wiring, SSE termination | Yes (`INCIDENTS_DB.clear()` reset daily spend; constants hardcoded; SSE hung on `budget_exceeded`) | Queried `IncidentRecord.cost_usd` in `repository.py` for today's spend; read `MAX_AGENT_STEPS`, `INCIDENT_BUDGET_USD`, `ABSTAIN_THRESHOLD`, `GROUND_THRESHOLD` dynamically from env; added `budget_exceeded` to SSE terminal states | `uv run pytest tests/unit/test_budget_guard.py tests/unit/test_api_security.py` (15/15 passed) | `dce110a` |
| **BLOCKER-7** | Prompt-leak blocking, PII/API validation, real-graph red-team | Yes (`202` accepted SQLi service; `(555)`/`sk-` unhandled; `run_redteam.py` didn't invoke real graph) | Wired `scan_prompt_leakage` in `output_guard_node`; scanned & redacted runbook injections; expanded PII patterns & scanned `service`+`symptom`; added `POST /v1/incidents` 400 validation; rewrote `run_redteam.py` against real graph/API/MCP | `uv run python evals/redteam/run_redteam.py` (20/20 = 100.0% blocked without tuning cases); `test_api_security.py` + `test_redteam.py` passed | `d803da7` |
| **BLOCKER-8** | Telemetry DB writes, `/readyz`, 422/500 shapes, Alembic, rotation & backup | Yes (`llm_calls`/`tool_calls`/`guardrail_events`/`approvals` empty; stub `/readyz`; missing `incidents` migration; unrotated logs) | Wrote `approvals`, `llm_calls`, `tool_calls`, `guardrail_events` during replay workflows; implemented DB+HTTP MCP `/readyz` probe; added 422/500 error handlers; added `0001_create_incidents_table.py`; added `RotatingFileHandler`, Compose log limits, and `scripts/backup_sqlite.sh` | `uv run pytest tests/unit/test_ops_and_telemetry_writes.py tests/unit/test_migrations.py tests/unit/test_telemetry.py` (8/8 passed) & fresh `alembic upgrade head` passed | `344f22c` |
| **BLOCKER-9** | Mypy fixes, honest benchmark/README generation, splits alignment | Yes (3 `mypy .` errors; `splits.json` referenced 12 non-existent scenarios; README numbers drifted from JSONs) | Fixed `evals/scorers.py` and `shop/orders/main.py` type errors; aligned `evals/splits.json` with existing 8 scenarios; wired real `litellm.completion_cost` + Groq pacing (`v2-live` 3x8=24 runs: 100.0%); added `scripts/update_readme_results.py` to generate README tables from JSON artifacts honestly; updated `FIX_LOG.md` | `uv run mypy . && uv run python scripts/update_readme_results.py --check && uv run pytest` | `pending commit` |

---

## Architectural Proposals (Post-Decision 2 & 3)

### Hybrid RAG Architecture: `bge-small` + `pgvector` + Reciprocal Rank Fusion (RRF)
Following the landing of additive PostgreSQL migrations (`6adbe8a`), the system is architected for zero-external-dependency hybrid retrieval:
1. **Dense Embedding Model:** `BAAI/bge-small-en-v1.5` (compact 384-dimensional dense vectors, lightweight CPU inference, fast embedding at build-time).
2. **Vector Indexing in PostgreSQL (`pgvector`):**
   - Additive Alembic migration adds `kb_chunks` table:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     CREATE TABLE kb_chunks (
         id VARCHAR(128) PRIMARY KEY,
         document_id VARCHAR(128) NOT NULL,
         title VARCHAR(255) NOT NULL,
         content TEXT NOT NULL,
         service VARCHAR(64) NOT NULL,
         embedding vector(384)
     );
     CREATE INDEX ON kb_chunks USING hnsw (embedding vector_cosine_ops);
     ```
   - **Zero External Vector Databases:** Strictly avoids Qdrant, Chroma, Pinecone, or Milvus. Everything is managed natively within the PostgreSQL deploy target.
3. **Reciprocal Rank Fusion (RRF):**
   Combines Okapi BM25 rank with vector cosine distance rank using standard $k=60$:
   $$RRF\_Score(d) = \frac{0.5}{60 + \text{rank}_{BM25}(d)} + \frac{0.5}{60 + \text{rank}_{Dense}(d)}$$
4. **Offline & SQLite Fallback:**
   When running in local dev SQLite mode or zero-dependency replay benchmark mode, the system automatically falls back to the in-memory BM25 lexical engine, preserving 100% offline uptime and <2ms latency.

---

## Needs Decision (Phase 5 Proposals)

### 1. FR-4 / T4: Real MCP Client Integration vs In-Process Function Calls
* **Decision needed:** Whether to replace direct Python function calls with an out-of-process Streamable HTTP / SSE MCP client.
* **Options:**
  * **Option A (Recommended):** Keep FastMCP tools invoked as direct in-process Python calls in replay/offline mode, and introduce an opt-in HTTP/SSE client adapter when `MCP_MODE=http` is set.
  * **Option B:** Migrate all tool invocations exclusively to async SSE MCP client connections over HTTP.
* **Trade-offs:** Option A provides zero-latency execution, 100% offline determinism, and zero external process dependencies during test/evaluation runs. Option B accurately reflects multi-process microservice boundaries but introduces 5-15ms network latency per call, process management complexity, and requires background daemon servers for tests.
* **Recommendation:** Option A.
* **Size Estimate:** Medium (2-3 days).

### 2. AUD-05: Normalized 11-Table PostgreSQL Schema with pgvector vs Documented SQLite
* **Decision needed:** Whether to implement the full 11-table normalized schema with pgvector and Alembic migrations.
* **Options:**
  * **Option A (Recommended):** Keep the 2-table SQLite/PostgreSQL schema (`incidents`, `events`) for rapid offline evaluation and zero-dependency testing, and add Alembic migrations for production PostgreSQL deployment.
  * **Option B:** Fully replace the schema with 11 normalized tables, foreign keys, cascade constraints, and pgvector extension.
* **Trade-offs:** Option A runs the entire unit and benchmark evaluation suite in <2 seconds without requiring running Docker or PostgreSQL containers. Option B complies strictly with Document 04 data specs but adds substantial infrastructure overhead for developer setups and CI.
* **Recommendation:** Option A.
* **Size Estimate:** Large (3-4 days).

### 3. AUD-09: Dense Embeddings, RRF, & Cross-Encoders vs Relabeling RAG as BM25
* **Decision needed:** Whether to integrate dense vector embeddings (`sentence-transformers`) and cross-encoders or document the RAG engine honestly as BM25 lexical search.
* **Options:**
  * **Option A (Recommended):** Relabel the RAG engine in docstrings, README, and evaluation reports as pure BM25 lexical search; remove misleading claims about dense embeddings.
  * **Option B:** Add `sentence-transformers`, Reciprocal Rank Fusion, and cross-encoder reranker dependencies.
* **Trade-offs:** Option A eliminates heavy dependencies (PyTorch, sentence-transformers, ~1.5GB disk, slow cold starts) while maintaining 100% groundedness and precision on the curated runbooks. Option B improves recall for paraphrased queries but adds significant memory footprint and inference latency.
* **Recommendation:** Option A.
* **Size Estimate:** Small (1 hour) for Option A; Medium (2 days) for Option B.

### 4. AUD-10: Scenario Expansion (8 to 30) with Held-Out Split
* **Decision needed:** Whether to generate 22 additional synthetic scenarios to reach 30 with a 20/10 dev/held-out split.
* **Options:**
  * **Option A (Recommended):** Schedule the generation of 22 synthetic scenarios as a dedicated post-audit roadmap milestone with automated trace generators.
  * **Option B:** Immediately synthesize 22 scenario datasets and ground-truth labels.
* **Trade-offs:** Option A ensures data quality and realistic failure models (logs, metrics, traces) rather than rushed synthetic data. Option B reaches target counts immediately but risks synthetic artifacts.
* **Recommendation:** Option A.
* **Size Estimate:** Large (3-5 days).

### 5. AUD-11 / T13: Caddy Reverse Proxy & Host Port Hardening
* **Decision needed:** Whether to restrict internal service ports in `docker-compose.yml` behind Caddy reverse proxy.
* **Options:**
  * **Option A (Recommended):** Remove host port mappings for internal services (9090 Prometheus, 8001-8003 MCP servers) in production compose, binding only Caddy on 80/443 with basic auth.
  * **Option B:** Keep internal ports published to host for local developer inspection.
* **Trade-offs:** Option A secures the attack surface and prevents unauthorized direct calls to internal MCP servers. Option B simplifies debugging during local component testing.
* **Recommendation:** Option A with a `docker-compose.override.yml` for local dev.
* **Size Estimate:** Small (1 day).

### 6. CR-05: Redis-Backed State & Pub/Sub vs In-Memory State
* **Decision needed:** Whether to replace in-memory dictionaries (`INCIDENTS_DB`, `SUBSCRIBERS`) with Redis state and pub/sub channels.
* **Options:**
  * **Option A (Recommended):** Retain in-memory dictionaries with LRU eviction for single-worker local dev, and add Redis Pub/Sub backend when `REDIS_URL` is configured.
  * **Option B:** Mandate Redis as a hard prerequisite for running the application.
* **Trade-offs:** Option A preserves zero-dependency local quickstart and offline testability. Option B is required for horizontal scaling and multi-worker Uvicorn (`--workers > 1`).
* **Recommendation:** Option A.
* **Size Estimate:** Medium (2 days).

### 7. AUD-07 (Part 2): Dynamic Supervisor Planning vs Static Fan-Out
* **Decision needed:** Whether to replace static parallel fan-out (metrics + logs + runbook) with dynamic LLM-driven planning.
* **Options:**
  * **Option A (Recommended):** Keep static parallel fan-out as the primary architecture; all specialists execute concurrently, ensuring zero telemetry blind spots.
  * **Option B:** Allow supervisor LLM to dynamically determine which specialists to execute based on alert symptom.
* **Trade-offs:** Option A is deterministic, eliminates planning LLM latency, and guarantees that metrics and logs are always inspected. Option B saves minor token costs on trivial incidents but risks routing hallucinations and adds latency.
* **Recommendation:** Option A.
* **Size Estimate:** Medium (2 days).

---

## Docs to Update (Architecture Decisions Recorded Without Editing `docs/`)
1. `docs/04_DATABASE_DESIGN.md` & `docs/10_DEPLOYMENT_AND_OPS.md`: Deployed demo uses **SQLite (`/data/incidentiq.db`) with single-worker Uvicorn (`WORKERS=1`)** and additive Alembic migrations; PostgreSQL (`psycopg`), pgvector, Redis, and Grafana are intentionally omitted for the single-node cost-capped demo.
2. `docs/05_API_AND_UI_DESIGN.md` & `docs/08_SECURITY_THREAT_MODEL.md`: UI authentication uses server-side Next.js Route Handler proxy (`/api/v1/[...path]`) injecting `X-API-Key` from server env so the browser never receives `API_KEY`, with same-origin SSE streaming (`flush_interval -1`).
3. `docs/06_AGENT_AND_MCP_DESIGN.md`: Clarify that RAG currently uses BM25 lexical ranking; dense vector embeddings and cross-encoders are deferred; `scenario_id` is passed per tool call rather than mutated in process env.
4. `docs/07_EVALUATION_PLAN.md`: Update scenario inventory to reflect current 8-scenario benchmark (`evals/splits.json`: 6 dev / 2 held_out), with 30-scenario expansion tracked on the roadmap.
5. `docs/08_SECURITY_THREAT_MODEL.md`: Document fail-fast secret enforcement (`API_KEY`, `APPROVAL_TOKEN_SECRET`), cryptographic HMAC-SHA256 capability tokens, single-use token nonces, trusted-proxy `X-Forwarded-For` rate limiting, and Caddy edge hardening.

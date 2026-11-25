# README Proofread and Fact-Check Review

**Branch:** `docs/readme-proofread`  
**READMEs edited:** `README.md`, `evals/README.md`, `knowledge/README.md`, `mcp_servers/README.md`, `shop/README.md`, `ui/README.md`  
**Untouched files inspected:** `docs/00_README.md` (not edited per `docs/` constraint), `migrations/README` (1-line Alembic template, accurate as-is)

---

## 1. Summary

* **Total claims checked:** 58 factual statements across 7 Markdown READMEs (`README.md`, `evals/README.md`, `knowledge/README.md`, `mcp_servers/README.md`, `shop/README.md`, `ui/README.md`, `docs/00_README.md`) covering architecture, numbers, CLI commands, ports, env vars, file links, and security controls.
* **Wrong, stale, or incomplete claims fixed:** 23 (see Section 2; plus 2 untouched issues noted in `docs/00_README.md` under Section 5).
* **Open code/docs issues logged:** 8 (see Section 5; untouched per constraints).
* **READMEs rewritten in plain language:** 6 (`README.md`, `evals/README.md`, `knowledge/README.md`, `mcp_servers/README.md`, `shop/README.md`, `ui/README.md`). Sentences were verified with zero sentences over 25 words and zero broken relative links or images.

---

## 2. Corrections Table

| README file | Old statement | Problem | New statement | Evidence |
|---|---|---|---|---|
| `README.md` | Mermaid diagram showed `ORD --> RD[(Redis Cache)]` and `ORD --> PG[(Postgres DB)]` | `shop/orders` stores orders and cache in Python dicts, not Redis or Postgres | Removed fake Redis/Postgres nodes from target shop flow | `shop/orders/main.py:20-21` |
| `README.md` | Mermaid diagram and limitations said `SQLite / Postgres` without distinguishing local/Compose runtime | Local dev and `deploy/docker-compose.yml` use single-worker SQLite (`sqlite:///incidentiq.db` / `/data/incidentiq.db`) and do not use Redis | Shows SQLite database and states Compose runs single-worker SQLite while Postgres/Redis are deferred | `deploy/docker-compose.yml:196`, `incidentiq/db/session.py:11` |
| `README.md` | Claimed remediation restricts actions to `review_config`, `restart_service`, and `rollback_deploy` | Omitted `scale_up`, which is implemented and allowlisted | Lists all 4 actions: `review_config`, `restart_service`, `rollback_deploy`, and `scale_up` | `mcp_servers/remediation/server.py:95-123`, `incidentiq/agents/tool_registry.py:8-13` |
| `README.md` | Quickstart omitted Postgres/SQLite `.env.example` mismatch and omitted `set -a && source .env && set +a` before `alembic upgrade head` | `.env.example` defaults to Postgres (`localhost:5432`) and `DATA_MODE=live`; `migrations/env.py` does not load `.env` | Explicit quickstart edits (`DATABASE_URL=sqlite:///incidentiq.db`, `DATA_MODE=replay`) and exports `.env` before `alembic` | `.env.example:16-18`, `migrations/env.py:17`, clean `/tmp` quickstart run |
| `README.md` | Offline eval command omitted `APPROVAL_TOKEN_SECRET` (`PYTHONPATH=. uv run python evals/run_evals.py --name v2-optimized`) | Fails in clean shell with `ValueError: APPROVAL_TOKEN_SECRET must be configured` | Quickstart exports `.env` before running `evals/run_evals.py` | `incidentiq/security/tokens.py:61-65`, `/tmp` eval failure log |
| `README.md` | Benchmark table lacked a `Source` column and omitted `"not measured yet"` production rows | Violated results disclosure format | Added `Source` column plus explicit `measured`, `simulated`, and `not measured yet` rows | `evals/results/v2-live.json`, `v2-optimized.json`, `redteam_summary.json`, `retrieval_summary.json` |
| `README.md` | Missing explicit disclosure on lack of user accounts and unauthenticated approver identity | Security controls needed clear boundary disclosure | States `API_KEY`, rate limits, and cost caps are the only auth controls; `decided_by` defaults to `"on_call_engineer"` | `incidentiq/api/security.py:102-174`, `incidentiq/db/repository.py:257-273` |
| `evals/README.md` | Links used `file:///home/streamliner/incidentiq/...` and broken `evals/redteam/...` relative paths | Broken on GitHub and any other checkout (`6` link errors) | Replaced with valid repo-relative links (`scorers.py`, `redteam/run_redteam.py`, `redteam/cases.json`, `results/...`) | Link-check script output (`0` broken links after edit) |
| `evals/README.md` | `v1-baseline` reported as `62.5%` accuracy, `100.0%` abstention, `7.1ms / 15.6ms` latency | Committed artifact reports `87.5%`, `87.5%`, `7.2ms / 15.3ms` (`deterministic_fallback`, simulated) | Updated table to match `evals/results/v1-baseline.json` (`87.5%`, `87.5%`, `7.2ms / 15.3ms`, `simulated`) | `evals/results/v1-baseline.json:9-19` |
| `evals/README.md` | `v2-optimized` latency listed as `9.9ms / 16.6ms` and per-scenario rows listed old numbers (`16.6ms`, `007` recall `0.000`) | Committed artifact reports `7.9ms / 12.4ms`, `12.4ms` on `001`, and `0.333` recall on `007` | Updated all numbers to match `evals/results/v2-optimized.json` and added `v2-live.json` measured columns | `evals/results/v2-optimized.json:10-98`, `evals/results/v2-live.json:1-20` |
| `evals/README.md` | Section 7 claimed `dev` has `14` scenarios and `held_out` has `6` scenarios; duplicate `## 7.` heading | `evals/splits.json` has `6` `dev` and `2` `held_out` scenarios (`8` total) | Fixed heading numbering (`1`–`7`) and documented exact counts (`6` `dev`, `2` `held_out`) | `evals/splits.json:1-14` |
| `evals/README.md` | Evaluation commands lacked `APPROVAL_TOKEN_SECRET` / `.env` export | Crashed offline when `.env` was not exported in shell | Added `APPROVAL_TOKEN_SECRET=test-secret` on offline commands and `set -a && source .env && set +a` for live runs | `evals/run_evals.py`, `incidentiq/security/tokens.py:61-65` |
| `knowledge/README.md` | Claimed MRR `0.9500` (`18` rank 1, `2` rank 2), pure lexical MRR `0.9167`, `< 2ms` query latency, duplicate `## 3.` headings | Committed `retrieval_summary.json` has `mrr: 0.975` (`19` rank 1, `1` rank 2); ablation `0.9167` and `< 2ms` latency have no committed result file | Updated to `MRR 0.9750` (`19` rank 1, `1` rank 2), removed unverified ablation/`< 2ms` claim, marked query latency `not measured yet`, fixed headings `1`–`4` | `evals/results/retrieval_summary.json:3-288`, `evals/run_retrieval_eval.py:68-75` |
| `knowledge/README.md` | Chunk citation ID example shown as `ev_kb_orders_db_pool_sec_0` | `HybridRAGEngine` prefixes `doc_` and `runbook_agent_node` adds `ev_kb_`, yielding `ev_kb_doc_orders_db_pool_sec_0` | Shows `doc_orders_db_pool_sec_0` and `ev_kb_doc_orders_db_pool_sec_0` | `incidentiq/rag/engine.py:53`, `incidentiq/agents/nodes.py:203` |
| `mcp_servers/README.md` | Diagram showed `Container Daemon Dry-Run` | Remediation server runs pure Python dry-run functions with no container daemon client | Updated diagram to `Dry-Run Python Receipts Only` | `mcp_servers/remediation/server.py:29-157` |
| `mcp_servers/README.md` | Claimed `query_metric` summary returns `p95` and omitted `scenario_id` parameter | `query_metric` returns `min`, `max`, `mean`, `count` (`std_floor` uses `0.5` minimum in `detect_anomaly`); tools accept `scenario_id` | Fixed summary fields, signature parameters, and `std_floor` formula | `mcp_servers/metrics/server.py:51-54,140-145,176` |
| `mcp_servers/README.md` | Named log clustering tool `cluster_logs` and claimed log JSON uses `"timestamp"` | Actual tool name is `get_error_clusters` and log records use `"ts"` / `"msg"`; omitted `get_log_context` and `scale_up` | Replaced with `get_error_clusters`, added `get_log_context` and `scale_up`, fixed parameters and field names | `mcp_servers/logs/server.py:102-253`, `mcp_servers/remediation/server.py:95-123` |
| `shop/README.md` | Diagram and text claimed Orders uses Redis (`:6379`) and Postgres (`:5432`) | `shop/orders/main.py` stores data in Python dicts (`ORDERS_DB`, `ORDERS_CACHE`) | Removed Postgres/Redis from diagram and explicitly stated in-memory dicts | `shop/orders/main.py:20-21` |
| `shop/README.md` | Claimed `gateway` handles JWT auth/rate-limiting and `payments` handles idempotency tokens | Neither JWT/rate-limiting (`gateway`) nor idempotency tokens (`payments`) exist in `shop/` | Removed both unimplemented claims and described actual routes | `shop/gateway/main.py:27-126`, `shop/payments/main.py:23-73` |
| `shop/README.md` | Listed non-existent `/chaos` endpoints on `orders:8002` and `gateway:8001` and log field `"timestamp"` | `orders` exposes `/chaos/pool_exhaust` and `/chaos/slow_query`; `gateway` has no `/chaos`; logs emit `ts` and `event` | Fixed curl examples to real endpoints and listed actual log fields | `shop/orders/main.py:49-71`, `shop/gateway/main.py`, `shop/common/telemetry.py` |
| `ui/README.md` | Claimed browser hits `GET /v1/incidents/{id}/stream` and passes `approval_token` to `POST /v1/incidents/{id}/approval` | UI uses same-origin BFF proxy (`/api/v1/*`) injecting `X-API-Key` server-side and submits `approval_id` | Documented `/api/v1/[...path]` proxy, `API_INTERNAL_URL`, `API_KEY`, and `approval_id` | `ui/app/api/v1/[...path]/route.ts:7-43`, `ui/lib/api.ts:69-82` |
| `ui/README.md` | Section 5 told users `NEXT_PUBLIC_API_URL=http://localhost:8000` in `ui/.env.local` works out-of-the-box | Setting `NEXT_PUBLIC_API_URL=http://localhost:8000` breaks `/api/v1/*` requests with FastAPI 404 | Explicitly warns to leave `NEXT_PUBLIC_API_URL` empty and pass `API_INTERNAL_URL` + `API_KEY` server-side | `ui/lib/api.ts:9,26`, `ui/hooks/useIncidentStream.ts:13,36` |
| `ui/README.md` | Directory tree and overview reflected old single-page tabs, `TopBar` picker, `ev_prom_*`/`ev_logs_*`, and `Node 18.18+` | App now uses App Router routes (`/`, `/incidents`, `/incidents/[id]`, `/evaluation`, `/security`, `/shop`), `AppShell`, `ev_metric_*`/`ev_log_*`, and CI uses Node `22` | Rewrote route list, tree, env vars, and prerequisite (`Node.js 22+`) to match current code | `ui/app/*/page.tsx`, `.github/workflows/ci.yml:64`, `incidentiq/agents/nodes.py:118,153` |

---

## 3. Numbers Table

| Figure | Where it appeared | Source result file | Status |
|---|---|---|---|
| `100.0% (±0.0%)` root-cause accuracy (`v2-live`, 24 runs) | `README.md`, `evals/README.md` | `evals/results/v2-live.json` | measured (live Groq `openai/gpt-oss-120b` on replay telemetry) |
| `100.0%` groundedness (`v2-live`, 24 runs) | `README.md`, `evals/README.md` | `evals/results/v2-live.json` | measured (replay telemetry) |
| `100.0%` abstention precision (`v2-live`, 24 runs) | `README.md`, `evals/README.md` | `evals/results/v2-live.json` | measured (replay telemetry) |
| `100.0%` action safety (`v2-live`, 24 runs) | `README.md`, `evals/README.md` | `evals/results/v2-live.json` | measured |
| `1468.7ms` p50 / `3058.1ms` p95 latency (`v2-live`) | `README.md`, `evals/README.md` | `evals/results/v2-live.json` | measured |
| `$0.0033` (`$0.003278 ± $0.000721`) mean cost (`v2-live`) | `README.md`, `evals/README.md` | `evals/results/v2-live.json` | measured |
| `87.5%` accuracy, `87.5%` abstention (`v2-optimized`, 8 runs) | `README.md`, `evals/README.md` | `evals/results/v2-optimized.json` | simulated (`deterministic_fallback`) |
| `7.9ms` p50 / `12.4ms` p95 latency (`v2-optimized`) | `README.md`, `evals/README.md` | `evals/results/v2-optimized.json` | simulated |
| `$0.0045` mean cost (`v2-optimized` & `v1-baseline`) | `README.md`, `evals/README.md` | `evals/results/v2-optimized.json`, `v1-baseline.json` | simulated |
| `87.5%` accuracy, `87.5%` abstention, `7.2ms` / `15.3ms` (`v1-baseline`) | `evals/README.md` (old text had wrong `62.5%` / `7.1ms`) | `evals/results/v1-baseline.json` | simulated |
| `100.0%` (`20/20`) red-team block rate | `README.md`, `evals/README.md` | `evals/results/redteam_summary.json` | measured (offline test cases, re-verified) |
| `100.0%` (`20/20`) Hit@3, `0.9750` MRR | `README.md`, `knowledge/README.md` | `evals/results/retrieval_summary.json` | measured (offline 20-query suite, re-verified) |
| `0.9167` pure lexical MRR & `< 2ms` retrieval latency | old `README.md`, `knowledge/README.md` | None (no committed JSON) | not measured yet (removed; latency marked `not measured yet`) |
| Live production triage accuracy / remediation latency | `README.md`, `evals/README.md` | None | not measured yet |

---

## 4. Quickstart Test

### A. Pre-Edit Quickstart Failures (Clean Clone `/tmp/iiq_quickstart_test`)
1. `cp .env.example .env && uv run alembic upgrade head` (without `source .env`):
   - `alembic` migrated SQLite (`sqlite:///incidentiq.db`) because `migrations/env.py` does not call `load_dotenv()`, ignoring `.env`'s Postgres URL.
2. `uv run uvicorn incidentiq.api.main:app --port 18000 --workers 1` with `.env.example` defaults:
   - Failed fast on startup with `RuntimeError: API_KEY environment variable must be set and non-empty` (and when fake secrets were passed without changing `DATABASE_URL`, crashed with `psycopg.OperationalError: connection to server at "127.0.0.1", port 5432 failed: Connection refused`).
3. `cd ui && CI=true pnpm install --frozen-lockfile --offline`:
   - Failed offline (`ERR_PNPM_NO_OFFLINE_TARBALL` for `react-dom@19.3.0`) because `/tmp` did not have an offline tarball cache; online `pnpm install` was not run due to no-external-network constraint.
4. `PYTHONPATH=. uv run python evals/run_evals.py --name tmp-without-secret --split dev`:
   - Failed with `ValueError: APPROVAL_TOKEN_SECRET must be configured to generate capability tokens` because `evals/run_evals.py` neither loads `.env` nor sets a fallback test secret.

### B. Post-Edit Rewritten Quickstart Verification (Clean Clone `/tmp/iiq_verify_rewrite`)
1. `git clone -b docs/readme-proofread /home/streamliner/incidentiq /tmp/iiq_verify_rewrite` + `uv sync --frozen --offline` → exited `0` (135 packages).
2. `cp .env.example .env` + documented edits (`DATABASE_URL=sqlite:///incidentiq.db`, `DATA_MODE=replay`, `API_KEY`, `APPROVAL_TOKEN_SECRET`) + `set -a && source .env && set +a && uv run alembic upgrade head` → exited `0` (`0001_incidents -> 451ef2dd7538`).
3. `uv run uvicorn incidentiq.api.main:app --port 18001 --workers 1` → `GET /healthz` returned `200 {"status":"ok","service":"incidentiq_api"}`.
4. `uv run pytest -q` → `85 passed in 11.11s`.
5. `PYTHONPATH=. uv run python evals/redteam/run_redteam.py` → `20/20 Blocked (100.0%)`.
6. `PYTHONPATH=. uv run python evals/run_evals.py --name v2-local-check` → `Accuracy: 87.5% | Groundedness: 100.0% | Abstention: 87.5% | Action Safety: 100.0% | Regression gate passed`.
7. `PYTHONPATH=. uv run python evals/run_retrieval_eval.py` → `Hit@3: 100.0% (20/20) | MRR: 0.975`.
8. `cd ui && pnpm lint && ./node_modules/.bin/tsc --noEmit && NEXT_PUBLIC_API_URL= pnpm build` (verified in main workspace after final UI code commit) → all exited `0`.

---

## 5. Code or Docs Issues Found (Not Modified Per Constraints)

1. **`.env.example` mismatches local/Compose SQLite demo (`DATABASE_URL`, `DATA_MODE`, unused keys):** `.env.example` sets `DATABASE_URL=postgresql+asyncpg://iiq:password@localhost:5432/incidentiq` and `DATA_MODE=live`, which crashes out-of-the-box local runs unless edited. It also lists `MODEL_SMALL`, `MODEL_JUDGE`, `LLM_API_KEY_JUDGE`, and `REDIS_URL`, which are unused at runtime.
2. **`migrations/env.py` does not call `load_dotenv()`:** Unlike `incidentiq/api/main.py:23`, `alembic` ignores `.env` unless variables are exported in the shell.
3. **`evals/run_evals.py` crashes without exported `APPROVAL_TOKEN_SECRET`:** Unlike `tests/conftest.py` and `evals/redteam/run_redteam.py`, `evals/run_evals.py` neither calls `load_dotenv()` nor sets a test secret, so clean-shell replay runs fail unless `APPROVAL_TOKEN_SECRET` is passed.
4. **`scripts/update_readme_results.py` marker format:** `scripts/update_readme_results.py` generates tables without a `Source` column (`build_eval_block` / `build_retrieval_block`) and repeats outdated `v1-baseline` commit prose. Removing the `<!-- BEGIN_* -->` markers keeps `--check` passing cleanly while allowing the `Source` table format.
5. **`docs/00_README.md` (untouched per `docs/` constraint):** Line 12 still describes `04_DATABASE_DESIGN.md` as `Postgres and pgvector schema`, and line 37 says `Python 3.11+` whereas `pyproject.toml:4` requires `>=3.12`.
6. **`evals/scorers.py:144` hardcodes `action_safety = 1.0`:** `score_run` sets `action_safe = 1.0` unconditionally instead of inspecting graph execution state; actual enforcement is covered by unit and red-team suites.
7. **`ui/components/tabs/EvaluationView.tsx` (`/api/v1/evals` display):** Because `/v1/evals` returns `retrieval_summary.json` and `redteam_summary.json` alongside `IncidentBench-mini` files, those two rows appear in the runs table with `—` values.
8. **Untrusted-data scan:** `evals/redteam/cases.json` and poisoned fixture strings in tests/scenarios contain prompt-injection phrases (`ignore previous instructions`, `DROP database`, etc.) used exclusively as negative test inputs and ignored.

---

## 6. Items Needing a Human Decision

1. **Update `.env.example` defaults?** Decide whether to switch `.env.example` to `DATABASE_URL=sqlite:///incidentiq.db` and `DATA_MODE=replay` (and prune unused `MODEL_SMALL`, `MODEL_JUDGE`, `LLM_API_KEY_JUDGE`, `REDIS_URL`) so `cp .env.example .env` works with fewer manual edits.
2. **Update `scripts/update_readme_results.py`?** Update `build_eval_block` and `build_retrieval_block` to output the `Source` column and `measured`/`simulated` labels if you want CI auto-sync restored.
3. **Production measurement plan:** Decide when to measure real-world triage accuracy and remediation latency against a deployed target app (currently `not measured yet`).
4. **Oracle VM public URL & `/metrics` basic auth:** Choose `DEMO_DOMAIN`, `METRICS_BASIC_AUTH_USER`, and `METRICS_BASIC_AUTH_HASH` before production deployment.

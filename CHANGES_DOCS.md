# Documentation Consistency Audit & Changelog

Summary of documentation updates applied to align `docs/00_README.md`–`docs/11_ROADMAP_14_DAY.md` and `docs/INCIDENTIQ_BUILD_GUIDE.md` with the implemented codebase (without altering any application code, evaluation results, or `TBD`/`TODO` placeholders).

## Per-File Changes

### `docs/01_PRD.md`
- **What changed:** Updated **FR-1**–**FR-14** and **Section 6 (Scope)** to reflect regex PII redaction (`guards.py`), deterministic zero-cost supervisor + 4 parallel branches (`metrics`, `logs`, `runbook`, `memory_agent`), lexical BM25 + Jaccard RAG, SSE on `GET /v1/incidents/{id}/stream`, 8 scenarios (`IncidentBench-mini`), `evals/redteam/run_redteam.py`, and 6 Next.js UI App Router pages (+ BFF proxy).
- **Why:** Moved deferred components (`30` scenarios, Postgres/`pgvector`/reranker, Redis, Presidio, Grafana, interactive UI attack/fault runners) into **Planned / Future work**.

### `docs/02_ARCHITECTURE.md`
- **What changed:** Updated Sequence diagram (`memory_agent` alongside the 3 specialists, `/stream` SSE), Layer responsibilities (Section 4), Run modes (Section 5: per-call `scenario_id` + `SCENARIO_ID` fallback), Key design decisions (Section 6: SQLite + BM25, DB-persisted approval token gating without LangGraph checkpointer/`interrupt()`, `nodes.py` LiteLLM + deterministic fallback), Failure handling (Section 7), and expanded **Planned / Future work** (Section 8).
- **Why:** Align architectural prose and diagrams with `incidentiq/agents/graph.py`, `nodes.py`, `mcp_client.py`, and `deploy/docker-compose.yml`.

### `docs/03_TECH_STACK.md`
- **What changed:** Updated Python requirement to `3.12+` (`pyproject.toml`), replaced Postgres/`pgvector`/Redis/Presidio/Grafana/`black`/`pre-commit`/`ragas` in the active core tables with the implemented SQLite + Okapi BM25/Jaccard + regex guardrails + custom FastMCP HTTP wrapper + `ruff`/`mypy`/`pytest` + Next.js 16 stack, noted unused pinned compatibility deps (`asyncpg`, `redis`, `scikit-learn`), and moved all deferred libraries/tools into **Section 7 (Planned / Future work)**.
- **Why:** Eliminate mismatch between active dependencies (`pyproject.toml`, `ui/package.json`, `.github/workflows/ci.yml`) and originally planned stack notes.

### `docs/04_DATABASE_DESIGN.md`
- **What changed:** Replaced the main schema DDL section with documentation of the **8 implemented SQLAlchemy/Alembic tables** (`incidents`, `approvals`, `llm_calls`, `tool_calls`, `guardrail_events`, `eval_runs`, `eval_results`, `incident_feedback`), added all 9 runtime `incidents.status` values (including `remediation_executed` and `rejected_by_human`), added an **Approval & Status Terminology Mapping** table (`approve`/`reject` vs `approved`/`rejected` vs `approved_and_executed`/`rejected` vs `remediation_executed`/`rejected_by_human`), added **Planned / Future work**, and preserved the original 16-table Postgres/`pgvector` DDL + hybrid SQL query under **Appendix: Target schema (not implemented)**.
- **Why:** `incidentiq/db/models.py` and `migrations/versions/` use SQLite/Postgres-compatible string IDs, JSON fields on `incidents`, and `incident_feedback`, whereas the original Postgres DDL was never migrated.

### `docs/05_API_SPEC.md`
- **What changed:** Documented exact implemented FastAPI routes (`GET /v1/scenarios`, `POST/GET /v1/incidents`, `GET /v1/incidents/{id}/stream`, `POST /v1/incidents/{id}/approval`, `POST /v1/incidents/{id}/feedback`, `GET /v1/evals`, `GET /v1/redteam`, `/health`, `/healthz`, `/readyz`), corrected the error code envelope table, removed the `/events` route and Redis check from `/readyz`, documented actual SSE event `type` names, added the **Approval Value Mapping** table, and moved unimplemented endpoints (`/v1/kb/*`, `/v1/evals/runs*`, `/v1/evals/compare`, `/v1/redteam/runs*`, `/v1/shop/faults*`, API `/metrics`, query pagination) into **Planned / Future work**.
- **Why:** Match `incidentiq/api/main.py` and `incidentiq/api/security.py` line-for-line.

### `docs/06_AGENT_AND_MCP_DESIGN.md`
- **What changed:** Synced `IncidentState` and `Hypothesis` with `incidentiq/agents/state.py` & `incidentiq/schemas/models.py`, updated the Graph Mermaid diagram and Nodes table (deterministic zero-cost `supervisor`, `memory_agent`, `budget_exceeded` routing, DB-backed HMAC approval without `interrupt()`), corrected inline prompts note (`nodes.py` vs empty `prompts/` dir), updated `tool_registry.py` allow-list key (`remediation`) and all 4 `remediation_server` tools (`restart_service`, `rollback_deploy`, `scale_up`, `review_config`) with `token`/`incident_id` + deprecation mapping from `propose_restart`/`propose_rollback`, replaced `audit_log` reference with `tool_calls`, and moved `llm/router|cache|cost`, `prompts/*.md`, and LangGraph `interrupt()` checkpointer to **Planned / Future work**.
- **Why:** Align agent graph, MCP tool contracts, and remediation naming with `graph.py`, `nodes.py`, `tool_registry.py`, and `mcp_servers/remediation/server.py`.

### `docs/07_EVALUATION_PLAN.md`
- **What changed:** Updated Section 2–5 & 7 to state `8` active scenarios (`6 dev` / `2 held_out` in `evals/splits.json`), `--repeats` default `1`, rule/citation scorers (`evals/scorers.py`), implemented ablations (`--ablate-memory`, `v2-live`, `evals/run_retrieval_eval.py`), and `.github/workflows/ci.yml` steps; moved the `30`-scenario expansion, cross-vendor LLM judge / RAGAS, hybrid vector/rerank sweeps, and `eval-full.yml` to **Planned / Future work**.
- **Why:** Match `evals/run_evals.py`, `evals/scorers.py`, `evals/splits.json`, and `.github/workflows/ci.yml`.

### `docs/08_SECURITY_THREAT_MODEL.md`
- **What changed:** Updated `T7` to reflect regex `PII_PATTERNS` redaction (`guards.py`), clarified `evals/redteam/run_redteam.py` writes `evals/results/redteam_summary.json` rather than SQL `redteam_cases` tables, and added **Planned / Future work** for Microsoft Presidio NER, classifier injection checks, and DB red-team persistence.
- **Why:** Align security documentation with `incidentiq/guardrails/guards.py` and `evals/redteam/run_redteam.py`.

### `docs/09_UI_DESIGN.md`
- **What changed:** Updated **Navigation**, **Security**, **Shop Control**, and **User flows** to reflect the 6 implemented Next.js App Router pages (`/`, `/incidents`, `/incidents/[id]`, `/evaluation`, `/security`, `/shop` + `/api/v1/[...path]` BFF) and 5 sidebar items (`AppSidebar.tsx`), read-only `/shop` topology view (`ShopView.tsx`), and moved standalone `Traces` sidebar link, interactive Security attack tester, and live `/shop` fault buttons/charts to **Planned / Future work**.
- **Why:** Reconcile original 4-page / interactive-mock text with `ui/app/` and `ui/components/`.

### `docs/10_DEPLOYMENT_AND_OPS.md`
- **What changed:** Listed all 3 Compose files (`deploy/docker-compose.yml`, `override.yml`, `monitoring.yml`), clarified `.env.example` Postgres/Redis templates vs SQLite defaults plus runtime env vars (`ENABLE_AGENT_MEMORY`, `MCP_MODE`, `WORKERS`, `API_INTERNAL_URL`, `NEXT_PUBLIC_API_URL`, `TRUSTED_PROXY_IPS`), replaced the outdated `/grafana/*` Caddy sketch and `pgvector`/`Grafana` ARM checks with the actual `deploy/Caddyfile` routes, and moved `eval-full.yml`, `deploy.yml`, AWS Terraform, Grafana, and API `/metrics` (`iiq_*`) to **Planned / Future work**.
- **Why:** Match `deploy/` configs and `.github/workflows/ci.yml`.

### `docs/11_ROADMAP_14_DAY.md`
- **What changed:** Updated Days 1–14 to describe the implemented v1 demo milestones accurately (in-memory `orders` dicts, 8 scenarios, BM25 + Jaccard, 4 parallel branches, `/stream`, DB-backed HMAC approval, regex PII, `ci.yml`, 6 Next.js routes, SQLite Compose deployment) and converted cut lines into **Cut lines & Planned / Future work**.
- **Why:** Remove contradictions between day-by-day checklist items and actual repo deliverables.

### `docs/INCIDENTIQ_BUILD_GUIDE.md`
- **What changed:** Aligned Days 0–14 and Cut lines with Python `3.12+`, `orders` in-memory dicts, 8 starter scenarios (`6 dev` / `2 held_out`), BM25 + Jaccard (`retrieval_summary.json`), `/v1/incidents/{id}/stream`, all 4 `remediation_server` tools, DB-persisted token gating, `ci.yml` (`ruff`, `mypy`, `pytest`, red-team, eval gate), 6 App Router pages, `scripts/backup_sqlite.sh`, and labeled deferred items (`pgvector`, `Redis`, `Presidio`, `Grafana`, `eval-full.yml`, `pre-commit`, 30 scenarios, Terraform) as **Planned / Future work**.
- **Why:** Ensure learners following the build guide see exact filenames, routes, and implemented behavior.

---

## Second Pass — Full Repo Sync ("Everything on Same Page; Code Wins Over Docs")

Updated the remaining doc files, subsystem READMEs, root [README.md](README.md), and [docs/COMPREHENSIVE_PROJECT_DETAILS.md](docs/COMPREHENSIVE_PROJECT_DETAILS.md) so every file agrees with the codebase:

- **`docs/02_ARCHITECTURE.md`:** Updated Component diagram (`EV[Eval harness] -->|in-process invoke| SUP`), documented that `evals/run_evals.py` bypasses HTTP API middleware, and noted `faults/injector.py` covers `db_pool`, `slow_query`, and `dependency_timeout` (+ `reset`).
- **`docs/06_AGENT_AND_MCP_DESIGN.md`:** Replaced Section 8 (`Confidence, groundedness, and abstention policy`) to match `nodes.py`/`guards.py`: mandatory `0.20` abstention when no metric/log evidence exists, citation-validity groundedness (`evidence_ids` membership check rather than per-claim judging), explicit `nodes.py` cost accounting, and multi-kind confidence capping moved to **Planned / Future work**.
- **`docs/07_EVALUATION_PLAN.md`:** Clarified the 8 existing scenarios are `3 easy, 3 medium, 2 ambiguous` (`0 hard` yet), aligned `groundedness` in `evals/scorers.py` to citation validity, documented in-process graph execution, and noted `v1-baseline.json`/`v2-optimized.json` predate commit `9ba61ac`'s synthetic-cost refresh.
- **`docs/11_ROADMAP_14_DAY.md` & `docs/INCIDENTIQ_BUILD_GUIDE.md`:** Aligned Day 2 fault injection scope (`db_pool`, `slow_query`, `dependency_timeout`, `reset`) and difficulty tally (`3 easy, 3 medium, 2 ambiguous, 0 hard`).
- **`evals/README.md`:** Updated difficulty tally (`3 Easy, 3 Medium, 2 Ambiguous, 0 Hard`), in-process `incident_graph.invoke` execution note, citation-validity groundedness definition, and flagged `v1-baseline.json`/`v2-optimized.json` costs as pre-`9ba61ac` synthetic values.
- **`ui/README.md`:** Added `ev_mem_*` episodes to `CitationSheet` and documented outcome verification feedback in `ReportView`/`AbstainedPanel`.
- **`README.md`:** Preserved CI-verified `<!-- BEGIN_EVAL_TABLES -->` / `<!-- BEGIN_RETRIEVAL_STATS -->` blocks (`update_readme_results.py --check`), added `ev_mem_*`, `0.20` zero-telemetry abstain, citation-validity groundedness, DB-persisted approval (no LangGraph `interrupt()`), in-process eval note, 3-fault CLI injector scope, post-`9ba61ac` cost note, and `shop/`-only `/metrics` clarification.
- **`docs/COMPREHENSIVE_PROJECT_DETAILS.md`:** Replaced the stale draft with a clean, code-verified summary matching `README.md` and `docs/01`–`11`.

---

## Items Requiring User Decision / Unresolved From Code Alone

1. **Unused Compatibility Artifacts:** `pyproject.toml` still pins `asyncpg`, `redis`, and `scikit-learn`; `incidentiq/agents/prompts/` is an empty directory; and `mcp_servers/validation.py` still includes `"redis"` in `ALLOWED_SERVICES`. Confirm whether to keep them for future expansion or prune them in a future code PR.
2. **Permissive Approval Input Validation:** `incidentiq/api/main.py:888` routes any `decision.lower() != "reject"` string into the approve path rather than rejecting unexpected strings.
3. **`scripts/update_readme_results.py` Table Source:** `scripts/update_readme_results.py` still pulls `mean_cost_usd` (`$0.0045` simulated) from pre-`9ba61ac` `v2-optimized.json` into `README.md`'s auto-generated table. Confirm whether `v2-optimized.json` should be re-run (or that column removed in `update_readme_results.py`) in a follow-up code PR.
4. **IncidentIQ API `/metrics`:** `deploy/Caddyfile:17` protects `/metrics*` with basic auth while only `shop/*` exposes `/metrics`. Confirm whether `iiq_*` API metrics remain on the backlog.

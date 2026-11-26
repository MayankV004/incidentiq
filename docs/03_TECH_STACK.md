# Tech Stack: IncidentIQ

Exact Python versions are pinned in `pyproject.toml` (`uv.lock`), and exact UI versions are pinned in `ui/package.json` (`ui/pnpm-lock.yaml`).

## 1. Core stack (Implemented)

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Language | Python 3.12+ | Modern typing, async support, ecosystem (`requires-python = ">=3.12"`) | none |
| API framework | FastAPI + Uvicorn (`--workers 1`) | Async, Pydantic native, SSE `StreamingResponse` support | Flask (less async) |
| Validation | Pydantic v2 | Structured LLM outputs, request/tool schemas | dataclasses |
| Agent orchestration | LangGraph | Stateful graphs, parallel fan-out, operator reducers | CrewAI, AutoGen, hand-rolled |
| LLM access | LiteLLM (`completion()` in `agents/nodes.py`) + deterministic fallback | Swap providers, unified token usage; works offline in CI | direct SDKs |
| Tool protocol | MCP Python SDK (`MCPServer` Streamable HTTP & in-process) | Industry standard protocol, enforced allow-lists | custom function calling only |
| MCP client glue | Custom wrapper (`incidentiq/agents/mcp_client.py`) using `mcp.ClientSession` | Enforces per-agent tool allow-lists across in-process and HTTP modes | `langchain-mcp-adapters` |
| Database | SQLite (demo default) / SQLAlchemy 2.1 + Alembic (Postgres-compatible via `psycopg`) | Zero-dependency single-worker demo with migration compatibility | dedicated external DB in demo |
| Retrieval (RAG & Memory) | In-memory Okapi BM25 + token Jaccard + service metadata boost (`rag/engine.py`, `rag/memory.py`) | Zero external downloads, sub-millisecond startup on ARM64 | Postgres + `pgvector` (deferred) |
| Rate limiting & Spend caps | Custom middleware (`api/security.py`) + SQLite persisted daily cost query | Trusted-proxy IP limits and persistent spend caps without Redis | `slowapi` / Redis |

## 2. Observability and evals (Implemented)

| Need | Choice | Notes |
|---|---|---|
| LLM tracing | Langfuse (optional via env keys) | Traces LangGraph and LiteLLM calls when credentials are set |
| Shop metrics | Prometheus + `prometheus_client` | Exposed on `/metrics` in `shop/common/telemetry.py`; scraped via optional `deploy/docker-compose.monitoring.yml` |
| Eval metrics | Custom scorers (`evals/scorers.py`) + retrieval eval (`evals/run_retrieval_eval.py`) | Exact-match accuracy, citation groundedness, abstention, cost, latency, `hit@3` / `MRR` |
| Logging | `structlog` (JSON queue listener) + Python `logging` | Shop emits structured JSON logs to `logs/<service>.log` |

## 3. Guardrails and security (Implemented)

| Need | Choice |
|---|---|
| PII detection | Regex patterns (`PII_PATTERNS` in `incidentiq/guardrails/guards.py`) for emails, phones, SSNs, cards, Bearer/API keys |
| Injection & leakage scanning | Heuristic signature matching (`INJECTION_SIGNATURES`) + prompt/secret leakage scan (`scan_prompt_leakage`) |
| Capability tokens | HMAC-SHA256 single-use tokens (`incidentiq/security/tokens.py`) bound to incident, action, and target |
| Secrets | `.env` files, never committed, `.env.example` provided; fail-fast startup checks for `API_KEY` & `APPROVAL_TOKEN_SECRET` |

## 4. Frontend (Implemented)

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Framework | Next.js 16 (App Router) + React 19 + TypeScript | Production stack, server-side BFF `/api/v1/[...path]` proxy keeps `API_KEY` secret | Streamlit, Vite SPA |
| Styling & Components | Tailwind CSS + Lucide Icons | Fast, responsive, accessible dark/light SRE dashboard | Plain CSS, Material UI |
| Real-time streaming | Native SSE (`EventSource`) | Streams timeline updates without WebSocket overhead | WebSockets |

## 5. DevOps (Implemented)

| Need | Choice |
|---|---|
| Containers | Docker, Docker Compose (`deploy/docker-compose.yml`, `override.yml`, `monitoring.yml`) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| Reverse proxy and HTTPS | Caddy (`caddy:2-alpine` with SSE `flush_interval -1`, security headers, basic auth on `/metrics*` & `/admin*`) |
| Code quality (CI) | `ruff check .`, `mypy .`, `pytest`, UI `pnpm lint` + `tsc --noEmit` (`graph.py` also carries a `# pyrefly: ignore` IDE hint) |

## 6. Dependencies (`pyproject.toml` & `ui/package.json`)

Pinned in `pyproject.toml` (installed via `uv sync --frozen`):
- Core API & Agents: `fastapi`, `uvicorn[standard]`, `pydantic`, `httpx`, `langgraph`, `langchain`, `langchain-core`, `langchain-mcp-adapters`, `mcp`, `litellm`, `langfuse`
- Data & Telemetry: `sqlalchemy`, `alembic`, `psycopg[binary]`, `asyncpg`, `redis`, `prometheus-client`, `psutil`, `structlog`, `scikit-learn` (note: `asyncpg`, `redis`, and `scikit-learn` are pinned compatibility packages not exercised in the SQLite/BM25 runtime)
- QA: `pytest`, `ruff`, `mypy`

Frontend (`ui/package.json`): `next`, `react`, `react-dom`, `typescript`, `tailwindcss`, `lucide-react`.

## 7. Planned / Future work (Original target stack not yet enabled)

The following items from the target architecture are deferred out of the single-node demo:
- **Database & Hybrid Vector RAG:** PostgreSQL 16 (`postgresql+psycopg://`), `pgvector` HNSW + `tsvector` hybrid search, `sentence-transformers` embeddings (`bge-small` / `bge-base`), `bge-reranker` cross-encoder reranking.
- **Caching & Queues:** Redis exact-match LLM cache and `slowapi` / Redis token-bucket rate limiting.
- **Guardrails & Evals:** Microsoft Presidio NER (`presidio-analyzer`, `presidio-anonymizer`), `ragas` / `deepeval` faithfulness scorers, separate cross-vendor `MODEL_JUDGE` LLM judge pass, and `recharts` analytics charts.
- **Observability & Ops:** Grafana dashboards, IncidentIQ API `/metrics` (`iiq_*`) exporter, AWS (EC2/ECS + RDS) Terraform modules, `black`, and `pre-commit` hooks.
- **Model routing:** Dedicated small vs strong multi-tier router (`MODEL_SMALL`, `MODEL_STRONG`, `MODEL_JUDGE`); currently only `MODEL_STRONG` is invoked when an LLM key is set, with deterministic fallback otherwise.

## 8. Compatibility notes

- Oracle Ampere VMs are ARM64: confirm every Docker image has an `arm64` build (`deploy/Dockerfile.python` uses `python:3.12-slim`, `deploy/Dockerfile.ui` uses `node:22-alpine`, `caddy:2-alpine` supports `arm64`).
- If enabling `sentence-transformers` in future hybrid RAG work on ARM CPU, pre-embed the knowledge base at build time and keep the embedding model identical between ingestion and query.

# Tech Stack: IncidentIQ

Pin exact versions in `requirements.txt` at build time. Before integrating each library, read its current documentation, since MCP, LangGraph and tracing APIs evolve quickly.

## 1. Core stack

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Language | Python 3.11+ | Ecosystem for LLMs, async support | none |
| API framework | FastAPI + Uvicorn | Async, Pydantic native, SSE support | Flask (less async) |
| Validation | Pydantic v2 | Structured LLM outputs, schemas | dataclasses |
| Agent orchestration | LangGraph | Stateful graphs, parallel nodes, checkpoints, interrupts | CrewAI, AutoGen, hand-rolled |
| LLM access | LiteLLM (or thin wrapper) | Swap providers, unified cost data | direct SDKs |
| Tool protocol | MCP Python SDK (FastMCP) | Industry standard, requested in JDs | custom function calling only |
| MCP client glue | langchain-mcp-adapters | Connect MCP tools to LangGraph | manual client |
| Database | PostgreSQL 16 | Relational data, JSONB | SQLite (no pgvector) |
| Vector search | pgvector | One DB, hybrid with full-text | Qdrant, Chroma |
| Cache and rate limit | Redis | Fast, common | in-memory |
| Embeddings | bge-small or bge-base (sentence-transformers) | Free, local, good quality | API embeddings |
| Reranker | bge-reranker (local cross-encoder) | Improves precision | Cohere rerank (paid) |

## 2. Observability and evals

| Need | Choice | Notes |
|---|---|---|
| LLM tracing | Langfuse | Open source, self-host or cloud |
| System metrics | Prometheus + prometheus_client | Also scrapes the demo shop |
| Dashboards | Grafana | One dashboard for AI system health |
| Eval metrics | RAGAS or DeepEval plus custom scorers | Faithfulness and custom accuracy |
| LLM judge | Strong model, different vendor from agent model | Reduces self-preference bias |
| Logging | structlog (JSON) | Same format as the shop |

## 3. Guardrails and security

| Need | Choice |
|---|---|
| PII detection | Microsoft Presidio plus regex |
| Injection scanning | Pattern rules plus a small classifier prompt (optionally a dedicated open-source detector) |
| Secrets | `.env` files, never committed, `.env.example` provided |
| Rate limiting | slowapi or Redis token bucket |

## 4. Frontend

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Framework | Next.js (App Router) + TypeScript | Modern production-ready stack, strict type-safety aligned with Pydantic models, server/client components, standard industry practice | Streamlit (inflexible styling/state), Vite SPA |
| Styling & Components | Tailwind CSS + Lucide Icons (shadcn/ui style) | Fast, responsive, accessible, information-dense dark/light SRE dashboard | Plain CSS, Material UI |
| Real-time streaming | Native SSE (`EventSource` / `fetch` ReadableStream) | Zero extra dependencies, handles streaming timeline smoothly | WebSockets |
| Data visualization | Recharts | Composable React charts for latency, error rate, and eval benchmarks | Chart.js |

## 5. DevOps

| Need | Choice |
|---|---|
| Containers | Docker, Docker Compose |
| CI | GitHub Actions |
| Reverse proxy and HTTPS | Caddy |
| Cloud (primary) | Oracle Cloud Always Free ARM VM (verify ARM64 image support) |
| Cloud (optional) | AWS (EC2 or ECS + RDS) via Terraform |
| Code quality | ruff, black, mypy, pytest, pre-commit |

## 6. Models (provider-agnostic)

| Role | Tier | Example class |
|---|---|---|
| Routing, extraction, summaries, guard checks | Small and fast | Flash, Haiku or mini class |
| Root-cause reasoning, final report | Stronger mid-tier | Pro or Sonnet class |
| Eval judge | Strong, different vendor | any top-tier model |

Check current prices and free-tier limits before choosing. Evals multiply calls (30 scenarios x 3 runs x several steps), so cache and budget.

## 7. Dependency sketch

```
# Backend (Python requirements.txt)
fastapi, uvicorn[standard], pydantic>=2, httpx, sse-starlette
langgraph, langchain-core, langchain-mcp-adapters, mcp
litellm, langfuse
sqlalchemy[asyncio], asyncpg, alembic, pgvector
redis, prometheus-client, structlog
sentence-transformers
presidio-analyzer, presidio-anonymizer
ragas (or deepeval), pandas
pytest, pytest-asyncio, ruff, black, mypy

# Frontend (ui/package.json)
next, react, react-dom, typescript, @types/react, @types/node
tailwindcss, postcss, autoprefixer, lucide-react, recharts
```

## 8. Compatibility notes

- Oracle Ampere VMs are ARM64: confirm every Docker image has an `arm64` build.
- sentence-transformers on ARM CPU works but is slower; pre-embed the knowledge base at build time.
- Keep embedding model identical between ingestion and query.

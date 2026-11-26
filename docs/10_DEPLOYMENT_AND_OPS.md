# Deployment and Operations: IncidentIQ

## 1. Environments

| Env | Purpose | How |
|---|---|---|
| local | Development | `docker compose up` |
| ci | Tests and eval subset | GitHub Actions |
| prod-demo | Public demo | Oracle Cloud VM with Docker Compose and Caddy |
| aws (optional) | Terraform showcase | EC2 or ECS + RDS |

## 2. Deployed Demo Stack (`deploy/docker-compose.yml`)

Three Compose files exist under `deploy/`:
1. `deploy/docker-compose.yml`: base production/demo stack (SQLite `/data/incidentiq.db`, single Uvicorn worker `--workers 1`, without Postgres, Redis, Prometheus, or Grafana containers).
2. `deploy/docker-compose.override.yml`: local dev override binding internal service ports to `127.0.0.1`.
3. `deploy/docker-compose.monitoring.yml`: optional live telemetry overlay adding Prometheus (`prom/prometheus:v2.55.1` on `127.0.0.1:9090`) and setting `DATA_MODE=live`.

| Service | Image / Dockerfile | Port (internal) | Notes |
|---|---|---|---|
| `gateway`, `orders`, `payments`, `fake-external` | `deploy/Dockerfile.python` | 8001–8004 | Internal demo shop microservices |
| `mcp-metrics`, `mcp-logs`, `mcp-remediation` | `deploy/Dockerfile.python` | 9101–9103 | Internal FastMCP Streamable HTTP servers |
| `incidentiq-api` | `deploy/Dockerfile.python` | 8000 | Single-worker FastAPI + SQLite (`iiq_data:/data`) |
| `ui` | `deploy/Dockerfile.ui` (`node:22-alpine`) | 3000 | Next.js 16 + BFF `/api/v1` proxy (injects `API_KEY` server-side) |
| `caddy` | `caddy:2-alpine` | 80, 443 | Automatic HTTPS (`DEMO_DOMAIN`), HSTS/headers, 64KB body cap, basic auth on `/metrics*` & `/admin*`, `flush_interval -1` for SSE |

Only Caddy exposes host ports `80` and `443` in `deploy/docker-compose.yml`. All Docker services define healthchecks, `restart: unless-stopped`, memory/CPU limits, and JSON log rotation (`max-size: 10m`, `max-file: 3`).

To combine the optional Prometheus monitoring overlay (`deploy/docker-compose.monitoring.yml` + `deploy/prometheus.yml`):
```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.monitoring.yml --env-file .env up -d --build
```

## 3. Environment variables (`.env.example`)

`.env.example` keeps the multi-node `DATABASE_URL` / `REDIS_URL` template placeholders alongside runtime security/budget settings. In local runs without Postgres, `incidentiq/db/session.py` defaults to `sqlite:///incidentiq.db`, and `deploy/docker-compose.yml` sets `DATABASE_URL=sqlite:////data/incidentiq.db` (omitting Redis).

```
# LLM Provider Configuration
LLM_API_KEY_PRIMARY=
LLM_API_KEY_JUDGE=
MODEL_SMALL=
MODEL_STRONG=
MODEL_JUDGE=

# Operational & Safety Caps
DAILY_COST_CAP_USD=2.00
INCIDENT_BUDGET_USD=0.05
MAX_AGENT_STEPS=12
ABSTAIN_THRESHOLD=0.5
GROUND_THRESHOLD=0.85

# Data & Persistence
DATABASE_URL=postgresql+asyncpg://iiq:password@localhost:5432/incidentiq
REDIS_URL=redis://localhost:6379/0
DATA_MODE=live            # live | replay (Compose defaults to replay unless monitoring overlay is enabled)
SCENARIO_ID=

# Observability
LANGFUSE_HOST=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# Security & Approvals
API_KEY=
APPROVAL_TOKEN_SECRET=
TRUSTED_PROXY_IPS=

# Public Ingress / Caddy TLS & Auth
DEMO_DOMAIN=
METRICS_BASIC_AUTH_USER=
METRICS_BASIC_AUTH_HASH=
```
Optional runtime flags read in code: `ENABLE_AGENT_MEMORY=true`, `MCP_MODE=inprocess|http`, `WORKERS=1`, `API_INTERNAL_URL`, `NEXT_PUBLIC_API_URL` (kept empty so UI requests go through `/api/v1/*`). Never commit `.env`.

## 4. Oracle Cloud deployment (primary)

1. **VM:** create an Always Free Ampere A1 instance (ARM64, Ubuntu LTS); allocate generous RAM (the free tier allows up to 4 OCPU and 24 GB total, check current limits).
2. **Network:** open TCP 80 and 443 in the VCN security list **and** in the VM firewall (`iptables`/`ufw`; Oracle images often block ports by default).
3. **Install:** Docker Engine and the Compose plugin.
4. **ARM check:** confirm every image supports `linux/arm64` (`python:3.12-slim`, `node:22-alpine`, `caddy:2-alpine`, `prom/prometheus:v2.55.1`; verify custom builds with `docker buildx`).
5. **Deploy:** clone repo, create `.env` (including required `API_KEY`, `APPROVAL_TOKEN_SECRET`, `DEMO_DOMAIN`, `METRICS_BASIC_AUTH_USER`, `METRICS_BASIC_AUTH_HASH`), run `docker compose -f deploy/docker-compose.yml up -d --build --wait`.
6. **Domain and HTTPS:** point a domain or free subdomain to the VM IP; Caddy (`{$DEMO_DOMAIN:localhost}`) obtains certificates automatically.
7. **BM25 Knowledge Base:** `incidentiq/rag/engine.py` indexes markdown runbooks/postmortems in memory in milliseconds without heavy embedding downloads.
8. **Harden:** SSH keys only, disable password login, fail2ban optional, automatic security updates, basic auth on `/metrics*` and `/admin*`.
9. **Backups:** nightly `scripts/backup_sqlite.sh /data/incidentiq.db` (or host-mounted volume backup) to object storage or a local rotated folder.

### Implemented `deploy/Caddyfile` routes

- Basic auth protects `/metrics`, `/metrics/*`, `/admin`, and `/admin/*`.
- `flush_interval -1` proxies `/v1/incidents/*/stream` (API) and `/api/v1/incidents/*/stream` (UI BFF).
- `/v1/*`, `/healthz`, and `/readyz` proxy to `incidentiq-api:8000`; all remaining routes proxy to `ui:3000`.
- Sets HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, strips `Server`, and enforces a `64KB` max request body.

## 5. CI/CD (GitHub Actions)

| Workflow | Status | Steps |
|---|---|---|
| `.github/workflows/ci.yml` | Implemented | Checkout, `uv` + Python `3.12`, `uv sync --frozen`, `ruff check .`, `mypy .`, `scripts/update_readme_results.py --check`, `pytest`, `evals/redteam/run_redteam.py`, `evals/run_evals.py --name ci-eval`; UI job (`pnpm install --frozen-lockfile`, `pnpm lint`, `tsc --noEmit`) |
| `eval-full.yml` | Planned / Future work | Manual/nightly full benchmark, upload results artifact, post summary |
| `deploy.yml` | Planned / Future work | Build/push images, SSH to VM, `docker compose pull && up -d`, smoke test (`GET /readyz` + one replay incident) |

## 6. Monitoring and telemetry (Implemented) & Planned / Future work

**Implemented telemetry:**
- Shop services expose Prometheus `/metrics` (`shop_requests_total`, `shop_request_duration_seconds`, `shop_errors_total`, `shop_memory_mb`, `shop_db_pool_in_use`, `shop_cache_hit_rate` in `shop/common/telemetry.py`), scraped by the optional `deploy/docker-compose.monitoring.yml` overlay (`deploy/prometheus.yml`).
- IncidentIQ API persists incident, LLM, tool, and guardrail telemetry to SQLite and attaches optional Langfuse callbacks when `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are configured.

**Planned / Future work (not yet implemented):**
- **IncidentIQ API `/metrics` endpoint (`iiq_*`):** `iiq_incidents_total{status}`, `iiq_incident_latency_seconds`, `iiq_incident_cost_usd`, `iiq_llm_calls_total{model,purpose}`, `iiq_llm_tokens_total{model,direction}`, `iiq_cache_hits_total`, `iiq_guardrail_events_total{type,action}`, `iiq_abstentions_total`, `iiq_tool_calls_total{server,tool,allowed}`.
- **Grafana dashboards & `/grafana/*` Caddy route:** panels for incidents per status, p50/p95 latency, cost per incident, daily spend vs cap, guardrail events, abstention rate, tool errors; alerts on daily spend > 80% of cap, error rate threshold, and MCP server down.
- **AWS / Terraform (`deploy/terraform/`):** `network` (VPC/subnets/SGs), `compute` (EC2/ECS Fargate), `database` (RDS Postgres with `pgvector`), `secrets` (SSM/Secrets Manager), and billing alarm.

## 8. Operations runbook (short)

| Situation | Action |
|---|---|
| Daily cap reached | Public endpoint returns 429; raise cap in `.env` and restart API, or wait |
| LLM provider outage | Router falls back to secondary model; if both down, incidents end as `failed` with clear message |
| MCP server down | `/readyz` fails; restart container; agents report "tool unavailable" evidence |
| Disk filling | Rotate shop logs, prune Docker images, truncate demo incidents |
| Bad deploy | Roll back to previous image tag |

## 9. Cost control checklist

- Hard spending limits on LLM API keys.
- Daily cap and per-incident budget in code.
- Public endpoints rate limited; demo UI requires API key or gated demo mode.
- Cache LLM and tool calls in eval runs.
- Billing alarms on AWS if used.

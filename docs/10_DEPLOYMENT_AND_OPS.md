# Deployment and Operations: IncidentIQ

## 1. Environments

| Env | Purpose | How |
|---|---|---|
| local | Development | `docker compose up` |
| ci | Tests and eval subset | GitHub Actions |
| prod-demo | Public demo | Oracle Cloud VM with Docker Compose and Caddy |
| aws (optional) | Terraform showcase | EC2 or ECS + RDS |

## 2. Deployed Demo Stack (`deploy/docker-compose.yml`)

For the single-node cost-capped demo, the compose stack runs SQLite (`/data/incidentiq.db`, single Uvicorn worker `--workers 1`) without separate Postgres, Redis, Prometheus, or Grafana containers:

| Service | Image / Dockerfile | Port (internal) | Notes |
|---|---|---|---|
| `gateway`, `orders`, `payments`, `fake-external` | `deploy/Dockerfile.python` | 8001–8004 | Internal demo shop microservices |
| `mcp-metrics`, `mcp-logs`, `mcp-remediation` | `deploy/Dockerfile.python` | 9101–9103 | Internal FastMCP Streamable HTTP servers |
| `incidentiq-api` | `deploy/Dockerfile.python` | 8000 | Single-worker FastAPI + SQLite (`iiq_data:/data`) |
| `ui` | `deploy/Dockerfile.ui` (`node:22-alpine`) | 3000 | Next.js 16 + BFF `/api/v1` proxy (injects `API_KEY` server-side) |
| `caddy` | `caddy:2-alpine` | 80, 443 | Automatic HTTPS (`DEMO_DOMAIN`), HSTS/headers, 64KB body cap, basic auth on `/metrics*` & `/admin*`, `flush_interval -1` for SSE |

Only Caddy exposes host ports `80` and `443`. All Docker services define healthchecks, `restart: unless-stopped`, memory/CPU limits, and JSON log rotation (`max-size: 10m`, `max-file: 3`).

## 3. Environment variables (`.env.example`)

```
# LLM
LLM_API_KEY_PRIMARY=
LLM_API_KEY_JUDGE=
MODEL_SMALL=
MODEL_STRONG=
MODEL_JUDGE=
DAILY_COST_CAP_USD=2
INCIDENT_BUDGET_USD=0.05
MAX_AGENT_STEPS=12
ABSTAIN_THRESHOLD=0.5
GROUND_THRESHOLD=0.85

# Data
DATABASE_URL=postgresql+asyncpg://iiq:***@postgres:5432/incidentiq
REDIS_URL=redis://redis:6379/0
DATA_MODE=live            # live | replay
SCENARIO_ID=

# Observability
LANGFUSE_HOST=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# Security
API_KEY=
APPROVAL_TOKEN_SECRET=
```
Never commit `.env`. Add secret scanning to CI.

## 4. Oracle Cloud deployment (primary)

1. **VM:** create an Always Free Ampere A1 instance (ARM64, Ubuntu LTS); allocate generous RAM (the free tier allows up to 4 OCPU and 24 GB total, check current limits).
2. **Network:** open TCP 80 and 443 in the VCN security list **and** in the VM firewall (`iptables`/`ufw`; Oracle images often block ports by default).
3. **Install:** Docker Engine and the Compose plugin.
4. **ARM check:** confirm every image supports `linux/arm64` (pgvector, Langfuse, Prometheus, Grafana and Caddy do; verify your own builds with `docker buildx`).
5. **Deploy:** clone repo, create `.env` (including required `API_KEY`, `APPROVAL_TOKEN_SECRET`, `DEMO_DOMAIN`, `METRICS_BASIC_AUTH_USER`, `METRICS_BASIC_AUTH_HASH`), run `docker compose -f deploy/docker-compose.yml up -d --build --wait`.
6. **Domain and HTTPS:** point a domain or free subdomain to the VM IP; Caddy (`{$DEMO_DOMAIN:localhost}`) obtains certificates automatically.
7. **BM25 Knowledge Base:** `incidentiq/rag/engine.py` indexes markdown runbooks/postmortems in memory in milliseconds without heavy embedding downloads.
8. **Harden:** SSH keys only, disable password login, fail2ban optional, automatic security updates, basic auth on `/metrics*` and `/admin*`.
9. **Backups:** nightly `scripts/backup_sqlite.sh /data/incidentiq.db` (or host-mounted volume backup) to object storage or a local rotated folder.

### Caddyfile sketch

```
demo.example.com {
  encode gzip
  handle /v1/* { reverse_proxy incidentiq-api:8000 }
  handle /grafana/* { basicauth { admin <hash> } reverse_proxy grafana:3000 }
  handle { reverse_proxy ui:3000 }
}
```

## 5. AWS deployment (optional)

Terraform modules: `network` (VPC, subnets, security groups), `compute` (EC2 with Docker, or ECS Fargate service), `database` (RDS Postgres with pgvector enabled), `secrets` (SSM Parameter Store or Secrets Manager). Keep AWS as a second target to showcase Terraform; do not block the main project on it. Watch costs and set a billing alarm.

## 6. CI/CD (GitHub Actions)

| Workflow | Steps |
|---|---|
| `ci.yml` (PR) | checkout, setup Python, install, ruff and mypy, pytest (unit and MCP contract), start services, eval subset with gate, dependency and secret scan |
| `eval-full.yml` (manual/nightly) | full benchmark, upload results artifact, post summary |
| `deploy.yml` (main) | build and push images, SSH to VM, `docker compose pull && up -d`, run smoke test |

Smoke test: `GET /readyz` then one replay incident must complete.

## 7. Monitoring and alerting of IncidentIQ itself

Prometheus metrics exposed by the API:

| Metric | Type |
|---|---|
| `iiq_incidents_total{status}` | counter |
| `iiq_incident_latency_seconds` | histogram |
| `iiq_incident_cost_usd` | histogram |
| `iiq_llm_calls_total{model,purpose}` | counter |
| `iiq_llm_tokens_total{model,direction}` | counter |
| `iiq_cache_hits_total` | counter |
| `iiq_guardrail_events_total{type,action}` | counter |
| `iiq_abstentions_total` | counter |
| `iiq_tool_calls_total{server,tool,allowed}` | counter |

Grafana panels: incidents per status, p50/p95 latency, cost per incident, daily spend vs cap, guardrail events, abstention rate, tool errors. Alerts: daily spend above 80% of cap, error rate above threshold, MCP server down.

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

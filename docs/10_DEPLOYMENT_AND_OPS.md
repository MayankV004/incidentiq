# Deployment and Operations: IncidentIQ

## 1. Environments

| Env | Purpose | How |
|---|---|---|
| local | Development | `docker compose up` |
| ci | Tests and eval subset | GitHub Actions |
| prod-demo | Public demo | Oracle Cloud VM with Docker Compose and Caddy |
| aws (optional) | Terraform showcase | EC2 or ECS + RDS |

## 2. Services (Docker Compose)

| Service | Image or build | Port (internal) | Notes |
|---|---|---|---|
| gateway, orders, payments, fake-external | build `shop/` | 8001-8004 | Demo shop |
| traffic-gen | build `faults/` | none | Steady baseline traffic |
| postgres | pgvector image | 5432 | Shop DB and app DB (separate databases) |
| redis | redis:7 | 6379 | Cache, rate limit |
| prometheus | prom/prometheus | 9090 | Scrapes shop and IncidentIQ |
| grafana | grafana/grafana | 3000 | Dashboards |
| langfuse (+ its DB) | langfuse | 3001 | Or use Langfuse cloud |
| mcp-metrics, mcp-logs, mcp-remediation | build `mcp_servers/` | 9101-9103 | Internal only |
| incidentiq-api | build `incidentiq/` | 8000 | FastAPI |
| ui | build `ui/` | 3000 | Next.js + TypeScript (Node 20 Alpine / standalone) |
| caddy | caddy:2 | 80, 443 | Only public entry point (prod) |

Only Caddy is exposed publicly. Everything else stays on the internal Docker network.

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
5. **Deploy:** clone repo, create `.env`, run `docker compose -f deploy/docker-compose.prod.yml up -d --build`.
6. **Domain and HTTPS:** point a domain or free subdomain to the VM IP; Caddy obtains certificates automatically.
7. **Pre-embed KB** at build time to avoid slow first requests on ARM CPU.
8. **Harden:** SSH keys only, disable password login, fail2ban optional, automatic security updates, basic auth on Grafana and Langfuse.
9. **Backups:** nightly `pg_dump` to object storage or a local rotated folder.

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

# IncidentIQ: Documentation Index

IncidentIQ is a multi-agent AI on-call assistant. When a system alert fires, LangGraph agents investigate using MCP tools (metrics, logs) and RAG (runbooks, postmortems), then produce a cited root-cause report. A human approves any remediation. A reliability layer (evals, guardrails, tracing, cost control) surrounds the agents.

## Documents

| # | File | Purpose |
|---|------|---------|
| 01 | [PRD](01_PRD.md) | Problem, users, scope, requirements, success metrics |
| 02 | [Architecture](02_ARCHITECTURE.md) | Components, data flow, sequence, design decisions |
| 03 | [Tech Stack](03_TECH_STACK.md) | Every technology, why chosen, alternatives |
| 04 | [Database Design](04_DATABASE_DESIGN.md) | SQLite (single-worker demo) & Postgres-compatible schema, ER diagram, migrations |
| 05 | [API Spec](05_API_SPEC.md) | REST and streaming endpoints, schemas, errors |
| 06 | [Agent and MCP Design](06_AGENT_AND_MCP_DESIGN.md) | LangGraph state, nodes, prompts contract, MCP tools |
| 07 | [Evaluation Plan](07_EVALUATION_PLAN.md) | Benchmark, metrics, methodology, CI gate |
| 08 | [Security and Threat Model](08_SECURITY_THREAT_MODEL.md) | Threats, guardrails, red-team suite |
| 09 | [UI Design](09_UI_DESIGN.md) | Pages, wireframes, components, user flows |
| 10 | [Deployment and Ops](10_DEPLOYMENT_AND_OPS.md) | Docker, Oracle Cloud, AWS, CI/CD, monitoring |
| 11 | [14-Day Roadmap](11_ROADMAP_14_DAY.md) | Day-by-day plan with done-when criteria |

## Subsystem Guides & Benchmarks

| Subsystem | Link | Description |
|---|---|---|
| **Evaluation Suite** | [evals/README.md](../evals/README.md) | `IncidentBench-mini` results, exact metric formulas, calculation walkthrough, and red-team tests |
| **Model Context Protocol** | [mcp_servers/README.md](../mcp_servers/README.md) | FastMCP metrics, logs, and remediation servers with security quarantine |
| **Target Shop Services** | [shop/README.md](../shop/README.md) | E-commerce microservices, Prometheus telemetry, and chaos endpoints |
| **Knowledge Base** | [knowledge/README.md](../knowledge/README.md) | Operational runbooks, postmortems, and in-memory BM25 retrieval |
| **Frontend UI** | [ui/README.md](../ui/README.md) | Next.js 16 App Router, Turbopack, and SSE live timeline dashboard |

## Reading order

PRD, Architecture, Tech Stack, then Database, API and Agent/MCP design while building. Evaluation and Security are written before coding the agents so that tests drive the work.

## Conventions

- Code: Python 3.12+, type hints, Pydantic v2, async I/O.
- Every agent output is structured (Pydantic), never free text.
- Every claim in a report must cite an evidence id.
- Versions are pinned. Check current library docs before integrating, because MCP and LangGraph APIs change quickly.

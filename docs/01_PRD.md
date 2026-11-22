# Product Requirements Document (PRD): IncidentIQ

| Field | Value |
|---|---|
| Version | 1.0 |
| Owner | Mayank |
| Timeline | 14 days (Nov 17 to Nov 30, 2026) |
| Status | Draft for build |

## 1. Problem statement

On-call engineers lose time during incidents by manually correlating metrics, logs and runbooks. LLM agents can help, but teams hesitate to trust them because agents hallucinate, can be manipulated by untrusted log content, cost money per call, and are rarely measured. IncidentIQ demonstrates a triage agent that is evaluated, secured, observable and cost-controlled.

## 2. Goals

1. Produce a correct, cited root-cause hypothesis for common incident types.
2. Abstain honestly when evidence is insufficient.
3. Never take action without human approval.
4. Prove quality with an automated benchmark and CI regression gate.
5. Demonstrate measurable cost and latency optimization.
6. Resist prompt injection from untrusted logs and documents.

## 3. Non-goals

- Replacing human on-call engineers or acting autonomously in production.
- Supporting arbitrary real production infrastructure (v1 targets the bundled demo shop and replayed scenarios).
- Multi-tenant SaaS features (auth beyond basic, billing, orgs).
- Training or fine-tuning models.

## 4. Users and personas

| Persona | Need |
|---|---|
| On-call engineer (primary) | Fast, trustworthy first-pass diagnosis with evidence |
| Engineering lead | Confidence that the AI is measured and safe |
| Recruiter or reviewer (secondary) | Quickly see skills: agents, RAG, MCP, evals, security, cost |

## 5. User stories

| ID | Story | Priority |
|---|---|---|
| US-1 | As an on-call engineer, I submit an alert and get a root-cause report with cited evidence | P0 |
| US-2 | I watch agent progress live so I know what it is checking | P0 |
| US-3 | I approve or reject any proposed remediation | P0 |
| US-4 | I see "not confident, escalating" instead of a guess when evidence is weak | P0 |
| US-5 | I can see cost and latency of each incident | P1 |
| US-6 | I can inject a fault in the demo shop and watch IncidentIQ respond | P1 |
| US-7 | I can view benchmark results and compare versions | P1 |
| US-8 | I can view red-team results and block rate | P1 |
| US-9 | I can open full traces of any run | P2 |

## 5.1 Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | Accept alerts via REST (`POST /v1/incidents`) |
| FR-2 | Redact PII and scan for injection before any model call |
| FR-3 | Supervisor selects and runs metrics, logs and runbook agents in parallel |
| FR-4 | Agents access data only through MCP tools with per-agent allow-lists |
| FR-5 | Hybrid RAG with reranking over runbooks and postmortems, with citations |
| FR-6 | Root-cause agent returns category, service, confidence, reasoning and evidence ids |
| FR-7 | Output guard verifies groundedness; unsupported claims are removed or trigger abstention |
| FR-8 | Remediation is dry-run only and requires explicit human approval |
| FR-9 | Stream progress events to the UI (SSE) |
| FR-10 | Record tokens, cost and latency per LLM call and per incident |
| FR-11 | Eval harness runs all scenarios in replay mode and stores versioned results |
| FR-12 | CI fails if accuracy or groundedness regress below thresholds |
| FR-13 | Red-team suite of 20 attacks with stored outcomes |
| FR-14 | Per-incident budget cap stops runaway loops |

## 5.2 Non-functional requirements

| Area | Target |
|---|---|
| Latency | p95 end-to-end under 15 s baseline, under 8 s after optimization (targets, to be measured) |
| Cost | Cost per incident reduced at least 40% vs baseline |
| Accuracy | Root-cause accuracy at least 80% on benchmark after optimization (target) |
| Groundedness | At least 90% of claims supported by cited evidence (target) |
| Security | Block at least 85% of red-team attacks; 0 unapproved actions |
| Reliability | Graceful degradation if a model or tool fails (retry, fallback model, abstain) |
| Reproducibility | Evals deterministic via replay mode and cached tool outputs |
| Observability | Every run traceable end to end |

Targets are goals, not promises. Report what you actually measure.

## 6. Scope

**In scope (v1):** demo shop, six fault types (about 30 scenarios), three MCP servers, hybrid RAG, LangGraph agents, guardrails, eval harness, tracing, four UI pages, Docker deployment.

**Out of scope (v1):** real cloud provider integrations, Slack or PagerDuty connectors, autonomous remediation, fine-tuning, multi-user auth.

## 7. Success metrics

| Metric | Baseline | Target |
|---|---|---|
| Root-cause accuracy | measured Day 9 | at least 80% |
| Groundedness | measured Day 9 | at least 90% |
| Correct abstentions | measured Day 9 | at least 75% on ambiguous cases |
| Cost per incident | measured Day 9 | at least 40% lower |
| p95 latency | measured Day 9 | at least 40% lower |
| Injection block rate | measured Day 10 | at least 85% |

## 8. Assumptions and risks

| Risk | Mitigation |
|---|---|
| LLM rate limits | Caching, cheap model in CI, small paid budget |
| Small benchmark is noisy | 3 runs per scenario, report mean and spread |
| API changes in MCP or LangGraph | Pin versions, read current docs |
| Scope creep | Follow cut lines in the roadmap |

## 9. Release criteria

- All P0 stories work end to end.
- Benchmark, red-team and CI gate results committed.
- Public demo deployed with rate limit and cost cap.
- README with architecture diagram, results table and demo video.

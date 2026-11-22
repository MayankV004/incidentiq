# 14-Day Roadmap: IncidentIQ

Assumes 5 to 6 focused hours per day, Nov 17 to Nov 30, 2026. Each day has a concrete done-when check.

| Day | Date | Work | Done when |
|---|---|---|---|
| 1 | Nov 17 | Repo skeleton, Docker Compose. Build gateway, orders, payments, fake external API, Postgres, Redis. Add `/metrics` and JSON logs. Traffic generator. Prometheus | Shop runs; Prometheus shows live graphs; logs grow |
| 2 | Nov 18 | Fault injector (6 fault types). Record about 30 scenarios with labels, including 3 to 4 ambiguous. Scenario loader | `scenarios/` complete and loadable |
| 3 | Nov 19 | Metrics and logs MCP servers (live and replay modes), validation, caps, audit log. MCP Inspector tests, contract tests | Tools work standalone in both modes |
| 4 | Nov 20 | Write runbooks and postmortems. DB schema and migrations. RAG ingestion, hybrid search, reranker, citations. Retrieval test set | hit@3 and MRR recorded for vector, hybrid, hybrid+rerank |
| 5 | Nov 21 | LangGraph skeleton: state, supervisor, three specialists in parallel, structured outputs. MCP adapters with allow-lists | One scenario runs end to end in terminal |
| 6 | Nov 22 | Root-cause agent, confidence, citations. Try 5 scenarios, fix obvious prompt problems | Correct on easy scenarios, citations present |
| 7 | Nov 23 | FastAPI endpoints, SSE streaming, remediation MCP (dry-run), approval interrupt with checkpointing, minimal Live Incident page | Alert, agents, report, approve works |
| 8 | Nov 24 | Langfuse tracing, per-incident cost tracking, Prometheus metrics for IncidentIQ, Grafana dashboard | Every run has a trace and cost |
| 9 | Nov 25 | Eval harness: all metrics, 3 repeats, versioned results, judge spot-check. **Record baseline** | Baseline results committed |
| 10 | Nov 26 | Guardrails: PII, injection defense, groundedness gate, abstention. 20-case red-team suite and runner | Block rate measured; failures noted |
| 11 | Nov 27 | Optimization: model routing, prompt trimming, caching, budget guard, parallelism. Re-run evals | Before/after table complete |
| 12 | Nov 28 | GitHub Actions with eval subset and regression gate. Evaluation and Security pages. Demonstrate a red CI run | Gate proven; all UI pages working |
| 13 | Nov 29 | Deploy to Oracle VM with Compose and Caddy. Rate limit and cost cap. Public end-to-end test | Public demo works |
| 14 | Nov 30 | README with diagram and results, 2-minute demo video, blog draft, resume and portfolio updates | Ready to share |

## Daily rhythm

1. Start: write the day's "done when" test or check first.
2. Build the smallest version, run it, commit.
3. End: update the changelog, record any metric you measured, note blockers.

## Cut lines (drop in this order if behind)

1. UI polish and Security page (keep numbers in README).
2. Semantic cache (keep exact-match).
3. Scenarios 30 down to 20.
4. Grafana dashboard (keep Langfuse).
5. AWS and Terraform.

**Never cut:** eval harness, baseline-then-optimize numbers, guardrails and red-team suite, human approval.

## Checkpoints

| Checkpoint | By | Question to ask |
|---|---|---|
| A | End of Day 4 | Do I have data, tools and retrieval working independently? |
| B | End of Day 7 | Can I demo one incident end to end with approval? |
| C | End of Day 9 | Do I have a trustworthy baseline? |
| D | End of Day 12 | Are quality, security and CI proven with numbers? |
| E | End of Day 14 | Can a stranger understand and run it from the README? |

## Risks to watch

| Risk | Early signal | Response |
|---|---|---|
| Behind schedule at Day 5 | Agents not running end to end | Reduce scenarios to 20, simplify UI |
| Rate limits | 429 errors in evals | Cache, cheaper model, spread runs |
| Benchmark too easy | 100% accuracy on first run | Add ambiguous and overlapping-symptom scenarios |
| ARM image issues on Oracle | Container exec format errors | Rebuild with `buildx` for arm64 |

## Final deliverables

- Public repo with docs, README, results and red-team outcomes
- Live demo URL (cost-capped)
- 2-minute demo video
- One blog post on a concrete finding
- Updated resume bullets with real measured numbers

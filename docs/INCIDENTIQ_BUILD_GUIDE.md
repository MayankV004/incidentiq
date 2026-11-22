# IncidentIQ: Hand-Coding Guide

Two parts:

- **Part A**: a mentor prompt. Paste it into a new Claude chat (or a Claude Project) together with your 12 doc files. It makes Claude teach and review instead of dumping code.
- **Part B**: the step-by-step implementation plan. Follow it in order. Each step has *Learn*, *Build*, *Done when*, and *Watch out*.

---

# Part A: The Mentor Prompt

Copy everything inside the block below.

```text
ROLE
You are my senior engineer mentor. I am Mayank, a final-year CS student, hand-coding a project called IncidentIQ from scratch to learn it deeply. My 12 design docs (00_README to 11_ROADMAP_14_DAY) are attached. Treat them as the source of truth for scope, schemas, API shapes, and the build order.

MY GOAL
I must be able to explain and defend every line in an interview. I am NOT trying to finish fastest. I am trying to understand fastest.

HOW YOU TEACH (every step)
1. CONCEPT FIRST: before I write code, explain the concept in 5-10 lines: what it is, why this project needs it, and one alternative and why we don't use it. Use a small analogy or toy example. No jargon without defining it.
2. PREDICT: ask me one short question about how I think it will work. Wait for my answer.
3. I CODE: I write the code myself. You do not give me the full solution.
4. HINT LADDER when I'm stuck, one rung at a time, and only when I ask:
   (a) a question that points at the problem,
   (b) the name of the function/concept to look up,
   (c) a tiny snippet of at most 5 lines,
   (d) the full solution, only if I explicitly say "show me the answer".
5. REVIEW: when I paste my code, review it like a PR: correctness, naming, types, error handling, and "what happens if X fails?". Point out the 2-3 most important issues, not everything.
6. VERIFY: give me a concrete "done when" check (a command to run, a test to write, an output to see).
7. CHECKPOINT: end each step with 2-3 quiz questions on what I just built. If I miss one, re-explain differently.

RULES
- Never write a whole file or module for me unless I say "show me the answer".
- Boilerplate (Dockerfile syntax, YAML, config) you may give, but explain each line.
- For fast-moving libraries (LangGraph, MCP SDK, Langfuse, LiteLLM, RAGAS), tell me to check the CURRENT official docs and ask me to paste the relevant doc snippet. Do not guess API names from memory. If unsure, say so.
- If I make a design decision that conflicts with the docs, say so and explain the tradeoff, then let me decide.
- If I'm over-engineering or behind schedule, point to the cut lines in 11_ROADMAP_14_DAY.
- Be honest when my code or approach is wrong. Don't flatter. Explain kindly.
- Keep replies short. One step at a time. Do not jump ahead.
- Connect new concepts to ones I already learned ("this is the same idea as X from Day 3").

SESSION PROTOCOL
- Start of session: ask me which Day/Step I'm on, what I finished, and what's blocking me.
- End of session: summarize (a) what I built, (b) concepts I now know, (c) concepts I'm shaky on, (d) the first task for next session.
- If I say "explain like I'm new", drop to first principles. If I say "go deeper", go into internals and tradeoffs.

FIRST MESSAGE
Confirm you've read the docs, summarize IncidentIQ in 5 lines to check we agree, then start at Part B Step 0. Ask me only one question.
```

**Tips for using the prompt**

- Put it in a Claude **Project** with the 12 docs as project knowledge so you don't re-upload.
- Start every new chat with: `Day N, Step N.M. Done so far: ... Stuck on: ...`
- Paste *your* code and the *error output* together. It saves a round trip.
- Say "quiz me" at the end of each day.

---

# Part B: Step-by-Step Implementation Plan

## How to use this plan

For every step, do this loop: **Learn (20 min) → Predict → Build → Run the check → Commit**.

- Dates in the roadmap (Nov 17 to 30) are a guide. Use **Day numbers**, not dates. If you are behind, use the cut lines at the bottom.
- Commit after every "Done when" passes. Message format: `day3: logs MCP server replay mode`.
- Keep a `LEARNING_LOG.md`: three lines per day (built / learned / confused about). It becomes your blog and interview material.
- Write the **test or check first**, then the code.

## Dependency map (what depends on what)

```
Shop (Day 1) -> Scenarios (Day 2) -> MCP servers (Day 3) ----+
                                  -> RAG (Day 4) ------------+--> LangGraph agents (Day 5-6)
                                                                  -> API + approval (Day 7)
                                                                  -> Tracing/cost (Day 8)
                                                                  -> Evals BASELINE (Day 9)
                                                                  -> Guardrails + red team (Day 10)
                                                                  -> Optimize + re-eval (Day 11)
                                                                  -> CI + UI (Day 12) -> Deploy (13) -> Ship (14)
```

---

## Day 0: Setup (1 to 2 hours, before Day 1)

**Learn:** virtual environments, `pyproject.toml`, why we pin versions, `.env` vs `.env.example`.

**Build**
1. Create repo `incidentiq/`. Folders: `shop/`, `faults/`, `mcp_servers/`, `incidentiq/` (package), `evals/`, `ui/`, `knowledge/`, `scenarios/`, `deploy/`, `tests/`.
2. Python 3.11+ venv. Install: `fastapi uvicorn pydantic httpx pytest ruff`.
3. `.gitignore` (include `.env`, `__pycache__`, `.venv`), `.env.example`, empty `README.md`.
4. `pre-commit` with ruff.
5. Install Docker and confirm `docker compose version` works.

**Done when:** `pytest` runs (even with 0 tests), `ruff check .` passes, first commit pushed to GitHub.

**Watch out:** never commit a `.env` with real keys. Run `git status` before every commit.

---

## Day 1: The demo shop (the thing we will break)

**Learn first**
- What a *metric* is vs a *log* (numbers over time vs event lines). Why on-call engineers need both.
- Prometheus model: counters, gauges, histograms; the `/metrics` scrape endpoint.
- Structured (JSON) logging and why it beats plain text.
- Docker Compose basics: services, networks, volumes, `depends_on`.

**Build**
1. `shop/orders`, `shop/payments`, `shop/gateway`, `shop/fake_external` as tiny FastAPI apps (gateway calls orders and payments; payments calls the fake external API; orders uses Postgres and Redis).
2. Add `prometheus_client` metrics to each: request counter, latency histogram, error counter, plus gauges `db_pool_in_use`, `memory_mb`, and a cache hit-rate metric. These names must match the "allowed metrics" in doc 06.
3. JSON logs with `structlog`: fields `ts, level, service, msg, request_id`. Write to a file in a shared volume.
4. `faults/traffic_gen.py`: a loop sending steady requests to the gateway.
5. `docker-compose.yml` with postgres, redis, shop services, prometheus (scrape config).

**Done when:** Prometheus UI (`:9090`) graphs request rate and latency for each service, and `tail -f` on the log file shows JSON lines growing.

**Watch out:** make the DB connection pool small and configurable now (you will exhaust it on purpose on Day 2).

---

## Day 2: Fault injection and scenarios (your benchmark data)

**Learn first**
- What each fault looks like in telemetry: memory leak (slow ramp), pool exhaustion (flat-lines at max, then errors), slow query (latency up, DB fine), bad deploy (errors start at a point in time), dependency timeout, cache failure.
- Why *ground-truth labels* matter and why a benchmark needs a train/held-out split.

**Build**
1. Fault injector: an endpoint or env flag per fault (`memory_leak`, `slow_db_query`, `db_pool_exhaustion`, `bad_deploy_config`, `dependency_timeout`, `cache_failure`) with a `variant` parameter.
2. A recorder script: inject fault, wait, query the Prometheus HTTP API for the window, copy the matching log lines, save `metrics.json`, `logs.jsonl`, `alert.json`, `label.json` into `scenarios/<id>/` (format in doc 07).
3. Record ~30 scenarios, including 3 to 4 **ambiguous** ones (symptoms with no clear cause, `should_abstain: true`).
4. A `load_scenario(id)` function and a pytest that loads all scenarios and validates `label.json` with a Pydantic model.

**Done when:** `pytest tests/test_scenarios.py` passes for all scenarios and you can eyeball one scenario and guess its label yourself.

**Watch out:** record each scenario yourself and *look at it*. If you can't tell the cause from the data, it's a good "hard" or "ambiguous" case. Mark 10 as held-out now and do not tune on them.

---

## Day 3: MCP servers (the tool boundary)

**Learn first**
- What MCP is: a protocol so an AI client can discover and call tools on a server. Compare to plain function calling (MCP = standard, separate process, discoverable).
- Tools, input schemas, transports (stdio vs streamable HTTP).
- Why tool outputs from logs are **untrusted**, and what "wrapping" does.
- Least privilege and input validation.

**Build**
1. Read the *current* MCP Python SDK docs (FastMCP). Make a trivial `hello` server and call it with the **MCP Inspector**.
2. `mcp_servers/metrics_server.py`: `list_metrics`, `query_metric`, `detect_anomaly`. Pydantic validation, allowed-metric list, minutes 1..180, downsample to ≤60 points.
3. `mcp_servers/logs_server.py`: `search_logs`, `get_error_clusters`, `get_log_context` (caps from doc 06). Wrap results in `<untrusted_data source="logs">`.
4. Implement both `DATA_MODE=live` (Prometheus HTTP API / real log file) and `replay` (reads `scenarios/<id>/`). Put the data access behind one small interface so tools don't care which mode.
5. Audit logging: every call writes tool name, args, result size.
6. Contract tests with pytest: bad service name rejected, window cap enforced, output wrapped.

**Done when:** Inspector shows the tools, they return correct data in both modes, contract tests pass.

**Watch out:** `detect_anomaly` can be simple (z-score on a rolling window). Don't over-engineer. For error clustering, normalize numbers/UUIDs in messages then group by the normalized string.

---

## Day 4: Knowledge base and RAG

**Learn first**
- Embeddings (text to vector), cosine similarity, why bge-small has 384 dimensions.
- Chunking: why we split by section and keep titles.
- Keyword search (BM25 / Postgres `tsvector`) vs vector search, and why **hybrid** wins.
- Reciprocal Rank Fusion (RRF) and what a cross-encoder reranker does differently from a bi-encoder.
- Metrics: hit@k and MRR.

**Build**
1. Write ~8 to 10 runbooks and a few postmortems in `knowledge/` (markdown with headings), one per fault type plus a couple of distractors.
2. Alembic migrations for `kb_documents` and `kb_chunks` (copy the schema from doc 04, run postgres with pgvector).
3. Ingestion script: split by heading, embed with sentence-transformers, store; skip unchanged docs using `content_hash`.
4. Retrieval functions, built one at a time: vector-only, keyword-only, RRF hybrid, then rerank top 20 and return top 5.
5. A small retrieval test set: 20 queries with the expected chunk id. Measure hit@3 and MRR for the three strategies and save the numbers.

**Done when:** a table of hit@3/MRR for vector vs hybrid vs hybrid+rerank is saved in `evals/results/retrieval.md`.

**Watch out:** the same embedding model must be used at ingest and query time. Changing dimension means re-embedding and altering the column.

### Checkpoint A: do data, tools, and retrieval each work independently?

---

## Day 5: LangGraph skeleton

**Learn first**
- What an *agent* really is: an LLM in a loop that can call tools. Difference between a *workflow* (fixed graph) and a free-roaming agent. We use a graph for control and testability.
- LangGraph concepts: `State`, nodes, edges, conditional edges, reducers (why `Annotated[list, operator.add]` lets parallel nodes append safely), compile, invoke/stream.
- Structured output: forcing the LLM to return a Pydantic schema, and what to do when parsing fails (retry).

**Build**
1. First, **no LLM**: build the graph with fake nodes that return canned evidence. Prove parallel fan-out and the merge reducer work. Print the state.
2. `llm/client.py`: *one* function through which all model calls go (this is where cost, cache, retry, tracing attach later). Start simple: call with a model name, return parsed Pydantic.
3. Supervisor node (small model) returns the `plan`.
4. Metrics and logs agents: connect to the MCP servers through the adapter library (read its current docs). Add the **allow-list wrapper** now, in code, before any agent runs.
5. Runbook agent calling your RAG retriever.
6. Every agent returns `Evidence` objects with stable ids (`ev_metric_001`).

**Done when:** one replay scenario runs end to end in the terminal and prints the evidence list.

**Watch out:** write a test that asserts each agent's tool list equals its allow-list (doc 08 safe-by-design check). It is cheap now and painful later.

---

## Day 6: Root-cause agent, confidence, citations

**Learn first**
- Prompt structure: role, rules, input format, output schema. Why a "never invent evidence" rule helps but is not enough.
- Why LLM self-reported confidence is unreliable, and how to cap it with evidence signals (doc 06 section 8).
- Citation grounding: each claim must reference evidence ids.

**Build**
1. Prompts as markdown files in `incidentiq/agents/prompts/` with a version string.
2. Root-cause agent: takes all evidence, returns `Hypothesis`. No tools.
3. Confidence capping: fewer than 2 evidence kinds, or conflicts, lowers confidence. Abstain below `ABSTAIN_THRESHOLD`.
4. Run 5 scenarios manually. Read the outputs critically; fix obvious prompt issues.

**Done when:** easy scenarios are right with citations that actually point to real evidence ids.

**Watch out:** don't tune on all 30 scenarios by hand. Use the dev set only.

---

## Day 7: API, streaming, approval, minimal UI

**Learn first**
- FastAPI async endpoints, background tasks, dependency injection.
- Server-Sent Events: one-way server-to-client stream; why SSE instead of WebSockets here.
- LangGraph **checkpointing** and **interrupt**: pausing a graph, persisting state, resuming after a human decision.
- Why remediation needs a single-use approval token (a capability the model cannot forge).

**Build**
1. Migrations for core tables (incidents, agent_runs, evidence, hypotheses, approvals).
2. `POST /v1/incidents` (returns 202, runs graph in background), `GET /v1/incidents/{id}`, `GET .../events` (SSE).
3. Emit events from nodes (`agent_started`, `tool_call`, `evidence`, `hypothesis`, `done`).
4. `remediation_server` (dry-run only, rejects calls without a valid token).
5. `human_approval` node with interrupt; `POST .../approval` issues the token and resumes.
6. Minimal Next.js + TypeScript Live Incident page: submit alert, show timeline, Approve/Reject.

**Done when:** alert, agents, report, approve (dry-run) works from the UI.

### Checkpoint B: can you demo one incident end to end with approval?

---

## Day 8: Observability and cost tracking

**Learn first**
- Traces vs metrics vs logs. What a span is. Why LLM apps need traces (you must see each prompt and response).
- How tokens turn into cost (price per 1M tokens, prompt vs completion).

**Build**
1. Langfuse (cloud or self-hosted): wrap the single LLM function so every call is a traced span with `incident_id`.
2. `llm/cost.py`: price table, compute cost, write `llm_calls`, update `incidents.cost_usd`.
3. Per-incident budget check inside nodes.
4. Prometheus metrics for the API (names in doc 10) and a basic Grafana dashboard.

**Done when:** every run has a Langfuse trace and a nonzero cost in the DB.

---

## Day 9: Evaluation harness and BASELINE

**Learn first**
- Why evals matter: "it seems to work" is not evidence. Variance in LLM outputs and why you run 3 repeats.
- Accuracy vs groundedness vs abstention precision/recall.
- LLM-as-judge: its biases, and why you spot-check by hand.
- Overfitting a benchmark, and why you hold out 10 scenarios.

**Build**
1. `evals/scorers.py`: accuracy (category AND service), evidence recall, tool-use correctness, abstention quality, action safety (must be 100%).
2. `evals/judge.py`: groundedness judge with a different model if possible.
3. `evals/run_evals.py`: loop (scenario x repeat), create incident in replay mode, wait, score, store to `eval_runs`/`eval_results`, write `results/<name>.json`.
4. `evals/report.py`: markdown table and comparison.
5. Hand-check 10 judge decisions and record agreement.
6. **Run the baseline unoptimized system and commit the results.** Do not improve anything before this.

**Done when:** `v1-baseline.json` is committed, with failure analysis notes (retrieval miss, tool misuse, reasoning error, guard too strict).

**Watch out:** if the baseline is 100%, your benchmark is too easy. Add harder scenarios.

### Checkpoint C: do you trust your baseline?

---

## Day 10: Guardrails and red team

**Learn first**
- Prompt injection (direct vs **indirect**: instructions hidden in data the agent reads). Why this is the top agent risk.
- Defense in depth: no single layer is trusted; capability limits are the backstop.
- PII redaction (Presidio + regex); false positives vs false negatives.

**Build**
1. Input guard: length limit, PII redaction before storage and model calls, injection scan.
2. Tool-output guard: scan and quarantine suspicious spans; record `guardrail_events`.
3. Output guard: groundedness check, strip unsupported claims, abstain rule, prompt-leak scan.
4. `evals/redteam/cases.json` (20 attacks per doc 08) and a runner that classifies outcome as blocked / partial / succeeded.
5. Automated safe-by-design tests (no remediation without token, no PII in stored `raw_alert`).
6. Run the suite, fix the top failures, re-run, keep history.

**Done when:** block rate is measured and stored, with a list of partial/succeeded cases and the fix for each.

**Watch out:** write the attack cases yourself before building defenses, so the tests aren't shaped by the fix.

---

## Day 11: Optimization (measure each change alone)

**Learn first**
- Why you change **one thing at a time** and re-measure.
- Model routing, prompt compression (clustered logs vs raw), exact-match caching, parallelism and p50 vs p95 latency.

**Build** (each as its own eval run)
1. Model routing: small model for supervisor and specialists, strong model for root cause only.
2. Prompt trimming: send clustered summaries rather than raw logs.
3. Redis exact-match LLM cache.
4. Budget guard and step cap tuning.
5. Sequential vs parallel specialists latency test.
6. Abstain threshold sweep: 0.4 / 0.5 / 0.6.
7. Run `v2-optimized`, fill in the before/after table.

**Done when:** README results table has real numbers for accuracy, groundedness, cost, latency, and block rate.

**Watch out:** if accuracy drops while cost drops, report the trade-off honestly.

---

## Day 12: CI gate and UI pages

**Learn first**
- GitHub Actions: workflows, jobs, secrets, artifacts.
- A regression gate: thresholds in a JSON file that fail the build.

**Build**
1. `ci.yml`: ruff, mypy, pytest, contract tests, eval subset (8 scenarios, 1 repeat, cached outputs), secret and dependency scan.
2. `evals/thresholds.json` and a script that exits nonzero on violation.
3. **Prove the gate**: degrade a prompt on a branch, capture the red build (screenshot), revert.
4. Evaluation page (compare two runs) and Security page (block rate, case table).

**Done when:** a red CI run is captured and all UI pages load.

### Checkpoint D: are quality, security, and CI proven with numbers?

---

## Day 13: Deploy

**Learn first**
- Reverse proxy and automatic HTTPS (Caddy), internal vs public Docker networks, ARM64 vs x86 images.
- Firewalls: cloud security list **and** the VM's own firewall.

**Build**
1. Oracle VM (Always Free ARM). SSH keys only. Install Docker and Compose.
2. Open ports 80 and 443 in both the VCN and the VM firewall.
3. `deploy/docker-compose.prod.yml`: only Caddy is public.
4. Pre-embed the knowledge base at build time.
5. Rate limit, daily cost cap, API key on the demo.
6. Smoke test: `/readyz`, then one replay incident completes.
7. Nightly `pg_dump`.

**Done when:** the public URL works end to end.

**Watch out:** `exec format error` means a wrong-architecture image; rebuild with `buildx` for arm64. Set a hard spending limit on LLM keys before going public.

---

## Day 14: Ship

**Build**
1. README: one-paragraph pitch, architecture diagram, results table, red-team table, limitations, how to run.
2. 2-minute demo video: inject fault, watch agents, read report, approve dry-run, show eval compare.
3. Blog post on one concrete finding (for example, "hybrid + rerank improved hit@3 from X to Y").
4. Resume bullets using **only measured numbers**; add to portfolio.
5. Have a friend try to run it from the README alone.

### Checkpoint E: can a stranger understand and run it?

---

## Cut lines (drop in this order if behind)

1. UI polish and Security page (keep numbers in README)
2. Semantic cache (keep exact-match)
3. 30 scenarios down to 20
4. Grafana dashboard (keep Langfuse)
5. AWS / Terraform

**Never cut:** eval harness, baseline-then-optimize numbers, guardrails and red team, human approval.

---

## Concept checklist (tick when you can explain it without notes)

- [ ] Metrics vs logs vs traces
- [ ] Prometheus counter / gauge / histogram
- [ ] What MCP is and why tool output is untrusted
- [ ] Embeddings, cosine similarity, hybrid search, RRF, reranking
- [ ] Workflow vs agent; LangGraph state, reducers, parallel fan-out
- [ ] Structured output and retry on parse failure
- [ ] Checkpointing and human-in-the-loop interrupt
- [ ] SSE vs WebSockets
- [ ] Groundedness and why confidence is unreliable
- [ ] Prompt injection (direct and indirect) and defense in depth
- [ ] LLM-as-judge biases, variance, held-out sets
- [ ] Token cost math, caching, routing, p50 vs p95
- [ ] CI regression gates
- [ ] Reverse proxy, HTTPS, ARM64 images

## Interview talking points (collect these as you go)

1. Why a graph and not a free agent loop?
2. How do you stop a poisoned log line from causing an action?
3. How do you know it works? (benchmark, repeats, held-out set, judge spot-check)
4. What did the red team find, and what did you fix?
5. What would you change to scale this beyond demo scale?

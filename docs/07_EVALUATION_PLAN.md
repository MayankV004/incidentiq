# Evaluation Plan: IncidentIQ

Evaluation is the centerpiece of this project. Build it before tuning anything, record a baseline, then improve and show the deltas.

## 1. Objectives

1. Measure whether the agent finds the right root cause.
2. Measure whether claims are supported by evidence (hallucination control).
3. Measure whether it abstains when it should.
4. Measure cost and latency.
5. Prevent regressions automatically in CI.

## 2. Benchmark: IncidentBench-mini

Currently comprises **8 curated scenarios** (`001`–`008` in `scenarios/`) covering all 6 fault categories plus 2 ambiguous abstention cases. Expansion to 30 scenarios (20 dev / 10 held-out) is tracked on the post-demo roadmap.

Current `evals/splits.json` split across the 8 existing scenarios:
- **`dev` (6 scenarios):** `001_orders_db_pool_exhaustion`, `002_payments_dependency_timeout`, `003_orders_slow_db_query`, `004_gateway_memory_leak`, `005_orders_cache_failure`, `006_ambiguous_transient_noise`
- **`held_out` (2 scenarios):** `007_payments_bad_deploy_config`, `008_ambiguous_no_logs_found`

*(Target 30-scenario expansion layout for reference:)*

| Fault type | Variants | Notes |
|---|---|---|
| memory_leak | 4 | Differs by service and leak speed |
| slow_db_query | 5 | Missing index vs heavy query |
| db_pool_exhaustion | 5 | Different services |
| bad_deploy_config | 5 | With and without deploy marker in logs |
| dependency_timeout | 5 | Slow vs failing external API |
| cache_failure | 3 | Redis down vs eviction |
| ambiguous / no clear cause | 3 to 4 | Correct behavior is abstain |

Difficulty tags defined in schema: `easy`, `medium`, `hard`, `ambiguous`. The current 8 scenarios (`001`–`008`) comprise **3 `easy`, 3 `medium`, and 2 `ambiguous`** (no `hard` scenario exists yet).

Each scenario folder contains `metrics.json`, `logs.jsonl`, `alert.json`, `label.json`:

```json
{
  "scenario_id": "003_db_pool_exhaustion",
  "root_cause_category": "db_pool_exhaustion",
  "root_cause_service": "orders",
  "key_evidence": ["too many connections", "db_pool_in_use at max"],
  "acceptable_actions": ["increase pool size", "find leaked connections"],
  "should_abstain": false,
  "difficulty": "medium"
}
```

Split: in the current 8-scenario benchmark (`evals/splits.json`), 6 are in `dev` and 2 in `held_out`. (Expansion to 30 scenarios split 20 dev / 10 held-out, including `hard` difficulty cases, is Planned / Future work.)

## 3. Metrics (`evals/scorers.py`)

| Metric | Definition | How computed |
|---|---|---|
| Root-cause accuracy | category AND service match label (or abstains iff `should_abstain`) | exact match |
| Evidence recall | fraction of `key_evidence` items present in cited evidence | case-insensitive substring match in `evals/scorers.py` |
| Groundedness (citation validity) | cited `evidence_ids` non-empty for diagnosis (or abstained) | citation presence/validity check in `evals/scorers.py` + `guards.py` (per-claim LLM judge planned) |
| Tool-use correctness | required tools called, no forbidden or redundant calls | rule checks on `tool_calls` (in unit/contract tests) |
| Abstention quality | abstains iff `should_abstain` | `hypothesis.abstained == should_abstain` |
| Action safety | zero actions executed without approval | assertion (`100%` structurally enforced by HMAC capability tokens) |
| Cost per incident | sum of `cost_usd` (`litellm.completion_cost()` + node allowances) | aggregated in `evals/run_evals.py` |
| Latency | p50 and p95 end to end | wall-clock duration in `evals/run_evals.py` |
| Retrieval hit@3 and MRR | correct runbook in top results | `evals/run_retrieval_eval.py` |
| Injection block rate | red-team outcomes | `evals/redteam/run_redteam.py` |

## 4. Methodology

1. **In-process replay execution:** `evals/run_evals.py` invokes `incident_graph.invoke(...)` **directly in-process** with `DATA_MODE=replay` (note: this bypasses FastAPI HTTP auth and rate limits).
2. **Configurable repeats (`--repeats`, default `1`, `3` recommended for live LLM variance)**: aggregate mean scores over `8` active scenarios (`6 dev` / `2 held_out`; scaling to `30` scenarios is Planned / Future work).
3. **Versioned results:** model path (`real_llm_live` vs `deterministic_fallback`), split, repeats, and aggregate metrics are persisted to `eval_runs`/`eval_results` and committed under `evals/results/<name>.json`. Note: `v1-baseline.json` and `v2-optimized.json` were captured prior to commit `9ba61ac`'s synthetic-cost refresh, so only `v2-live.json` carries post-fix token costs.
4. **Baseline first, then optimize:** record `v1-baseline`, optimize, then re-run (`v2-optimized`, plus `v2-live` for live LLM providers).
5. **Failure analysis & honest reporting:** inspect wrong predictions (e.g. `003_orders_slow_db_query` in offline fallback) and state benchmark size (`8` scenarios -> indicative checks, not statistically strong proof).

## 5. Experiments & Planned / Future work

**Implemented comparisons:**
- **Episodic memory ablation:** `--ablate-memory` (`ENABLE_AGENT_MEMORY=false` vs `true`).
- **Deterministic offline fallback vs live LLM synthesis (`v2-live`):** measure real model quality, cost, and latency vs rule fallback.
- **Knowledge retrieval quality:** 20-query BM25 + Jaccard evaluation via `evals/run_retrieval_eval.py`.

**Planned / Future work (not yet implemented in harness):**
- **Hybrid RAG comparison:** vector only vs `pgvector` + `tsvector` hybrid vs hybrid + cross-encoder rerank.
- **Cross-vendor LLM judge + RAGAS/DeepEval faithfulness:** evaluate with a separate strong judge model and spot-check 10 decisions manually.
- **Dedicated sweeps:** strong everywhere vs routed small/strong (`MODEL_SMALL`/`MODEL_STRONG`), raw logs vs clustered summaries, Redis LLM cache on vs off, sequential vs parallel specialists, abstention threshold sweep (`0.4`/`0.5`/`0.6`), and `eval_runs.config` git SHA JSON metadata column.

## 6. Harness design

```
evals/
  run_evals.py        # CLI: --name, --repeats, --split, --scenarios-dir, --ablate-memory
  score_live.py       # Scores SQLite incidents labeled via POST /v1/incidents/{id}/feedback
  scorers.py          # accuracy, recall, groundedness, abstention
  run_retrieval_eval.py # 20-query KB BM25 evaluation (Hit@3, MRR)
  results/            # versioned JSON outputs, committed
  redteam/            # 20-vector adversarial attack suite and runner
scripts/
  capture_incident.py # Captures live Prometheus + log window into replay scenarios
```

### Real-World Capture & Shadow-Mode Scoring
1. Run Prometheus scraping alongside the stack via `deploy/docker-compose.monitoring.yml` (`DATA_MODE=live`).
2. Snapshot real fault windows with `scripts/capture_incident.py --scenario-id ... --service ...` into `scenarios_real/`, then evaluate them via `evals/run_evals.py --scenarios-dir scenarios_real --no-enforce`.
3. Measure episodic memory impact via `evals/run_evals.py --ablate-memory` (`ENABLE_AGENT_MEMORY=false` vs `true`).
4. Label live/shadow UI runs (`correct_root_cause`, `wrong_root_cause`, `good_abstention`, `false_alarm`) and run `evals/score_live.py` to compute empirical accuracy, abstention precision, confidence calibration gap, latency, and cost.

Flow: load scenarios, for each (scenario, repeat) create an incident in replay mode, wait for completion, score, store in `eval_results`, aggregate into `eval_runs.summary`, write `results/<name>.json`.

## 7. CI gate

| Workflow | Status | Trigger | Scope | Execution mode |
|---|---|---|---|---|
| `.github/workflows/ci.yml` | Implemented | Push / PR to `main`/`master` | `ruff check .`, `mypy .`, `update_readme_results.py --check`, `pytest`, `evals/redteam/run_redteam.py`, `evals/run_evals.py --name ci-eval`, UI `pnpm lint` + `tsc --noEmit` | Offline deterministic replay (`evals/thresholds.json`) |
| `eval-full.yml` | Planned / Future work | Manual or nightly | All scenarios, 3 repeats, uploads results artifact | Configured live LLM models |

Gate thresholds stored in `evals/thresholds.json` (`min_accuracy_pct`, `min_groundedness_pct`, `min_abstention_correct_pct`, `min_action_safety_pct`, `max_mean_cost_usd`). PR fails if any threshold is violated.

## 8. Reporting templates

Results table (README):

| Metric | v1 baseline | v2 optimized | Change |
|---|---|---|---|
| Accuracy | | | |
| Evidence recall | | | |
| Groundedness | | | |
| Abstention quality | | | |
| Cost per incident | | | |
| Latency p50 / p95 | | | |
| Injection block rate | | | |

Include a failure-analysis paragraph and a limitations paragraph (small benchmark, simulated faults, single demo system).

# Evaluation Plan: IncidentIQ

Evaluation is the centerpiece of this project. Build it before tuning anything, record a baseline, then improve and show the deltas.

## 1. Objectives

1. Measure whether the agent finds the right root cause.
2. Measure whether claims are supported by evidence (hallucination control).
3. Measure whether it abstains when it should.
4. Measure cost and latency.
5. Prevent regressions automatically in CI.

## 2. Benchmark: IncidentBench-mini

About 30 scenarios recorded from the demo shop.

| Fault type | Variants | Notes |
|---|---|---|
| memory_leak | 4 | Differs by service and leak speed |
| slow_db_query | 5 | Missing index vs heavy query |
| db_pool_exhaustion | 5 | Different services |
| bad_deploy_config | 5 | With and without deploy marker in logs |
| dependency_timeout | 5 | Slow vs failing external API |
| cache_failure | 3 | Redis down vs eviction |
| ambiguous / no clear cause | 3 to 4 | Correct behavior is abstain |

Difficulty tags: easy (single clear signal), medium (two plausible causes), hard (noisy or overlapping symptoms), ambiguous (should abstain).

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

Split: use 20 scenarios for development and prompt tuning, hold out 10 for the final reported numbers to avoid overfitting your prompts to the benchmark.

## 3. Metrics

| Metric | Definition | How computed |
|---|---|---|
| Root-cause accuracy | category AND service match label | exact match |
| Evidence recall | fraction of `key_evidence` items present in cited evidence | string or semantic match, judged |
| Groundedness | fraction of claims supported by cited evidence | LLM judge or RAGAS faithfulness |
| Tool-use correctness | required tools called, no forbidden or redundant calls | rule checks on `tool_calls` |
| Abstention quality | abstains iff `should_abstain` | precision and recall of abstention |
| Action safety | zero actions executed without approval | assertion, must be 100% |
| Cost per incident | sum of `llm_calls.cost_usd` | from DB |
| Latency | p50 and p95 end to end | from DB |
| Retrieval hit@3 and MRR | correct runbook in top results | separate retrieval test |
| Injection block rate | red-team outcomes | see security doc |

## 4. Methodology

1. **Replay mode only** for evals: MCP servers read frozen scenario data, so results are reproducible.
2. **3 repeats per scenario**; report mean and standard deviation. A single run of 30 items is too noisy to trust.
3. **Judge model from a different vendor** than the agent where possible. Spot-check at least 10 judge decisions by hand and record agreement.
4. **Version everything**: git sha, model names, prompts version, thresholds stored in `eval_runs.config`.
5. **Baseline first** (Day 9) with the unoptimized system, then optimize, then re-run (Day 11).
6. **Failure analysis**: for each wrong answer, categorize the cause (retrieval miss, tool misuse, reasoning error, guard too strict) and fix the top two categories.
7. **Honest reporting**: include failures and limits in the README.

## 5. Experiments to run and report

| Experiment | Comparison |
|---|---|
| RAG strategy | vector only vs hybrid vs hybrid + rerank |
| Model routing | strong model everywhere vs routed small/strong |
| Prompt trimming | raw logs vs clustered summaries |
| Caching | on vs off (cost and latency) |
| Parallelism | sequential vs parallel specialists (latency) |
| Abstention threshold | 0.4, 0.5, 0.6 (trade-off between wrong answers and over-abstaining) |

## 6. Harness design

```
evals/
  run_evals.py        # CLI: python -m evals.run_evals --name v1-baseline --repeats 3
  scorers.py          # accuracy, recall, tool-use, abstention
  judge.py            # groundedness judge prompts
  report.py           # markdown/CSV summary and comparison
  results/            # versioned JSON outputs, committed
  redteam/            # attack cases and runner
```

Flow: load scenarios, for each (scenario, repeat) create an incident in replay mode, wait for completion, score, store in `eval_results`, aggregate into `eval_runs.summary`, write `results/<name>.json`.

## 7. CI gate

| Workflow | Trigger | Scope | Model |
|---|---|---|---|
| `ci.yml` | every PR | lint, unit tests, MCP contract tests, eval subset (8 scenarios, 1 repeat) | cheap model with cached outputs |
| `eval-full.yml` | manual or nightly | all scenarios, 3 repeats, uploads results artifact | configured models |

Gate thresholds stored in `evals/thresholds.json` (for example accuracy at least baseline minus tolerance, groundedness at least 0.85). PR fails if any threshold is violated. Prove the gate once by deliberately degrading a prompt and capturing the red build.

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

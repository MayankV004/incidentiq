# Knowledge Base & BM25 Retrieval

This folder holds markdown runbooks and past incident reports searched by the Runbook Agent.
Retrieval runs locally in memory using keyword scoring with no vector database.

---

## 1. Files

```text
knowledge/
├── runbooks/
│   ├── bad_deploy_config.md
│   ├── cache_failure.md
│   ├── memory_leaks.md
│   ├── orders_db_pool.md
│   ├── payments_timeout.md
│   └── slow_queries.md
└── postmortems/
    ├── incident_104_db_pool_leak.md
    ├── incident_108_cache_eviction_storm.md
    └── incident_112_bad_deploy_config.md
```

---

## 2. How Retrieval Works (`incidentiq/rag/engine.py`)

`HybridRAGEngine` loads all markdown files under `knowledge/` at startup:
1. Splits each file on `##` headings and creates chunk IDs like `doc_orders_db_pool_sec_0`.
2. In `runbook_agent_node`, evidence IDs are prefixed with `ev_kb_` (for example `ev_kb_doc_orders_db_pool_sec_0`).
3. Scores every chunk against `f"{service} {alert.symptom}"` using:
   * **Okapi BM25** (`k1 = 1.5`, `b = 0.75`) weighted by `0.6`.
   * **Jaccard token overlap** weighted by `15.0`.
   * **Service metadata boost** (`+2.5`) when the document's `Service:` matches the alert service.

There are no embeddings and no external vector databases.

---

## 3. Retrieval Benchmark Results

Measured offline against the 20 queries in `evals/retrieval_queries.json`:

| Metric | Value | Status | Source |
|---|---|---|---|
| **Hit@3** | 100.0% (20/20 queries in top 3) | measured (offline queries) | [../evals/results/retrieval_summary.json](../evals/results/retrieval_summary.json) |
| **MRR (Mean Reciprocal Rank)** | 0.9750 (19 at rank 1, 1 at rank 2) | measured (offline queries) | [../evals/results/retrieval_summary.json](../evals/results/retrieval_summary.json) |
| **Query Latency** | not measured yet | not measured yet | — |

To run the retrieval check from the repo root:
```bash
PYTHONPATH=. uv run python evals/run_retrieval_eval.py
```

---

## 4. Safety Note

In `incidentiq/agents/nodes.py`, `runbook_agent_node` scans retrieved chunks with `GuardrailManager.scan_injection` before passing text to the synthesis step.
If a chunk matches an injection pattern, its preview is replaced with `[QUARANTINED_POTENTIAL_INJECTION]`.

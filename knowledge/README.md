# Operational Knowledge Base & BM25 Retrieval Engine 📚

This directory houses the curated operational runbooks and past incident postmortems ingested by IncidentIQ's **Runbook RAG Agent** via an in-memory BM25 lexical ranking engine.

---

## 1. Directory Structure

```
knowledge/
├── runbooks/                            # Actionable operational procedure manuals
│   ├── orders_db_pool.md                # DB connection pool sizing & leak troubleshooting
│   ├── payments_timeout.md              # Downstream payment gateway timeout mitigation
│   ├── memory_leaks.md                  # Heap surge identification and graceful recycling
│   ├── slow_queries.md                  # Unindexed query detection and explain analyze
│   ├── cache_failure.md                 # Redis cache connection drops & eviction stampedes
│   └── bad_deploy_config.md             # CrashLoops from missing environment variables / config errors
└── postmortems/                         # Historical incident reports & lessons learned
    ├── incident_104_db_pool_leak.md     # P0: Orders connection leak caused by retry bug
    ├── incident_108_cache_eviction_storm.md # P1: Redis limit reached triggering PostgreSQL stampede
    └── incident_112_bad_deploy_config.md    # P0: Payments CrashLoop from missing env secret in release
```

---

## 2. In-Memory BM25 Retrieval Engine (`incidentiq/rag/engine.py`)

IncidentIQ avoids heavy vector database infrastructure and vector embedding API latency by using a pure Python **BM25 Lexical Ranking Engine** tailored for engineering runbooks:

* **Sub-2ms Query Latency:** In-memory tokenization and inverted index ranking runs locally without external network overhead.
* **Service-Specific Metadata Boosting:** Automatically multiplies relevance scores when a runbook's title or tags match the alert target service (`orders`, `payments`, `gateway`).
* **Section-Level Chunking:** Splits documents on markdown headings (`##`), attaching a deterministic citation key (e.g., `ev_kb_orders_db_pool_sec_0`).

---

## 3. Runbook Structure & Grounded Citations

Every runbook follows a strict structure:
1. **Symptoms & Signals:** Specific Prometheus metrics and log signatures.
2. **Immediate Remediation:** Safe mitigation steps (restart, scale, configuration tuning).
3. **Investigation Checklist:** Commands and queries to confirm the root cause.

When the RAG Agent discovers a matching runbook section, it attaches the section ID as structured evidence, enabling full human verification inside the UI Citation Drawer.

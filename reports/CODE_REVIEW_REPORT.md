# IncidentIQ Code Quality & Architecture Review Report

**Review Target:** IncidentIQ Codebase (`/home/streamliner/incidentiq`)  
**Reviewer:** Principal Software Engineer & Code Quality Reviewer  
**Date:** 2026-11-24  
**Scope:** Architecture, Correctness, Concurrency, Error Handling, Typing, Performance, Testing, and Frontend Quality  
**Mode:** Rigorous Read-Only Code Review

---

## 1. Executive Summary

IncidentIQ exhibits modern engineering strengths—notably clean LangGraph state reducer semantics, structured Pydantic schemas, and an interactive Next.js dashboard with live SSE streaming. However, this code review identifies several critical architectural, concurrency, and logic defects that undermine system reliability in production. Most prominent is a frontend-backend property mismatch where `Hypothesis.category` is queried as `root_cause`, triggering hardcoded fallback UI strings across all incident scenarios. Additionally, synchronous disk I/O in the async HTTP telemetry middleware threatens to block the asyncio event loop under load, and SQLAlchemy sync queries are invoked directly inside async route handlers. In-memory dictionary state scaling limits horizontal scaling, and PostgreSQL runtime crashes occur due to an uninstalled driver.

### Top 5 Risks
1. **Frontend-Backend Property Deserialization Bug (High):** `ui/types/api.ts:31` defines `Hypothesis.root_cause`, but backend `incidentiq/schemas/models.py:27` defines `category`. Consequently, `ui/components/ReportView.tsx:96` evaluates `root_cause` to `undefined` and renders the hardcoded fallback `"DB connection pool exhaustion · orders"` for every incident.
2. **PostgreSQL Driver Missing from Runtime (High):** `incidentiq/db/session.py:10-11` rewrites `postgresql+asyncpg://` to `postgresql://`, forcing SQLAlchemy to use sync `psycopg`/`psycopg2`. Because neither is in `pyproject.toml`, specifying a PostgreSQL URL crashes the service on startup.
3. **Synchronous Disk I/O Blocking the Asyncio Event Loop (High):** `shop/common/telemetry.py:68-76` opens and writes to disk log files synchronously on every HTTP request within the FastAPI middleware, creating event loop stalls and file lock contention.
4. **Uncapped MCP Limits & Unused Query Window Parameters (Medium):** `mcp_servers/logs/server.py:61-90` and `metrics/server.py:34-45` accept `minutes: int = 30` but never filter by time window; `search_logs` lacks `min(limit, 50)` capping, allowing unbounded memory consumption.
5. **Global In-Memory State Dictionaries Preventing Multi-Worker Scaling (Medium):** `incidentiq/api/main.py:48-49` relies on module-level `INCIDENTS_DB` and `SUBSCRIBERS` dictionaries, preventing multi-process Uvicorn deployments and causing memory leaks over long uptimes.

### Readiness Ratings
- **Safe to show publicly:** **2 / 5** (The UI hardcoded fallback bug and unhandled database driver crash will be immediately apparent during live demonstrations).
- **Safe to put on a resume:** **3 / 5** (Code organization and LangGraph patterns are sound, but the concurrency bottlenecks and typing mismatches must be resolved).

---

## 2. Scope and Method

### Scope
Every source directory in the repository was analyzed across Python and TypeScript stacks:
- `incidentiq/api/`: FastAPI routes, SSE generator, state handling
- `incidentiq/agents/`: StateGraph topology, specialist nodes, reducers
- `incidentiq/guardrails/`: Regex PII masks, injection signatures, groundedness gate
- `incidentiq/rag/`: Document chunking, BM25 tokenizer, scoring
- `incidentiq/db/`: SQLAlchemy models, SQLite repository, session lifecycle
- `mcp_servers/`: FastMCP metrics, logs, and remediation endpoints
- `shop/`: Gateway, orders, payments, external service, telemetry middleware
- `evals/`: Evaluator scorers, replay runner, red-team suite
- `ui/`: Next.js 16 components, React hooks, API type contracts

### Method & Verification Tooling
Static analysis and execution checks were conducted strictly in read-only mode:
- **Linting:** `uv run ruff check .` (PASSED: All checks clean)
- **Formatting:** `uv run ruff format --check .` (FAILED: 19 files unformatted)
- **Typing:** `uv run mypy` (FAILED: `mypy` not installed in environment)
- **Unit Testing:** `uv run pytest` (PASSED: 6 unit tests in `tests/unit/`)
- **Frontend Dependencies:** `cd ui && pnpm audit` (PASSED: 0 vulnerabilities)
- **Database Driver Verification:** Executed Python driver import probe confirming missing `psycopg`
- **Replay & Redteam Benchmarks:** Executed benchmark runners verifying zero regressions in offline replay

### What Was NOT Verified and Why
- Live network traffic under ApacheBench / Locust was not executed to prevent local resource starvation.
- Live database failover scenarios on PostgreSQL / Redis were not executed because external database containers were not started.

---

## 3. Findings Table

| ID | Severity | Area | Finding | Evidence | Impact | Recommended Fix | Effort |
|---|---|---|---|---|---|---|---|
| **CR-01** | **High** | Correctness / UI | Property name mismatch (`root_cause` vs `category`) forces hardcoded fallback UI | `ui/types/api.ts:31`, `incidentiq/schemas/models.py:27`, `ui/components/ReportView.tsx:96` | UI always displays "DB connection pool exhaustion · orders" regardless of incident cause; backend logs "Diagnosis: None" | Align `Hypothesis` schema and TypeScript interfaces to use `category`, and render dynamic hypothesis reasoning | S |
| **CR-02** | **High** | Correctness / DB | Missing PostgreSQL driver crashes runtime when configured via `.env` | `incidentiq/db/session.py:10-11` | Application crashes with `ModuleNotFoundError: No module named 'psycopg'` when PostgreSQL URL is provided | Add `psycopg[binary]>=3.2.0` to `pyproject.toml` and use `postgresql+psycopg://` in `session.py` | S |
| **CR-03** | **High** | Concurrency / Perf | Synchronous blocking file I/O executed inside async telemetry middleware | `shop/common/telemetry.py:68-76` | Every request blocks Python asyncio event loop with file opens/writes; catastrophic under high concurrency | Replace synchronous `with open(...)` with an async logging handler or background `QueueHandler` | M |
| **CR-04** | **Medium** | Correctness / MCP | Time window `minutes` parameter ignored; query limit uncapped | `mcp_servers/metrics/server.py:34`, `mcp_servers/logs/server.py:53, 98` | Queries return all historical logs without time-slicing; callers can request millions of lines and trigger OOM | Implement timestamp filtering against `log["ts"]` and enforce `limit = min(limit, 50)` | S |
| **CR-05** | **Medium** | Concurrency / Arch | Module-level global dictionaries prevent multi-worker scaling and leak memory | `incidentiq/api/main.py:48-49` | Unbounded memory growth; running Uvicorn with `--workers > 1` isolates SSE subscribers and incident states | Back SSE pub/sub and state caches with Redis channels and rely on the database for incident retrieval | L |
| **CR-06** | **Medium** | Error Handling | Silent exception swallowing in LLM diagnosis node | `incidentiq/agents/nodes.py:206-210` | LLM API rate limits, authentication failures, and provider outages are hidden from telemetry | Record exception message in `state["error"]` or emit an explicit telemetry failure event before falling back | S |
| **CR-07** | **Medium** | Async Hygiene | Synchronous SQLAlchemy queries executed inside async FastAPI endpoints | `incidentiq/api/main.py:410, 480` | DB queries block the async event loop during active client connections | Wrap database repository calls in `starlette.concurrency.run_in_threadpool` or migrate to `AsyncSession` | M |
| **CR-08** | **Medium** | UI Quality | Hardcoded incident narrative body in ReportView component | `ui/components/ReportView.tsx:102-125` | UI displays orders DB pool narrative even for payment timeout or cache failure incidents | Render `hypothesis.reasoning` dynamically instead of hardcoded paragraphs | S |
| **CR-09** | **Low** | Typing | Lack of `mypy` type-checker in development dependencies | `pyproject.toml:5-24` | Type mismatches between Pydantic models and dictionaries remain undetected in CI | Add `mypy` and `pydantic-mypy` to dependencies and establish strict type-checking in CI | S |
| **CR-10** | **Low** | Code Style | 19 Python files fail automated code formatting checks | `uv run ruff format --check .` | Inconsistent code styling across codebase | Run `ruff format .` across all repository files | S |
| **CR-11** | **Low** | Maintainability | Misleading docstrings and dead parameters in RAG and log tools | `incidentiq/rag/engine.py:8-12`, `mcp_servers/logs/server.py:127` | Code claims cross-encoders and dense vectors that do not exist; `line_id` parameter is ignored | Update docstrings to accurately reflect BM25/Jaccard, and implement or remove dead parameters | S |
| **CR-12** | **Info** | Observability | Langfuse integration gracefully handles missing credentials | `incidentiq/api/main.py:55-73` | Clean fallback allows full offline development without third-party SaaS errors | Retain this robust fallback pattern | S |

---

## 4. Deep-Dive Code Review Analysis

### 4.1 Correctness & Logic Bugs

#### 1. The `root_cause` vs `category` Deserialization Defect
In `incidentiq/schemas/models.py:26-37`, the core diagnosis schema is defined as:
```python
class Hypothesis(BaseModel):
    category: str | None = None
    service: str | None = None
    confidence: float = 0.0
    reasoning: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_action: Action | None = None
    abstained: bool = False
    abstain_reason: str | None = None
```
However, in `ui/types/api.ts:28-40`, the frontend expects:
```typescript
export interface Hypothesis {
  root_cause: string;
  confidence: number;
  ...
}
```
Furthermore, in `incidentiq/api/main.py:230` and `417`:
```python
summary = f"Diagnosis: {hypothesis_dict.get('root_cause')} (Confidence: {int(hypothesis_dict.get('confidence', 0) * 100)}%)"
```
Because the Pydantic model contains `category` and not `root_cause`, `hypothesis_dict.get('root_cause')` always evaluates to `None`. This manifests as:
- SSE stream emits: `Diagnosis: None (Confidence: 85%)`
- `ui/components/ReportView.tsx:96` executes:
  ```typescript
  <h2>{hypothesis?.root_cause || "DB connection pool exhaustion · orders"}</h2>
  ```
  Since `hypothesis?.root_cause` is always `undefined`, the title falls back to `"DB connection pool exhaustion · orders"`.

#### 2. MCP Log Context Line Selection Logic
In `mcp_servers/logs/server.py:127-133`:
```python
@server.tool()
def get_log_context(
    service: str, line_id: str = "", before: int = 5, after: int = 5
) -> dict[str, Any]:
    raw_logs = load_raw_logs(service)
    return {
        "service": service,
        "context_lines": [
            wrap_untrusted(l.get("msg", "")) for l in raw_logs[: (before + after)]
        ],
    }
```
The parameter `line_id` is completely ignored. Instead of locating the target line and slicing `[target - before : target + after]`, the tool blindly returns the first `before + after` lines of the entire log file.

---

### 4.2 Error Handling & Resilience

#### 1. Swallowed Exceptions in Root-Cause Node
In `incidentiq/agents/nodes.py:206-210`:
```python
try:
    hyp = _call_llm_for_diagnosis(...)
    if hyp:
        return {"hypothesis": hyp, "cost_usd": cost, "steps": 1}
except Exception as exc:
    logger.warning(
        f"LiteLLM call failed: {exc}, falling back to deterministic synthesis"
    )
```
When an LLM provider returns a 401 Unauthorized, 429 Rate Limited, or 503 Overloaded error, the exception is logged as a warning and suppressed. The system immediately proceeds to deterministic string matching. The incident state records zero indication that an LLM call failed or that the diagnosis was produced by a fallback heuristic.

#### 2. Silent Database Upsert Failures
In `incidentiq/api/main.py:105, 335, 439`:
```python
try:
    upsert_incident(INCIDENTS_DB[incident_id])
except Exception as e:
    logger.debug(f"DB upsert failed: {e}")
```
Database insertion and update failures are logged at `DEBUG` level and swallowed. If the database disk is full, the SQLite file is locked, or PostgreSQL drops the connection, the API continues processing in memory while silently failing to persist incident state.

---

### 4.3 Concurrency & Async Hygiene

#### 1. Blocking Disk I/O in Async HTTP Middleware
In `shop/common/telemetry.py:68-76`:
```python
def file_output_processor(logger, method_name, event_dict):
    import json

    line = json.dumps(event_dict) + "\n"
    with open(log_file_path, "a") as f:
        f.write(line)
    with open(shared_log_path, "a") as f:
        f.write(line)
    return event_dict
```
This processor is invoked on every HTTP request intercepted by `telemetry_middleware`. Because FastAPI handles requests on an asyncio event loop, executing synchronous `open()`, `write()`, and flush operations blocks all concurrent coroutines on that thread.

#### 2. Synchronous Database Calls in Async SSE Endpoint
In `incidentiq/api/main.py:475-484`:
```python
@app.get("/v1/incidents/{incident_id}/stream")
async def stream_incident(incident_id: str, request: Request):
    if incident_id not in INCIDENTS_DB:
        db_inc = get_incident_from_db(incident_id)
        ...
```
`get_incident_from_db()` is a synchronous SQLAlchemy query. Calling synchronous database queries directly inside an `async def` route without delegating to `run_in_threadpool` blocks the Uvicorn worker thread.

---

### 4.4 Typing & Static Analysis

#### 1. Pydantic Model vs Dictionary Inconsistencies
State passing in `incidentiq/agents/state.py` defines `evidence: Annotated[list[Evidence], operator.add]`, where `Evidence` is a Pydantic model. However, in `incidentiq/api/main.py:207-220`:
```python
for e in node_ev:
    collected_evidence.append(e.model_dump() if hasattr(e, "model_dump") else e)
```
Throughout `main.py`, state objects are unpredictably converted between Pydantic model instances and raw dictionaries. This creates runtime attribute errors when downstream code calls `evidence.id` versus `evidence["id"]`.

#### 2. Absence of Static Type Checking in Tooling
`pyproject.toml` contains `pytest` and `ruff`, but omits `mypy`. When running `mypy .`, the command fails because `mypy` is not installed. Several modules feature `dict[str, Any]` and `list[Any]` type annotations that conceal typing mismatches between services.

---

### 4.5 Architecture & State Management

#### 1. In-Memory State Dictionaries
In `incidentiq/api/main.py:48-49`:
```python
INCIDENTS_DB: dict[str, dict[str, Any]] = {}
SUBSCRIBERS: dict[str, list[asyncio.Queue]] = {}
```
- **Horizontal Scaling:** The API cannot run with multiple Uvicorn workers (`uvicorn --workers 4`) because worker processes do not share memory. A client connecting to `/stream` on Worker A will never receive events dispatched by an investigation running on Worker B.
- **Memory Leak:** `INCIDENTS_DB` retains every incident and its full event list indefinitely in RAM with no eviction policy or TTL.

---

### 4.6 Performance & Resource Management

#### 1. Unbounded Memory in MCP Server Log Loading
In `mcp_servers/logs/server.py:20-47`:
```python
def load_raw_logs(service: str) -> list[dict[str, Any]]:
    ...
    with open(log_file) as f:
        for line in f:
            logs.append(json.loads(line))
    return logs
```
`load_raw_logs()` reads the entire log file into memory on every tool call (`search_logs`, `get_error_clusters`, `get_log_context`). On busy services where log files reach gigabytes, this will cause immediate Out-Of-Memory (OOM) process termination.

---

### 4.7 Frontend Engineering Quality

#### 1. Hardcoded Narrative Body in ReportView
In `ui/components/ReportView.tsx:102-125`:
```tsx
<p>
  Errors began when <code className="text-xs font-mono font-medium text-zinc-900 dark:text-zinc-100">db_pool_in_use</code> hit max{" "}
  {evidenceList.slice(0, 1).map((e) => (...))}
  . Logs show &quot;too many connections&quot;{" "}
  {evidenceList.slice(1, 2).map((e) => (...))}
  . Runbook section 2 matches{" "}
  {evidenceList.slice(2, 3).map((e) => (...))}
</p>
```
The narrative text is hardcoded to the orders database pool exhaustion incident. Even when diagnosing Scenario 004 (gateway memory leak) or Scenario 002 (payments timeout), the UI renders text stating that `db_pool_in_use` hit max and logs showed "too many connections".

---

## 5. What is Done Well

1. **State Reducer Architecture:** `incidentiq/agents/state.py` leverages `Annotated[list[Evidence], operator.add]` and `Annotated[float, operator.add]` for thread-safe state accumulation during parallel node execution.
2. **Deterministic Offline Replay Scenarios:** Scenarios in `scenarios/` provide structured JSON and JSONL telemetry files, enabling complete offline testing without cloud or live shop dependencies.
3. **Structured Pydantic Schemas:** Schemas in `incidentiq/schemas/models.py` cleanly define `Alert`, `Evidence`, `Hypothesis`, and `Action` models with strict validation.
4. **FastMCP Server Decoupling:** Tool servers in `mcp_servers/` use clean FastMCP decorators (`@server.tool()`) with structured return types.
5. **Modern Next.js Architecture:** The UI in `ui/` uses the Next.js 16 App Router, Tailwind CSS, Lucide icons, and semantic CSS variables for dark/light theme switching.
6. **Defensive SSE Heartbeats:** `incidentiq/api/main.py:492` emits `: ping\n\n` comments every 2 seconds during idle periods, preventing proxy connection timeouts.
7. **Clean Linting Compliance:** The codebase passes all rules in `uv run ruff check .` with zero errors or warnings.
8. **Isolated Test Fixtures:** `tests/unit/test_core.py` and `tests/unit/test_db.py` execute quickly and deterministically in under 0.6 seconds.

---

## 6. Prioritized Remediation Plan

### Tier 1: Fix Immediately (Before Going Public)
1. **Fix `root_cause` Deserialization:** Change `ui/types/api.ts` to use `category` and update `ui/components/ReportView.tsx` to render `hypothesis.reasoning` dynamically instead of hardcoded strings.
2. **Fix PostgreSQL Driver:** Add `psycopg[binary]>=3.2.0` to `pyproject.toml` and update `incidentiq/db/session.py` to use `postgresql+psycopg://`.
3. **Non-Blocking Telemetry Logging:** Migrate `shop/common/telemetry.py` to asynchronous file writers or standard Python `logging.handlers.QueueHandler`.
4. **Enforce MCP Limits:** Add `limit = min(limit, 50)` in `mcp_servers/logs/server.py` and enforce time window filtering on `log["ts"]`.

### Tier 2: Fix Before Resume Use
1. **Async DB Operations:** Refactor database calls in `incidentiq/api/main.py` using `run_in_threadpool` or SQLAlchemy async sessions.
2. **Log File Streaming / Tail:** Update `load_raw_logs` in `mcp_servers/logs/server.py` to read files using reverse line generators or file seeking rather than reading entire files into RAM.
3. **Record LLM Node Failures:** When `_call_llm_for_diagnosis` fails in `incidentiq/agents/nodes.py`, record the failure reason in state before engaging the deterministic fallback.
4. **Add `mypy` to Tooling:** Add `mypy` and `pydantic-mypy` to `pyproject.toml` and fix type annotations in API routes.

### Tier 3: Nice to Have
1. **Redis Pub/Sub State:** Replace in-memory `INCIDENTS_DB` and `SUBSCRIBERS` dictionaries with Redis streams/pubsub.
2. **Runbook Chunk ID Normalization:** Normalize markdown header chunking in `incidentiq/rag/engine.py` with content hashing.
3. **Automate Formatting in Git Hooks:** Add pre-commit hook running `ruff format --check .`.

---

## 7. Appendix: Exact Commands & Outputs

### Command 1: Pytest Unit Test Suite
```bash
$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.2.0, pluggy-1.6.0
rootdir: /home/streamliner/incidentiq
configfile: pyproject.toml
collected 6 items

tests/unit/test_core.py .....                                            [ 83%]
tests/unit/test_db.py .                                                  [100%]

============================== 6 passed in 0.54s ===============================
```

### Command 2: Ruff Linter Execution
```bash
$ uv run ruff check .
All checks passed!
```

### Command 3: Ruff Format Validation
```bash
$ uv run ruff format --check .
would reformat: incidentiq/agents/nodes.py
would reformat: incidentiq/agents/state.py
would reformat: incidentiq/api/main.py
would reformat: incidentiq/db/models.py
would reformat: incidentiq/db/repository.py
would reformat: incidentiq/db/session.py
would reformat: incidentiq/guardrails/guards.py
would reformat: incidentiq/rag/engine.py
would reformat: incidentiq/schemas/models.py
would reformat: mcp_servers/logs/server.py
would reformat: mcp_servers/metrics/server.py
would reformat: mcp_servers/remediation/server.py
would reformat: shop/common/telemetry.py
would reformat: shop/fake_external/main.py
would reformat: shop/gateway/main.py
would reformat: shop/orders/main.py
would reformat: shop/payments/main.py
would reformat: tests/unit/test_core.py
would reformat: tests/unit/test_db.py
19 files would be reformatted, 23 files already formatted
```

### Command 4: PostgreSQL Driver Probe
```bash
$ uv run python -c "import psycopg"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'psycopg'
```

### Command 5: Frontend Security & Package Audit
```bash
$ cd ui && pnpm audit
No known vulnerabilities found
```

# UI Design: IncidentIQ

Default implementation: Next.js (App Router) with TypeScript and Tailwind CSS. Keep the design clean, responsive, and information-dense; the goal is to make the agent's work and the proof of quality visible.

## 1. Navigation

Sidebar: **Live Incident**, **Incidents**, **Evaluation**, **Security**, **Traces** (external link to Langfuse), **Shop Control**.

## 2. Page 1: Live Incident (main)

```
+------------------------------------------------------------------+
| IncidentIQ                                   [Shop Control] [Docs]|
+-----------------+--------------------------+---------------------+
| ALERT           | AGENT TIMELINE (live)    | REPORT              |
| service: orders | 14:02:01 Supervisor      | Root cause:         |
| symptom: p95 4s |   plan: metrics,logs,rb  |  DB pool exhaustion |
| window: 30m     | 14:02:02 Metrics agent   |  (orders)           |
|                 |   db_pool_in_use at max  | Confidence: 87%     |
| [Submit alert]  | 14:02:03 Logs agent      | Groundedness: 95%   |
|                 |   312 "too many conn."   |                     |
| Source: live    | 14:02:03 Runbook agent   | Evidence            |
| Scenario: -     |   rb_db_pool section 2   |  [ev_metric_001]    |
|                 | Guardrails: 0 flags      |  [ev_log_004]       |
|                 | Cost $0.004  6.1 s       |  [ev_rb_002]        |
|                 |                          | Suggested action    |
|                 |                          | Review pool config  |
|                 |                          | [Approve] [Reject]  |
+-----------------+--------------------------+---------------------+
```

Behavior:
- Timeline appends events from the SSE stream; each step is expandable to show tool args and results (truncated).
- Evidence items are clickable: metric opens a small chart; log opens the lines with highlight; runbook opens the cited chunk.
- Abstained state shows an amber banner: "Not confident. Here is what was checked and what is missing."
- Guardrail events show as badges (for example "Injection quarantined") with a details popover.
- Approve and Reject only appear in `awaiting_approval`. After approval show the dry-run result.

## 3. Page 2: Incidents

Table of recent incidents: time, service, status, root cause, confidence, cost, latency. Filter by status. Click opens the Live Incident view in read-only mode.

## 4. Page 3: Evaluation

```
+------------------------------------------------------------------+
| Evaluation   Run: [v2-optimized v]  Compare with: [v1-baseline v]|
+------------------------------------------------------------------+
| Accuracy 83% (+21) | Groundedness 92% (+14) | Cost $0.004 (-58%) |
| Latency p95 6.2s (-55%) | Abstention 75% | Tool-use 95%          |
+------------------------------------------------------------------+
| Bar chart: accuracy by fault type, v1 vs v2                      |
+------------------------------------------------------------------+
| Scenario table: id | fault | difficulty | v1 | v2 | cost | notes  |
|  003 db_pool       | medium | fail      | pass | $0.004 | [trace]|
+------------------------------------------------------------------+
| [Run benchmark] (admin)                                          |
+------------------------------------------------------------------+
```

Failure drill-down: clicking a failed row shows expected vs actual, evidence used, and a link to the Langfuse trace. Show the numbers in this mock only after you have measured them.

## 5. Page 4: Security

- Headline: block rate (for example 17/20), with a bar by attack category.
- Table: case id, category, payload preview, outcome (blocked, partial, succeeded), defense that stopped it.
- A "Try an attack" box (demo mode): paste a poisoned log line, run it in a sandboxed replay scenario, and watch it get quarantined.

## 6. Page 5: Shop Control (demo)

Buttons per fault type with a variant selector, a "Reset shop" button, and a small live chart of error rate and latency from Prometheus so viewers see the fault happen. After injecting, a "Send alert to IncidentIQ" button (or automatic alert forwarding).

## 7. Components

| Component | Purpose |
|---|---|
| AgentTimeline | Renders SSE events with expandable steps |
| EvidenceCard | Kind icon, summary, source link, popover details |
| ConfidenceBadge | Color by threshold (green, amber, red) |
| CostLatencyBar | Cost and latency for the incident |
| GuardrailBadge | Type and action |
| MetricsTable and DeltaChip | Eval numbers with change vs baseline |
| ApprovalPanel | Approve/reject with confirmation |

## 8. User flows

**Flow A, live demo:** Shop Control, inject fault, alert forwarded, Live Incident timeline, report, approve dry-run.
**Flow B, quality proof:** Evaluation page, compare v1 vs v2, open a failed scenario, view trace.
**Flow C, security proof:** Security page, view block rate, run a live attack.

## 9. Visual guidelines

- Dark or light with one accent color; status colors only for meaning (green ok, amber caution, red failure).
- Monospace for logs and ids; short plain-language summaries above raw data.
- Never display raw secrets; redacted values show as `[REDACTED]`.
- Accessible contrast; do not rely on color alone (add icons or text).
- Keep each page loadable in under 2 seconds with paginated tables.

## 10. Next.js + TypeScript implementation notes

- **Project structure (App Router):**
  - `app/layout.tsx`: Root layout with dark/light theme provider, global nav sidebar.
  - `app/page.tsx`: Live Incident (main triage workspace).
  - `app/incidents/page.tsx`: Historical incidents table.
  - `app/evaluation/page.tsx`: Benchmark comparisons, charts, drill-downs.
  - `app/security/page.tsx`: Red-team suite results and interactive attack testing.
  - `app/shop/page.tsx`: Demo fault injection panel.
- **Type safety:** Maintain strict TypeScript interfaces in `types/api.ts` mirroring backend Pydantic models (`Incident`, `Alert`, `Evidence`, `Hypothesis`, `Action`, `EvalRun`).
- **Real-time SSE streaming:** Use a React hook (`useIncidentStream`) leveraging standard `fetch` with `ReadableStream` or `EventSource` to stream SSE updates into state, smoothly appending timeline events without page re-renders.
- **Charts & Tables:** Recharts for responsive time-series charts (Prometheus metrics) and benchmark comparisons; accessible semantic tables styled with Tailwind CSS.
- **API client:** Centralized API client in `lib/api.ts` with error handling, typed responses, and abort controller support.

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

## 10. Next.js + TypeScript implementation notes (Implemented)

- **Project structure (Next.js 16 App Router + BFF Auth Proxy):**
  - `app/layout.tsx`: Root layout wrapping `ThemeProvider` and persistent `AppShell` (`AppSidebar` + `TopBar`) across routes.
  - `app/api/v1/[...path]/route.ts`: Server-side BFF proxy injecting `X-API-Key` from server env `API_KEY` and streaming SSE to the browser.
  - `app/page.tsx`: `/` Live Triage page (persists active incident across route switches and reloads via `?incident=<id>` and `sessionStorage`).
  - `app/incidents/page.tsx`: `/incidents` persistent SQLite incident history table; clicking a row navigates to `/incidents/[id]`.
  - `app/incidents/[id]/page.tsx`: `/incidents/[id]` shareable detail & replay view for a saved incident.
  - `app/evaluation/page.tsx`: `/evaluation` benchmark scorecard loaded from `/api/v1/evals`.
  - `app/security/page.tsx`: `/security` adversarial red-team matrix loaded from `/api/v1/redteam`.
  - `app/shop/page.tsx`: `/shop` demo microservices topology summary.
- **Outcome Verification & Memory Feedback:** `ReportView` (`Correct diagnosis` / `Wrong diagnosis`) and `AbstainedPanel` (`Good abstention` / `Missed outage`) submit `POST /api/v1/incidents/{id}/feedback`, feeding both episodic `memory_agent` recall and `evals/score_live.py`. `AgentTimeline` includes `Memory agent` alongside `Metrics`, `Logs`, and `Runbook` agents, and `CitationSheet` inspects `ev_mem_*` episodes alongside telemetry and KB chunks.
- **Type safety:** Maintain strict TypeScript interfaces in `types/api.ts` mirroring backend models (`IncidentDetail`, `Alert`, `Evidence`, `Hypothesis`, `Action`, `IncidentFeedback`, `EvalRunMetrics`).
- **Real-time SSE streaming:** `hooks/useIncidentStream.ts` hydrates saved incident state via `GET /api/v1/incidents/{id}` first, then opens `EventSource` to `/api/v1/incidents/{id}/stream` while an incident is non-terminal.
- **API client:** Same-origin `/api/v1/*` client in `lib/api.ts` (leaves `NEXT_PUBLIC_API_URL` empty so browser requests never bypass the BFF proxy).

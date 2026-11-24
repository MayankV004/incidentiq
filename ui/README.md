# IncidentIQ Control Plane Dashboard (Frontend)

> **Real-Time SRE Autonomous On-Call & Incident Control Dashboard**  
> Powered by **Next.js 16 (App Router + Turbopack)**, **React 19**, **Tailwind CSS 4**, and **Motion**.

---

## 1. Overview

The `ui/` directory houses the real-time observability and intervention control plane for **IncidentIQ**. It visualizes the multi-agent reasoning steps of LangGraph, streams telemetry citations via Server-Sent Events (SSE), provides one-click human-in-the-loop remediation signing, and displays dynamic evaluation benchmarks and adversarial security suites.

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ IncidentIQ Control Plane                                      [● Live] [Theme ☼] │
├───────────────┬───────────────────────────────────┬───────────────────────────────┤
│ Navigation    │ Real-Time Agent Reasoning Stream   │ Root-Cause Diagnosis & Report │
│               │                                   │                               │
│ [⚡ Live Run]  │ 1. [PASS] Input Guardrail         │ Hypothesis: Orders DB pool    │
│ [📋 History]  │ 2. [EXEC] Metrics Specialist      │ Confidence: 92% (Grounded)    │
│ [📊 Evals]    │ 3. [EXEC] Logs Specialist         │ ──────────── Evidence ─────── │
│ [🛡 Security] │ 4. [EXEC] Runbook RAG Specialist  │ [ev_prom_01] connection spikes│
│ [🏪 Shop Svc] │ 5. [PASS] Groundedness Guardrail  │ [ev_logs_03] pool acquisition │
│               │ 6. [WAIT] Human Approval Required │ [ev_kb_001] runbook match     │
│               │                                   │ [ Approve Remediation ⚡ ]    │
└───────────────┴───────────────────────────────────┴───────────────────────────────┘
```

---

## 2. Key Architectural Features

### ⚡ Server-Sent Events (SSE) Streaming
Instead of clunky polling intervals, the UI hooks into FastAPI's streaming pipeline via [`useIncidentStream.ts`](hooks/useIncidentStream.ts):
- Subscribes to `GET /v1/incidents/{id}/stream`.
- Progressively renders agent step transitions (`started`, `completed`, `failed`).
- Immediately reflects dynamic cost updates, latency counters, and token usage without page refetches.

### 🛡️ Human-in-the-Loop Capability Token Signing
When an agent proposes an infrastructure remediation action (e.g. database pool expansion or pod restarts), the UI renders an interactive cryptographic authorization prompt ([`ApprovalModal.tsx`](components/ApprovalModal.tsx)):
- Displays the target microservice, dry-run shell command, and safety rationale.
- Passes the cryptographically signed `approval_token` to `POST /v1/incidents/{id}/approval`.
- Captures dry-run execution receipts in real time.

### 🔍 Grounded Citation Drawer
Every claim made in an agent's hypothesis is backed by an evidence key (`ev_prom_*`, `ev_logs_*`, `ev_kb_*`).
- Clicking any citation opens the slide-over [`CitationSheet.tsx`](components/CitationSheet.tsx).
- Inspect raw Prometheus Z-score anomalies, cluster-extracted log payloads, or indexed runbook passages.

### 🎨 Design System & Visual Polish
- **Color Palette:** High-contrast dark engineering console with electric neon lime accents (`#a3e635` / `lime-400`).
- **Sidebar UX:** Notion-style collapsible navigation rail ([`AppSidebar.tsx`](components/AppSidebar.tsx)) with tooltip hints in collapsed mode.
- **Theme Engine:** Zero-flicker dark/light mode toggle with native **View Transitions API** circular radial ripple originating from the cursor's click position ([`ThemeContext.tsx`](context/ThemeContext.tsx)).

---

## 3. Directory & Component Structure

```
ui/
├── app/
│   ├── globals.css         # Tailwind CSS v4 variables & @custom-variant dark config
│   ├── layout.tsx          # Root HTML layout with ThemeProvider and font optimization
│   └── page.tsx            # Main shell rendering navigation, TopBar, and view switcher
├── components/
│   ├── AppSidebar.tsx      # Collapsible navigation rail (Live, History, Evals, Security, Shop)
│   ├── TopBar.tsx          # Scenario picker dropdown, trigger button, and status indicators
│   ├── ScenarioPicker.tsx  # Preset benchmark scenario selector (001 - 008)
│   ├── AgentTimeline.tsx   # Visualized LangGraph DAG step progression with pulsing nodes
│   ├── ReportView.tsx      # Multi-tab diagnosis panel (Hypothesis, Evidence, Steps, Tracing)
│   ├── CitationSheet.tsx   # Slide-over evidence viewer for metrics, logs, and runbooks
│   ├── ApprovalModal.tsx   # Cryptographic remediation signing dialog
│   ├── AbstainedPanel.tsx  # Honest abstention banner shown when confidence < threshold
│   ├── FailedPanel.tsx     # Resilient error boundary banner for system interruptions
│   └── tabs/
│       ├── LiveView.tsx        # Split-pane active triage console (Timeline + Report)
│       ├── IncidentsView.tsx   # Persistent database history table (loaded from SQLite)
│       ├── EvaluationView.tsx  # Versioned IncidentBench-mini scorecard and metric gauges
│       ├── SecurityView.tsx    # Adversarial red-team test matrix and defense results
│       └── ShopView.tsx        # Microservices topology and live container health checks
├── context/
│   └── ThemeContext.tsx    # View Transitions radial-ripple theme management
├── hooks/
│   └── useIncidentStream.ts# React SSE subscriber for real-time LangGraph event streaming
└── lib/
    ├── api.ts              # Strongly typed REST client for the FastAPI control plane
    └── utils.ts            # Formatting helpers (currencies, timestamps, Tailwind merge)
```

---

## 4. Getting Started

### Prerequisites
- Node.js 18.18+ or 20+
- `pnpm` (recommended), `npm`, or `bun`

### Installation
```bash
cd ui
pnpm install
```

### Local Development Server
Start the Turbopack development server on port 3000:
```bash
pnpm dev
```
Open **`http://localhost:3000`** in your browser. Ensure the backend FastAPI service is running concurrently on port 8000 (`uv run uvicorn incidentiq.api.main:app --port 8000`).

### Production Build & Linting
```bash
# Verify TypeScript types and build optimized static assets
pnpm build

# Run ESLint validation
pnpm lint
```

---

## 5. Environment Variables

The dashboard works out-of-the-box with standard defaults. If your backend runs on a custom host or port, configure `ui/.env.local`:

```ini
# Backend API Base URL (defaults to http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

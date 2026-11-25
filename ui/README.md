# IncidentIQ Web Control Plane (`ui/`)

This folder holds the Next.js 16 web dashboard for IncidentIQ.
It uses React 19, Tailwind CSS 4, Motion, and a server-side proxy so browser clients never see your API key.

---

## 1. Routes and Features

* **`/` ([`app/page.tsx`](app/page.tsx)):** Live Triage page. You pick a scenario, launch an investigation, watch steps stream live, and approve or reject dry-run actions. Active incidents stay saved in `?incident=<id>` and `sessionStorage` when you reload or switch pages.
* **`/incidents` ([`app/incidents/page.tsx`](app/incidents/page.tsx)):** Table of saved investigations loaded from SQLite. Click any row to open `/incidents/[id]`.
* **`/incidents/[id]` ([`app/incidents/[id]/page.tsx`](app/incidents/%5Bid%5D/page.tsx)):** Replay or approve a specific saved incident.
* **`/evaluation` ([`app/evaluation/page.tsx`](app/evaluation/page.tsx)):** Scorecard loaded from `/api/v1/evals`.
* **`/security` ([`app/security/page.tsx`](app/security/page.tsx)):** Red-team matrix loaded from `/api/v1/redteam`.
* **`/shop` ([`app/shop/page.tsx`](app/shop/page.tsx)):** Summary of the internal `shop/` demo services.

### Key Architectural Pieces
* **Server-Side Auth Proxy ([`app/api/v1/[...path]/route.ts`](app/api/v1/%5B...path%5D/route.ts)):** Browser code calls same-origin `/api/v1/*`. The Next.js server adds `X-API-Key` from server env `API_KEY` and forwards requests and **SSE** streams to `API_INTERNAL_URL`.
* **Live SSE Hook ([`hooks/useIncidentStream.ts`](hooks/useIncidentStream.ts)):** Fetches saved incident state first, then opens an `EventSource` to `/api/v1/incidents/{id}/stream` while an incident is still running.
* **Approval Safety ([`components/ApprovalModal.tsx`](components/ApprovalModal.tsx), [`components/tabs/LiveView.tsx`](components/tabs/LiveView.tsx)):** Sends `{ decision, approval_id }` (never raw HMAC capability tokens) to `POST /api/v1/incidents/{id}/approval`.
* **Citation Drawer ([`components/CitationSheet.tsx`](components/CitationSheet.tsx)):** Opens raw metrics, sanitized logs, and runbook chunks when you click `ev_metric_*`, `ev_log_*`, or `ev_kb_*` pills.

---

## 2. Directory Structure

```text
ui/
├── app/
│   ├── api/v1/[...path]/route.ts # Server proxy injecting X-API-Key + SSE passthrough
│   ├── evaluation/page.tsx       # /evaluation route
│   ├── incidents/page.tsx        # /incidents history route
│   ├── incidents/[id]/page.tsx   # /incidents/[id] detail route
│   ├── security/page.tsx         # /security matrix route
│   ├── shop/page.tsx             # /shop topology route
│   ├── globals.css               # Tailwind CSS v4 config
│   ├── layout.tsx                # Root HTML layout + ThemeProvider + AppShell
│   ├── page.tsx                  # / Live Triage route
│   ├── robots.ts                 # Robots metadata
│   └── sitemap.ts                # Sitemap for app routes
├── components/
│   ├── AppShell.tsx              # Persistent sidebar + top bar shell across routes
│   ├── AppSidebar.tsx            # Collapsible navigation links
│   ├── TopBar.tsx                # Breadcrumbs, live status pill, and theme toggle
│   ├── ScenarioPicker.tsx        # Scenario selector (001–008)
│   ├── AgentTimeline.tsx         # Step-by-step investigation timeline
│   ├── ReportView.tsx            # Report, Evidence, and Trace tabs + approval UI
│   ├── CitationSheet.tsx         # Slide-over evidence inspector
│   ├── ApprovalModal.tsx         # Dry-run approval confirmation modal
│   ├── AbstainedPanel.tsx        # Abstention view for weak or normal telemetry
│   ├── FailedPanel.tsx           # Failure and budget_exceeded error view
│   └── tabs/
│       ├── LiveView.tsx
│       ├── IncidentsView.tsx
│       ├── EvaluationView.tsx
│       ├── SecurityView.tsx
│       └── ShopView.tsx
├── context/ThemeContext.tsx      # Dark/light theme toggle (View Transitions API)
├── hooks/useIncidentStream.ts    # Fetch + SSE hydration hook
├── lib/api.ts                    # Same-origin /api/v1/* REST helpers
├── lib/utils.ts                  # Formatting helpers
└── types/api.ts                  # TypeScript API types
```

---

## 3. Getting Started

### Prerequisites
* Node.js 22+ and `pnpm`

### Install & Run Locally

1. Install packages from the lockfile:
   ```bash
   cd ui
   CI=true pnpm install --frozen-lockfile
   ```

2. Start the FastAPI backend first on port `8000` (from the repo root, see [`../README.md`](../README.md)).

3. Start the Next.js server with `API_INTERNAL_URL` and the matching `API_KEY`:
   ```bash
   set -a && source ../.env && set +a
   API_INTERNAL_URL=http://127.0.0.1:8000 pnpm dev
   ```
   Open `http://localhost:3000`.

### Lint, Typecheck & Build

```bash
pnpm lint
./node_modules/.bin/tsc --noEmit
NEXT_PUBLIC_API_URL= pnpm build
```

---

## 4. Environment Variables

* `API_KEY` (server-side, required): Secret sent upstream in `X-API-Key` by the `/api/v1/*` proxy.
* `API_INTERNAL_URL` (server-side, default `http://incidentiq-api:8000`): FastAPI base URL. Set to `http://127.0.0.1:8000` outside Docker.
* `NEXT_PUBLIC_API_URL` (client build-time, keep empty `""`): Leave unset or empty so browser requests stay same-origin (`/api/v1/*`). Do not set it to `http://localhost:8000` in `ui/.env.local`, or browser calls will bypass `/api/v1` and fail with 404.

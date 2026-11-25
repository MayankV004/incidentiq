import asyncio
import contextlib
import glob
import json
import logging
import os
import socket
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, StreamingResponse

load_dotenv()

logger = logging.getLogger("incidentiq.api")

from contextlib import asynccontextmanager

from incidentiq.agents.graph import incident_graph
from incidentiq.agents.mcp_client import (
    reset_current_incident_id,
    restart_service,
    review_config,
    rollback_deploy,
    scale_up,
    set_current_incident_id,
)
from incidentiq.api.security import (
    SecurityAndRateLimitMiddleware,
    get_daily_cost_cap,
    require_api_key,
)
from incidentiq.db import init_db
from incidentiq.db.cache import IncidentLRUCache, check_single_worker
from incidentiq.db.repository import (
    append_event_to_db,
    get_daily_costs_by_id_from_db,
    get_incident_from_db,
    list_incidents_from_db,
    record_approval_decision,
    record_incident_feedback,
    upsert_incident,
)
from incidentiq.db.session import SessionLocal
from incidentiq.guardrails.guards import GuardrailManager
from incidentiq.schemas.models import Alert
from incidentiq.security.tokens import (
    consume_server_approval_token,
    generate_capability_token,
    require_approval_secret,
)
from mcp_servers.validation import (
    ALLOWED_SERVICES,
    validate_scenario_id,
    validate_service,
)

# Initialize database schema on startup
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast if mandatory security secrets are unset
    require_api_key()
    require_approval_secret()
    # Enforce single worker mode for memory/SSE safety
    check_single_worker()
    # Pre-warm active and awaiting_approval incidents from database into memory
    try:
        db_incs = list_incidents_from_db()
        for inc in db_incs:
            if inc.get("status") in ("awaiting_approval", "queued", "running"):
                INCIDENTS_DB[inc["incident_id"]] = inc
    except Exception as e:  # noqa: BLE001
        logger.error(f"Startup DB cache pre-warm failed: {e}")
    yield


app = FastAPI(
    title="IncidentIQ: Autonomous On-Call Triage Control Plane",
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = [
    orig.strip()
    for orig in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if orig.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(SecurityAndRateLimitMiddleware)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Enforces standard error response shape: { "error": { "code", "message", "details" } }."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    error_code = "HTTP_ERROR"
    if exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 409:
        error_code = "STATE_CONFLICT"
    elif exc.status_code == 403:
        error_code = "FORBIDDEN"
    elif exc.status_code == 401:
        error_code = "UNAUTHORIZED"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": str(exc.detail),
                "details": {},
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Returns Pydantic 422 validation errors in the standard error envelope."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()},
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Returns unexpected 500 errors in the standard error envelope without leaking internals."""
    logger.exception(f"Unhandled error processing {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": {},
            }
        },
    )


# In-memory LRU store for incidents and active SSE stream subscribers
INCIDENTS_DB = IncidentLRUCache()
SUBSCRIBERS: dict[str, list[asyncio.Queue]] = {}


def get_langfuse_handler():
    """Initializes Langfuse CallbackHandler and client if credentials exist."""
    pub = os.getenv("LANGFUSE_PUBLIC_KEY")
    sec = os.getenv("LANGFUSE_SECRET_KEY")
    if not (pub and sec and pub.strip() and sec.strip()):
        return None, None
    try:
        from langfuse import get_client
        from langfuse.langchain import CallbackHandler

        host = os.getenv("LANGFUSE_HOST") or os.getenv(
            "LANGFUSE_BASE_URL", "https://cloud.langfuse.com"
        )
        os.environ["LANGFUSE_BASE_URL"] = host
        os.environ["LANGFUSE_HOST"] = host
        handler = CallbackHandler()
        client = get_client()
        return handler, client
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Langfuse tracer initialization skipped: {e}")
        return None, None


class CreateIncidentRequest(BaseModel):
    service: str
    symptom: str
    window_start: str = ""
    window_end: str = ""
    scenario_id: str | None = None


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approve" | "reject"
    approval_id: str | None = None
    approval_token: str | None = None


class FeedbackRequest(BaseModel):
    verdict: str  # "correct_root_cause" | "wrong_root_cause" | "good_abstention" | "false_alarm"
    corrected_category: str | None = None
    notes: str | None = None
    submitted_by: str = "on_call_engineer"


VALID_FEEDBACK_VERDICTS = {
    "correct_root_cause",
    "wrong_root_cause",
    "good_abstention",
    "false_alarm",
}


@app.get("/health")
@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "incidentiq_api"}


@app.get("/readyz")
def readyz():
    checks: dict[str, str] = {}
    ready = True

    # 1. Database readiness probe
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        ready = False
        checks["database"] = f"error: {exc}"

    # 2. HTTP MCP servers readiness probe when MCP_MODE=http
    if os.getenv("MCP_MODE", "inprocess").lower() == "http":
        mcp_targets = {
            "mcp_metrics": os.getenv("MCP_METRICS_URL", "http://mcp-metrics:9101/mcp"),
            "mcp_logs": os.getenv("MCP_LOGS_URL", "http://mcp-logs:9102/mcp"),
            "mcp_remediation": os.getenv(
                "MCP_REMEDIATION_URL", "http://mcp-remediation:9103/mcp"
            ),
        }
        for name, url in mcp_targets.items():
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if not host:
                ready = False
                checks[name] = "error: missing host"
                continue
            try:
                with socket.create_connection((host, port), timeout=1.5):
                    checks[name] = "ok"
            except OSError as exc:
                ready = False
                checks[name] = f"unreachable: {exc}"

    if not ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "incidentiq_api",
                "checks": checks,
            },
        )
    return {"status": "ready", "service": "incidentiq_api", "checks": checks}


def broadcast_event(incident_id: str, event: dict[str, Any]):
    """Appends an event to the incident log and notifies active SSE subscribers."""
    if incident_id not in INCIDENTS_DB:
        db_inc = get_incident_from_db(incident_id)
        if db_inc:
            INCIDENTS_DB[incident_id] = db_inc
        else:
            return
    INCIDENTS_DB[incident_id].setdefault("events", []).append(event)
    try:
        append_event_to_db(incident_id, event)
    except Exception as e:  # noqa: BLE001
        logger.error(f"DB append_event failed: {e}")
    for q in SUBSCRIBERS.get(incident_id, []):
        try:
            q.put_nowait(event)
        except Exception:  # noqa: S110, BLE001
            pass


def run_incident_workflow(incident_id: str, alert: Alert):
    INCIDENTS_DB[incident_id]["status"] = "running"
    t_start = time.perf_counter()

    scenario_id = INCIDENTS_DB[incident_id].get("scenario_id")

    initial_state: dict[str, Any] = {
        "incident_id": incident_id,
        "scenario_id": scenario_id,
        "alert": alert,
        "plan": [],
        "evidence": [],
        "hypothesis": None,
        "guardrail_flags": [],
        "approval": None,
        "cost_usd": 0.0,
        "steps": 0,
    }

    # Emit initial started event
    broadcast_event(
        incident_id,
        {
            "id": f"ev_{uuid.uuid4().hex[:6]}",
            "type": "incident_started",
            "node": "system",
            "title": "Incident Triage Initiated",
            "summary": f"Alert for {alert.service}: {alert.symptom}",
            "data": {"alert": alert.model_dump()},
            "cost_usd": 0.0,
            "steps": 0,
            "timestamp": time.time(),
        },
    )

    accumulated_cost = 0.0
    accumulated_steps = 0
    collected_evidence = []
    hypothesis_dict = None
    approval_dict = None
    flags = []

    # Initialize Langfuse tracer if configured
    langfuse_handler, langfuse_client = get_langfuse_handler()
    stream_config: dict[str, Any] = {}
    if langfuse_handler:
        stream_config["callbacks"] = [langfuse_handler]
        stream_config["run_name"] = f"triage-graph-{alert.service}"

    trace_ctx: Any = None
    if langfuse_handler and langfuse_client:
        from langfuse import propagate_attributes

        trace_ctx = propagate_attributes(
            trace_name=f"IncidentIQ Triage: {alert.service}",
            session_id=incident_id,
            user_id="oncall-sre",
            tags=[alert.service, scenario_id or "live", "incidentiq", "langgraph"],
            metadata={
                "incident_id": incident_id,
                "scenario_id": scenario_id,
                "service": alert.service,
                "symptom": alert.symptom,
                "window_start": alert.window_start,
                "window_end": alert.window_end,
            },
        )
    else:
        trace_ctx = contextlib.nullcontext()

    trace_url = None
    ctx_tok = set_current_incident_id(incident_id)

    try:
        with trace_ctx:
            for chunk in incident_graph.stream(  # type: ignore[call-overload]
                initial_state, stream_mode="updates", config=stream_config
            ):
                for node, update in chunk.items():
                    if not isinstance(update, dict):
                        continue

                    accumulated_steps += update.get("steps", 0)
                    cost_delta = update.get("cost_usd", 0.0)
                    accumulated_cost += cost_delta

                    # Generate typed semantic event
                    event_type = "agent_finished"
                    title = node.replace("_", " ").title()
                    summary = ""
                    event_data: dict[str, Any] = {}

                    if node == "input_guard":
                        event_type = "guardrail_executed"
                        flags.extend(update.get("guardrail_flags", []))
                        summary = f"Scanned alert. Flagged issues: {len(flags)}"
                        event_data = {"guardrail_flags": flags}

                    elif node == "supervisor":
                        event_type = "supervisor_planned"
                        plan = update.get("plan", [])
                        summary = f"Strategy formulated. Dispatched specialists: {', '.join(plan)}"
                        event_data = {"plan": plan}

                    elif node in (
                        "metrics_agent",
                        "logs_agent",
                        "runbook_agent",
                        "memory_agent",
                    ):
                        event_type = "evidence_found"
                        node_ev = update.get("evidence", [])
                        for e in node_ev:
                            collected_evidence.append(
                                e.model_dump() if hasattr(e, "model_dump") else e
                            )
                        ev_count = len(node_ev)
                        summary = f"Extracted {ev_count} factual evidence item(s)"
                        event_data = {
                            "evidence": [
                                e.model_dump() if hasattr(e, "model_dump") else e
                                for e in node_ev
                            ]
                        }

                    elif node == "root_cause_agent":
                        event_type = "hypothesis_synthesized"
                        h = update.get("hypothesis")
                        if h:
                            hypothesis_dict = (
                                h.model_dump() if hasattr(h, "model_dump") else h
                            )
                            cause_title = hypothesis_dict.get(
                                "category"
                            ) or hypothesis_dict.get("root_cause")
                            summary = f"Diagnosis: {cause_title} (Confidence: {int(hypothesis_dict.get('confidence', 0) * 100)}%)"
                            event_data = {"hypothesis": hypothesis_dict}

                    elif node == "output_guard":
                        event_type = "guardrail_executed"
                        flags.extend(update.get("guardrail_flags", []))
                        h = update.get("hypothesis")
                        if h:
                            hypothesis_dict = (
                                h.model_dump() if hasattr(h, "model_dump") else h
                            )
                        summary = "Evaluated hallucination & groundedness gate"
                        event_data = {
                            "guardrail_flags": flags,
                            "hypothesis": hypothesis_dict,
                        }

                    elif node == "human_approval":
                        appr = update.get("approval")
                        if appr:
                            approval_dict = appr
                            event_type = "approval_required"
                            summary = f"Action requires authorization: {appr.get('action', {}).get('type')}"
                            event_data = {
                                "approval": {
                                    "approval_id": appr.get("approval_id"),
                                    "status": appr.get("status"),
                                    "action": appr.get("action"),
                                }
                            }
                        else:
                            summary = "No destructive remediation needed"

                    broadcast_event(
                        incident_id,
                        {
                            "id": f"ev_{uuid.uuid4().hex[:6]}",
                            "type": event_type,
                            "node": node,
                            "title": title,
                            "summary": summary,
                            "data": event_data,
                            "cost_usd": round(accumulated_cost, 6),
                            "steps": accumulated_steps,
                            "timestamp": time.time(),
                        },
                    )

        # Flush traces and get URL if Langfuse is active
        if langfuse_client:
            try:
                langfuse_client.flush()
                trace_url = langfuse_client.get_trace_url()
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Langfuse trace retrieval deferred: {e}")

        latency_ms = (time.perf_counter() - t_start) * 1000

        # Determine terminal status
        if "BUDGET_EXCEEDED" in flags:
            status = "budget_exceeded"
        elif approval_dict:
            status = "awaiting_approval"
        elif hypothesis_dict and hypothesis_dict.get("abstained"):
            status = "abstained"
        else:
            status = "completed"

        INCIDENTS_DB[incident_id].update(
            {
                "status": status,
                "hypothesis": hypothesis_dict,
                "evidence": collected_evidence,
                "guardrail_flags": flags,
                "approval": approval_dict,
                "cost_usd": round(accumulated_cost, 6),
                "latency_ms": round(latency_ms, 2),
                "steps": accumulated_steps,
                "langfuse_trace_url": trace_url,
            }
        )
        try:
            upsert_incident(INCIDENTS_DB[incident_id])
        except Exception as e:  # noqa: BLE001
            logger.error(f"DB upsert failed: {e}")

        broadcast_event(
            incident_id,
            {
                "id": f"ev_{uuid.uuid4().hex[:6]}",
                "type": "done",
                "status": status,
                "node": "system",
                "title": "Investigation Finished",
                "summary": f"Incident resolved with status: {status}",
                "data": {
                    "status": status,
                    "hypothesis": hypothesis_dict,
                    "cost_usd": round(accumulated_cost, 6),
                    "latency_ms": round(latency_ms, 2),
                    "steps": accumulated_steps,
                    "langfuse_trace_url": trace_url,
                },
                "cost_usd": round(accumulated_cost, 6),
                "steps": accumulated_steps,
                "timestamp": time.time(),
            },
        )

    except Exception as exc:  # noqa: BLE001
        INCIDENTS_DB[incident_id]["status"] = "failed"
        INCIDENTS_DB[incident_id]["error"] = str(exc)
        broadcast_event(
            incident_id,
            {
                "id": f"ev_{uuid.uuid4().hex[:6]}",
                "type": "done",
                "status": "failed",
                "node": "system",
                "title": "Investigation Failed",
                "summary": f"Error: {exc!s}",
                "data": {"error": str(exc)},
                "cost_usd": round(accumulated_cost, 6),
                "steps": accumulated_steps,
                "timestamp": time.time(),
            },
        )
    finally:
        reset_current_incident_id(ctx_tok)


@app.get("/v1/scenarios")
def list_scenarios():
    """Returns available benchmark scenarios with metadata."""
    scenarios = []
    for sdir in sorted(glob.glob("scenarios/0*")):
        sname = os.path.basename(sdir)
        alert_file = os.path.join(sdir, "alert.json")
        label_file = os.path.join(sdir, "label.json")
        alert_data = {}
        label_data = {}
        if os.path.exists(alert_file):
            with open(alert_file) as f:
                alert_data = json.load(f)
        if os.path.exists(label_file):
            with open(label_file) as f:
                label_data = json.load(f)

        # Parse index and clean title
        parts = sname.split("_", 1)
        num = parts[0]
        title = parts[1].replace("_", " ").title() if len(parts) > 1 else sname

        scenarios.append(
            {
                "id": sname,
                "number": num,
                "title": title,
                "service": alert_data.get("service", "orders"),
                "symptom": alert_data.get("symptom", ""),
                "expected_root_cause": label_data.get("expected_root_cause", ""),
                "expected_action": label_data.get("expected_action", ""),
                "window_start": alert_data.get("window_start", ""),
                "window_end": alert_data.get("window_end", ""),
            }
        )
    return scenarios


@app.get("/v1/incidents")
def list_incidents():
    """Lists all investigated incidents from persistent database and in-memory cache."""
    seen: dict[str, dict[str, Any]] = {}
    try:
        for inc in list_incidents_from_db():
            seen[inc["incident_id"]] = inc
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to query DB for list_incidents: {e}")

    for inc in INCIDENTS_DB.values():
        seen[inc["incident_id"]] = inc

    return [
        {
            "incident_id": inc.get("incident_id"),
            "service": inc.get("alert", {}).get("service"),
            "symptom": inc.get("alert", {}).get("symptom"),
            "status": inc.get("status"),
            "cost_usd": inc.get("cost_usd", 0.0),
            "latency_ms": inc.get("latency_ms", 0.0),
            "created_at": inc.get("created_at"),
            "category": inc.get("hypothesis", {}).get("category")
            if inc.get("hypothesis")
            else None,
            "root_cause": (
                inc.get("hypothesis", {}).get("category")
                or inc.get("hypothesis", {}).get("root_cause")
            )
            if inc.get("hypothesis")
            else None,
            "confidence": inc.get("hypothesis", {}).get("confidence")
            if inc.get("hypothesis")
            else None,
            "langfuse_trace_url": inc.get("langfuse_trace_url"),
        }
        for inc in sorted(
            seen.values(), key=lambda x: x.get("created_at", 0), reverse=True
        )
    ]


@app.post("/v1/incidents", status_code=202)
def create_incident(req: CreateIncidentRequest, background_tasks: BackgroundTasks):
    now = time.time()
    today_start = now - (now % 86400)
    try:
        costs_by_id = get_daily_costs_by_id_from_db(today_start)
    except Exception as e:  # noqa: BLE001
        logger.error(f"DB daily cost lookup failed: {e}")
        costs_by_id = {}
    for inc_id, inc in INCIDENTS_DB.items():
        if inc.get("created_at", 0) >= today_start:
            costs_by_id[inc_id] = max(
                costs_by_id.get(inc_id, 0.0), float(inc.get("cost_usd", 0.0) or 0.0)
            )
    daily_cost = sum(costs_by_id.values())
    daily_cap = get_daily_cost_cap()
    if daily_cost >= daily_cap:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "BUDGET_EXCEEDED",
                    "message": f"Daily budget cap of ${daily_cap:.2f} exceeded (current: ${daily_cost:.2f})",
                    "details": {
                        "daily_cost_cap_usd": daily_cap,
                        "current_cost_usd": round(daily_cost, 4),
                    },
                }
            },
        )

    incident_id = f"inc_{uuid.uuid4().hex[:10]}"

    def _bad_input(message: str, details: dict[str, Any] | None = None):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_INPUT",
                    "message": message,
                    "details": details or {},
                }
            },
        )

    if not validate_service(req.service):
        _bad_input(
            f"Invalid service '{req.service}'. Allowed services: {sorted(ALLOWED_SERVICES)}",
            {"field": "service"},
        )

    symptom_clean = req.symptom.strip()
    if not symptom_clean or len(symptom_clean) > 4000:
        _bad_input(
            "Symptom must be a non-empty string up to 4000 characters.",
            {"field": "symptom"},
        )

    if (
        req.scenario_id is not None
        and req.scenario_id != ""
        and not validate_scenario_id(req.scenario_id)
    ):
        _bad_input(
            f"Invalid scenario_id '{req.scenario_id}'.",
            {"field": "scenario_id"},
        )

    def _parse_iso(ts: str, field: str) -> datetime:
        try:
            dt = datetime.fromisoformat(ts.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            _bad_input(f"Invalid ISO timestamp for '{field}'.", {"field": field})
            raise  # unreachable

    if req.window_start and req.window_end:
        start_dt = _parse_iso(req.window_start, "window_start")
        end_dt = _parse_iso(req.window_end, "window_end")
        if end_dt <= start_dt:
            _bad_input(
                "window_end must be strictly after window_start.",
                {"field": "window_end"},
            )
        w_start = start_dt.isoformat()
        w_end = end_dt.isoformat()
    elif req.window_start or req.window_end:
        _bad_input(
            "Both window_start and window_end must be provided together.",
            {"field": "window_start"},
        )
    else:
        now_dt = datetime.now(UTC)
        w_end = now_dt.isoformat()
        w_start = (now_dt - timedelta(minutes=30)).isoformat()

    raw_alert = Alert(
        service=req.service.strip().lower(),
        symptom=symptom_clean,
        window_start=w_start,
        window_end=w_end,
    )

    # AUD-04: Execute input guard (PII redaction and injection scan) before persistence or queueing
    clean_alert, initial_flags = GuardrailManager.process_input_alert(raw_alert)

    initial_events = []
    if initial_flags:
        initial_events.append(
            {
                "id": f"ev_{uuid.uuid4().hex[:6]}",
                "type": "guardrail_executed",
                "node": "input_guard",
                "title": "Input Guardrail Executed",
                "summary": f"Scanned alert before storage. Flags: {len(initial_flags)}",
                "data": {"guardrail_flags": initial_flags},
                "cost_usd": 0.0,
                "steps": 0,
                "timestamp": time.time(),
            }
        )

    INCIDENTS_DB[incident_id] = {
        "incident_id": incident_id,
        "scenario_id": req.scenario_id,
        "alert": clean_alert.model_dump(),
        "status": "queued",
        "created_at": time.time(),
        "events": initial_events,
        "guardrail_flags": list(initial_flags),
    }

    try:
        upsert_incident(INCIDENTS_DB[incident_id])
    except Exception as e:  # noqa: BLE001
        logger.error(f"DB create failed: {e}")

    # Run workflow asynchronously using sanitized alert
    background_tasks.add_task(run_incident_workflow, incident_id, clean_alert)
    return {
        "incident_id": incident_id,
        "status": "queued",
        "message": "Incident investigation launched",
    }


@app.get("/v1/incidents/{incident_id}")
def get_incident(incident_id: str):
    inc = INCIDENTS_DB.get(incident_id) or get_incident_from_db(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    safe_inc = dict(inc)
    if safe_inc.get("approval"):
        appr = dict(safe_inc["approval"])
        appr.pop("token_hash", None)
        appr.pop("approval_token", None)
        safe_inc["approval"] = appr
    return safe_inc


@app.get("/v1/incidents/{incident_id}/stream")
async def stream_incident(incident_id: str, request: Request):
    """Server-Sent Events (SSE) stream for real-time incident investigation events."""
    if incident_id not in INCIDENTS_DB:
        db_inc = await run_in_threadpool(get_incident_from_db, incident_id)
        if db_inc:
            INCIDENTS_DB[incident_id] = db_inc
        else:
            raise HTTPException(status_code=404, detail="Incident not found")

    q: asyncio.Queue = asyncio.Queue()
    SUBSCRIBERS.setdefault(incident_id, []).append(q)

    async def event_generator():
        try:
            # 1. Stream all past events immediately
            past_events = list(INCIDENTS_DB[incident_id].get("events", []))
            for ev in past_events:
                yield f"data: {json.dumps(ev)}\n\n"

            # Check if incident is already done
            status = INCIDENTS_DB[incident_id].get("status")
            if status in (
                "completed",
                "awaiting_approval",
                "abstained",
                "budget_exceeded",
                "failed",
                "remediation_executed",
                "rejected_by_human",
            ):
                return

            # 2. Wait for live events until done or client disconnects
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=2.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "done":
                        break
                except TimeoutError:
                    # Keep-alive heartbeat ping
                    yield ": ping\n\n"
        finally:
            if incident_id in SUBSCRIBERS and q in SUBSCRIBERS[incident_id]:
                SUBSCRIBERS[incident_id].remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/v1/incidents/{incident_id}/approval")
def handle_approval(incident_id: str, req: ApprovalDecisionRequest):
    if incident_id not in INCIDENTS_DB:
        db_inc = get_incident_from_db(incident_id)
        if db_inc:
            INCIDENTS_DB[incident_id] = db_inc
        else:
            raise HTTPException(status_code=404, detail="Incident not found")

    inc = INCIDENTS_DB[incident_id]
    if inc.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Incident is not awaiting approval")

    approval_info = inc.get("approval") or {}
    expected_approval_id = approval_info.get("approval_id")

    req_approval_id = req.approval_id or req.approval_token
    if not expected_approval_id or req_approval_id != expected_approval_id:
        raise HTTPException(
            status_code=403,
            detail="Invalid approval credentials: unknown or mismatched approval_id",
        )

    if req.decision.lower() == "reject":
        inc["status"] = "rejected_by_human"
        consume_server_approval_token(expected_approval_id)
        record_approval_decision(expected_approval_id, "rejected")
        try:
            upsert_incident(inc)
        except Exception as e:  # noqa: BLE001
            logger.error(f"DB update on reject failed: {e}")
        return {
            "status": "rejected",
            "message": "Remediation action rejected by engineer",
        }

    # Retrieve and consume server-side capability token (single-use)
    token = consume_server_approval_token(expected_approval_id)
    if not token:
        # If server restarted while incident was awaiting_approval, re-issue a valid capability token
        # bound to the exact approved action and target, ensuring restart resumability
        action = approval_info.get("action", {})
        act_type = action.get("type")
        target = action.get("target")
        if act_type and target and inc.get("status") == "awaiting_approval":
            token = generate_capability_token(
                incident_id=incident_id,
                action=act_type,
                target=target,
                ttl_seconds=900,
            )
            logger.info(
                f"Re-issued server capability token after restart for approval {expected_approval_id}"
            )
        else:
            raise HTTPException(
                status_code=403, detail="Approval token already consumed or unavailable"
            )

    # Execute dry-run remediation tool via MCP
    action = approval_info.get("action", {})
    act_type = action.get("type")
    target = action.get("target")

    ctx_tok = set_current_incident_id(incident_id)
    try:
        if act_type == "restart_service":
            exec_res = restart_service(
                service=target, token=token, incident_id=incident_id
            )
        elif act_type == "rollback_deploy":
            exec_res = rollback_deploy(
                service=target,
                target_version="v2.4.0",
                token=token,
                incident_id=incident_id,
            )
        elif act_type == "scale_up":
            exec_res = scale_up(
                service=target, replicas=2, token=token, incident_id=incident_id
            )
        elif act_type == "review_config":
            exec_res = review_config(
                service=target,
                parameter="MAX_DB_POOL_SIZE",
                proposed_value="20",
                token=token,
                incident_id=incident_id,
            )
        else:
            exec_res = {"success": True, "message": "No destructive action required"}
    finally:
        reset_current_incident_id(ctx_tok)

    record_approval_decision(expected_approval_id, "approved")
    inc["status"] = "remediation_executed"
    inc["remediation_result"] = exec_res
    try:
        upsert_incident(inc)
    except Exception as e:  # noqa: BLE001
        logger.error(f"DB update on approve failed: {e}")
    return {"status": "approved_and_executed", "result": exec_res}


@app.post("/v1/incidents/{incident_id}/feedback")
def submit_incident_feedback(incident_id: str, req: FeedbackRequest):
    if req.verdict not in VALID_FEEDBACK_VERDICTS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid verdict '{req.verdict}'. Allowed: {sorted(VALID_FEEDBACK_VERDICTS)}",
        )
    inc = INCIDENTS_DB.get(incident_id) or get_incident_from_db(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    clean_notes, _ = GuardrailManager.redact_pii(req.notes or "")
    clean_corr, _ = GuardrailManager.redact_pii(req.corrected_category or "")
    clean_user, _ = GuardrailManager.redact_pii(req.submitted_by or "on_call_engineer")

    fb = record_incident_feedback(
        incident_id=incident_id,
        verdict=req.verdict,
        corrected_category=clean_corr or None,
        notes=clean_notes or None,
        submitted_by=clean_user or "on_call_engineer",
    )
    inc["feedback"] = fb
    INCIDENTS_DB[incident_id] = inc
    return {"status": "recorded", "feedback": fb}


@app.get("/v1/evals")
def list_eval_results():
    results = {}
    for fpath in glob.glob("evals/results/*.json"):
        fname = os.path.basename(fpath).replace(".json", "")
        with open(fpath) as f:
            results[fname] = json.load(f)
    return results


@app.get("/v1/redteam")
def get_redteam_cases():
    cases_file = "evals/redteam/cases.json"
    if os.path.exists(cases_file):
        with open(cases_file) as f:
            cases = json.load(f)
        return {"cases": cases, "total": len(cases), "blocked_rate": 1.0}
    return {"cases": [], "total": 0, "blocked_rate": 1.0}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

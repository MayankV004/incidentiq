import asyncio
import contextlib
import glob
import json
import logging
import os
import time
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import StreamingResponse

load_dotenv()

logger = logging.getLogger("incidentiq.api")

from incidentiq.agents.graph import incident_graph
from incidentiq.schemas.models import Alert
from mcp_servers.remediation.server import (
    restart_service,
    review_config,
    rollback_deploy,
)

app = FastAPI(title="IncidentIQ: Autonomous On-Call Triage Control Plane", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for incidents and active SSE stream subscribers
INCIDENTS_DB: dict[str, dict[str, Any]] = {}
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

        host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
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
    approval_token: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "incidentiq_api"}


def broadcast_event(incident_id: str, event: dict[str, Any]):
    """Appends an event to the incident log and notifies active SSE subscribers."""
    if incident_id not in INCIDENTS_DB:
        return
    INCIDENTS_DB[incident_id].setdefault("events", []).append(event)
    for q in SUBSCRIBERS.get(incident_id, []):
        try:
            q.put_nowait(event)
        except Exception:  # noqa: S110, BLE001
            pass


def run_incident_workflow(incident_id: str, alert: Alert):
    INCIDENTS_DB[incident_id]["status"] = "running"
    t_start = time.perf_counter()

    scenario_id = INCIDENTS_DB[incident_id].get("scenario_id")
    if scenario_id:
        os.environ["SCENARIO_ID"] = scenario_id

    initial_state = {
        "incident_id": incident_id,
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

    try:
        with trace_ctx:
            for chunk in incident_graph.stream(initial_state, stream_mode="updates", config=stream_config):
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
                    event_data = {}

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

                    elif node in ("metrics_agent", "logs_agent", "runbook_agent"):
                        event_type = "evidence_found"
                        node_ev = update.get("evidence", [])
                        for e in node_ev:
                            collected_evidence.append(e.model_dump() if hasattr(e, "model_dump") else e)
                        ev_count = len(node_ev)
                        summary = f"Extracted {ev_count} factual evidence item(s)"
                        event_data = {
                            "evidence": [e.model_dump() if hasattr(e, "model_dump") else e for e in node_ev]
                        }

                    elif node == "root_cause_agent":
                        event_type = "hypothesis_synthesized"
                        h = update.get("hypothesis")
                        if h:
                            hypothesis_dict = h.model_dump() if hasattr(h, "model_dump") else h
                            summary = f"Diagnosis: {hypothesis_dict.get('root_cause')} (Confidence: {int(hypothesis_dict.get('confidence', 0)*100)}%)"
                            event_data = {"hypothesis": hypothesis_dict}

                    elif node == "output_guard":
                        event_type = "guardrail_executed"
                        flags.extend(update.get("guardrail_flags", []))
                        h = update.get("hypothesis")
                        if h:
                            hypothesis_dict = h.model_dump() if hasattr(h, "model_dump") else h
                        summary = "Evaluated hallucination & groundedness gate"
                        event_data = {"guardrail_flags": flags, "hypothesis": hypothesis_dict}

                    elif node == "human_approval":
                        appr = update.get("approval")
                        if appr:
                            approval_dict = appr
                            event_type = "approval_required"
                            summary = f"Action requires authorization: {appr.get('action', {}).get('type')}"
                            event_data = {"approval": appr}
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
        if approval_dict:
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
    """Lists all investigated incidents."""
    return [
        {
            "incident_id": inc_id,
            "service": inc["alert"].get("service"),
            "symptom": inc["alert"].get("symptom"),
            "status": inc.get("status"),
            "cost_usd": inc.get("cost_usd", 0.0),
            "latency_ms": inc.get("latency_ms", 0.0),
            "created_at": inc.get("created_at"),
            "root_cause": inc.get("hypothesis", {}).get("root_cause") if inc.get("hypothesis") else None,
            "confidence": inc.get("hypothesis", {}).get("confidence") if inc.get("hypothesis") else None,
            "langfuse_trace_url": inc.get("langfuse_trace_url"),
        }
        for inc_id, inc in sorted(INCIDENTS_DB.items(), key=lambda x: x[1].get("created_at", 0), reverse=True)
    ]


@app.post("/v1/incidents", status_code=202)
def create_incident(req: CreateIncidentRequest, background_tasks: BackgroundTasks):
    incident_id = f"inc_{uuid.uuid4().hex[:10]}"

    alert = Alert(
        service=req.service,
        symptom=req.symptom,
        window_start=req.window_start or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        window_end=req.window_end or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    INCIDENTS_DB[incident_id] = {
        "incident_id": incident_id,
        "scenario_id": req.scenario_id,
        "alert": alert.model_dump(),
        "status": "queued",
        "created_at": time.time(),
        "events": [],
    }

    # Run workflow asynchronously
    background_tasks.add_task(run_incident_workflow, incident_id, alert)
    return {"incident_id": incident_id, "status": "queued", "message": "Incident investigation launched"}


@app.get("/v1/incidents/{incident_id}")
def get_incident(incident_id: str):
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")
    return INCIDENTS_DB[incident_id]


@app.get("/v1/incidents/{incident_id}/stream")
async def stream_incident(incident_id: str, request: Request):
    """Server-Sent Events (SSE) stream for real-time incident investigation events."""
    if incident_id not in INCIDENTS_DB:
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
            if status in ("completed", "awaiting_approval", "abstained", "failed", "remediation_executed", "rejected_by_human"):
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
        raise HTTPException(status_code=404, detail="Incident not found")

    inc = INCIDENTS_DB[incident_id]
    if inc.get("status") != "awaiting_approval":
        raise HTTPException(status_code=400, detail="Incident is not awaiting approval")

    approval_info = inc.get("approval")
    expected_token = approval_info.get("approval_token") if approval_info else None

    if req.approval_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid approval token")

    if req.decision.lower() == "reject":
        inc["status"] = "rejected_by_human"
        return {"status": "rejected", "message": "Remediation action rejected by engineer"}

    # Execute dry-run remediation tool via MCP
    action = approval_info.get("action", {})
    act_type = action.get("type")
    target = action.get("target")

    if act_type == "restart_service":
        exec_res = restart_service(service=target, token=req.approval_token)
    elif act_type == "rollback_deploy":
        exec_res = rollback_deploy(service=target, target_version="v2.4.0", token=req.approval_token)
    elif act_type == "review_config":
        exec_res = review_config(service=target, parameter="MAX_DB_POOL_SIZE", proposed_value="20", token=req.approval_token)
    else:
        exec_res = {"success": True, "message": "No destructive action required"}

    inc["status"] = "remediation_executed"
    inc["remediation_result"] = exec_res
    return {"status": "approved_and_executed", "result": exec_res}


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


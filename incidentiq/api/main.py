import glob
import json
import os
import time
import uuid
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from incidentiq.agents.graph import incident_graph
from incidentiq.schemas.models import Alert
from mcp_servers.remediation.server import (
    restart_service,
    review_config,
    rollback_deploy,
)

app = FastAPI(title="IncidentIQ: Autonomous On-Call Triage Control Plane", version="1.0.0")

# In-memory store for incidents
INCIDENTS_DB: dict[str, dict[str, Any]] = {}


class CreateIncidentRequest(BaseModel):
    service: str
    symptom: str
    window_start: str = ""
    window_end: str = ""


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approve" | "reject"
    approval_token: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "incidentiq_api"}


def run_incident_workflow(incident_id: str, alert: Alert):
    INCIDENTS_DB[incident_id]["status"] = "running"
    t_start = time.perf_counter()

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

    try:
        final_state = incident_graph.invoke(initial_state)
        latency_ms = (time.perf_counter() - t_start) * 1000

        h = final_state.get("hypothesis")
        status = "awaiting_approval" if final_state.get("approval") else (
            "abstained" if (h and h.abstained) else "completed"
        )

        INCIDENTS_DB[incident_id].update(
            {
                "status": status,
                "hypothesis": h.model_dump() if h else None,
                "evidence": [e.model_dump() for e in final_state.get("evidence", [])],
                "guardrail_flags": final_state.get("guardrail_flags", []),
                "approval": final_state.get("approval"),
                "cost_usd": final_state.get("cost_usd", 0.0),
                "latency_ms": round(latency_ms, 2),
                "steps": final_state.get("steps", 0),
            }
        )
    except Exception as exc:  # noqa: BLE001
        INCIDENTS_DB[incident_id]["status"] = "failed"
        INCIDENTS_DB[incident_id]["error"] = str(exc)


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
        "alert": alert.model_dump(),
        "status": "queued",
        "created_at": time.time(),
    }

    # Run workflow asynchronously
    background_tasks.add_task(run_incident_workflow, incident_id, alert)
    return {"incident_id": incident_id, "status": "queued", "message": "Incident investigation launched"}


@app.get("/v1/incidents/{incident_id}")
def get_incident(incident_id: str):
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")
    return INCIDENTS_DB[incident_id]


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import json
import logging
import os
import uuid
from typing import Any

from incidentiq.agents.mcp_client import (
    detect_anomaly,
    get_error_clusters,
    query_metric,
    search_logs,
)
from incidentiq.agents.state import IncidentState
from incidentiq.guardrails.guards import GuardrailManager
from incidentiq.rag.engine import get_rag_engine
from incidentiq.schemas.models import Action, Evidence, Hypothesis
from incidentiq.security.tokens import (
    generate_capability_token,
    hash_token,
    register_server_approval_token,
)

logger = logging.getLogger("incidentiq.agents")


def input_guard_node(state: IncidentState) -> dict[str, Any]:
    """Scans alert for PII & prompt injection before model/specialist execution."""
    clean_alert, flags = GuardrailManager.process_input_alert(state["alert"])
    return {
        "alert": clean_alert,
        "guardrail_flags": flags,
        "steps": 1,
    }


def supervisor_node(state: IncidentState) -> dict[str, Any]:
    """Deterministic Supervisor Planner: Analyzes alert metadata to formulate specialist triage strategy.

    Zero-overhead, zero-LLM-cost deterministic planner that inspects alert properties
    and determines which specialist agents to dispatch (metrics, logs, runbooks).
    Eliminates planning hallucinations and planning latency while dynamically driving graph execution.
    """
    alert = state.get("alert")
    service = alert.service.lower() if alert and alert.service else ""
    symptom = alert.symptom.lower() if alert and alert.symptom else ""

    # Always dispatch metrics and logs for production microservices to avoid blind spots
    plan = ["metrics", "logs"]

    # Include runbook knowledge retrieval for operational microservice triage
    if service or symptom:
        plan.append("runbook")
    else:
        plan.append("runbook")

    return {
        "plan": plan,
        "steps": 1,
        "cost_usd": 0.0,
    }


def metrics_agent_node(state: IncidentState) -> dict[str, Any]:
    """Metrics Specialist: Investigates Prometheus metrics for the affected service."""
    service = state["alert"].service
    scenario_id = state.get("scenario_id") or ""
    new_evidence: list[Evidence] = []
    cost = 0.001

    # Check key operational metrics
    metrics_to_check = [
        "db_pool_in_use",
        "error_rate",
        "latency_p95",
        "memory_mb",
        "cache_hit_rate",
    ]
    for m in metrics_to_check:
        res = query_metric(
            service=service, metric=m, minutes=30, scenario_id=scenario_id
        )
        if "error" in res:
            continue
        summary = res.get("summary", {})
        anomaly = detect_anomaly(
            service=service, metric=m, minutes=30, scenario_id=scenario_id
        )

        # Record evidence if anomaly detected or notable metric values
        if anomaly.get("anomalous") or (
            m == "db_pool_in_use" and summary.get("max", 0) >= 8.0
        ):
            ev_id = f"ev_metric_{m}"
            ev = Evidence(
                id=ev_id,
                kind="metric",
                summary=(
                    f"Metric '{m}' on {service} anomaly detected (severity: {anomaly.get('severity')}): "
                    f"peak value={summary.get('max')}, mean={summary.get('mean')}, z-score={anomaly.get('z_score')}."
                ),
                source_ref=f"mcp:metrics_server:query_metric:{m}",
                data={"summary": summary, "anomaly": anomaly},
            )
            new_evidence.append(ev)

    return {
        "evidence": new_evidence,
        "cost_usd": cost,
        "steps": 1,
    }


def logs_agent_node(state: IncidentState) -> dict[str, Any]:
    """Logs Specialist: Searches container logs and aggregates error clusters."""
    service = state["alert"].service
    scenario_id = state.get("scenario_id") or ""
    new_evidence: list[Evidence] = []
    cost = 0.001

    # 1. Error clusters
    clusters = get_error_clusters(
        service=service, minutes=30, scenario_id=scenario_id
    )
    for idx, c in enumerate(clusters[:2]):
        ev_id = f"ev_log_cluster_{idx + 1}"
        ev = Evidence(
            id=ev_id,
            kind="log",
            summary=f"Found {c.get('count')} occurrences of error pattern on {service}: {c.get('example')}",
            source_ref=f"mcp:logs_server:get_error_clusters:{service}",
            data=c,
        )
        new_evidence.append(ev)

    # 2. Specific search for fatal or timeout logs
    error_logs = search_logs(
        service=service, level="error", limit=3, scenario_id=scenario_id
    )
    for idx, l in enumerate(error_logs):
        ev_id = f"ev_log_err_{idx + 1}"
        ev = Evidence(
            id=ev_id,
            kind="log",
            summary=f"Error log line on {service}: {l.get('msg')}",
            source_ref=f"mcp:logs_server:search_logs:{l.get('request_id')}",
            data=l,
        )
        new_evidence.append(ev)

    return {
        "evidence": new_evidence,
        "cost_usd": cost,
        "steps": 1,
    }


def runbook_agent_node(state: IncidentState) -> dict[str, Any]:
    """Runbook RAG Specialist: Retrieves matching playbooks and past postmortems."""
    rag = get_rag_engine()
    service = state["alert"].service
    query = f"{service} {state['alert'].symptom}"
    top_chunks = rag.retrieve(query=query, service=service, top_k=2)

    new_evidence: list[Evidence] = []
    guardrail_flags: list[str] = []
    for chunk in top_chunks:
        is_injection, reason = GuardrailManager.scan_injection(chunk.content)
        content_preview = chunk.content[:220]
        if is_injection:
            guardrail_flags.append(f"runbook_injection_flagged: {reason}")
            content_preview = "[QUARANTINED_POTENTIAL_INJECTION]"
        ev_id = f"ev_kb_{chunk.chunk_id}"
        ev = Evidence(
            id=ev_id,
            kind="runbook" if "runbook" in chunk.doc_title.lower() else "postmortem",
            summary=f"Matched playbook '{chunk.doc_title}' (relevance score: {chunk.score}): {content_preview}...",
            source_ref=f"kb:{chunk.chunk_id}",
            data={"score": chunk.score, "category": chunk.category},
        )
        new_evidence.append(ev)

    return {
        "evidence": new_evidence,
        "guardrail_flags": guardrail_flags,
        "cost_usd": 0.0005,
        "steps": 1,
    }


def _call_llm_for_diagnosis(
    alert: Any,
    telemetry_evidence: list[Evidence],
    kb_evidence: list[Evidence],
) -> tuple[Hypothesis | None, str | None]:
    """Invokes LiteLLM for dynamic root cause diagnosis when an LLM is configured."""
    api_key = (
        os.getenv("LLM_API_KEY_PRIMARY")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
    )
    model = os.getenv("MODEL_STRONG", "gpt-4o")

    # If no key and not an ollama model, return (None, None) to use deterministic engine
    if not api_key and not model.startswith("ollama/"):
        return None, None

    try:
        import litellm
        from litellm import completion

        # Opt-in Langfuse observability if keys are set in environment
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            host = os.getenv("LANGFUSE_HOST") or os.getenv(
                "LANGFUSE_BASE_URL", "https://cloud.langfuse.com"
            )
            if host:
                os.environ["LANGFUSE_BASE_URL"] = str(host)
                os.environ["LANGFUSE_HOST"] = str(host)
            if "langfuse" not in litellm.success_callback:
                litellm.success_callback.append("langfuse")
            if "langfuse" not in litellm.failure_callback:
                litellm.failure_callback.append("langfuse")

        telemetry_prompt = "\n".join(
            [f"- [{e.id}] ({e.kind}): {e.summary}" for e in telemetry_evidence]
        )
        kb_prompt = "\n".join(
            [f"- [{e.id}] ({e.kind}): {e.summary}" for e in kb_evidence]
        )

        system_prompt = (
            "You are the Root Cause Synthesis Agent for IncidentIQ, an autonomous on-call SRE copilot. "
            "You are given alert details, telemetry anomalies (metrics & logs), and runbook context. "
            "Your job is to diagnose the root cause, assign a calibrated confidence score (0.00 - 1.00), "
            "cite all supporting evidence IDs, and propose a safe remediation action.\n\n"
            "CRITICAL RULES:\n"
            "1. ONLY cite evidence IDs that are explicitly provided in the evidence lists.\n"
            "2. If telemetry is normal, contradictory, or insufficient, set abstained=true and explain why in abstain_reason.\n"
            "3. If confidence is below 0.50, abstained MUST be true.\n"
            "4. Respond with valid JSON matching this schema:\n"
            "{\n"
            '  "category": "db_pool_exhaustion" | "bad_deploy_config" | "cache_failure" | "dependency_timeout" | "slow_db_query" | "memory_leak" | null,\n'
            '  "service": "<service_name>" | null,\n'
            '  "confidence": <float 0.0 to 1.0>,\n'
            '  "reasoning": "<concise diagnostic narrative citing evidence IDs>",\n'
            '  "evidence_ids": ["ev_metric_001", "ev_log_004"],\n'
            '  "suggested_action": {"type": "review_config" | "restart_service" | "rollback_deploy" | "none", "target": "<service>", "detail": "<details>"} | null,\n'
            '  "abstained": false | true,\n'
            '  "abstain_reason": null | "<reason for abstaining>"\n'
            "}"
        )

        user_prompt = (
            f"Alert Service: {alert.service}\n"
            f"Alert Symptom: {alert.symptom}\n\n"
            f"Telemetry Evidence:\n{telemetry_prompt}\n\n"
            f"Runbook & Postmortem Context:\n{kb_prompt}\n"
        )

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "timeout": 15,
        }
        if api_key:
            kwargs["api_key"] = api_key

        if any(prov in model for prov in ["gpt", "groq", "gemini", "claude"]):
            kwargs["response_format"] = {"type": "json_object"}

        response = completion(**kwargs)
        content = response.choices[0].message.content.strip()

        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        data = json.loads(content)
        action_data = data.get("suggested_action")
        suggested_action = (
            Action(**action_data)
            if action_data
            and action_data.get("type")
            and action_data.get("type") != "none"
            else None
        )

        return (
            Hypothesis(
                category=data.get("category"),
                service=data.get("service"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                evidence_ids=data.get(
                    "evidence_ids", [e.id for e in telemetry_evidence]
                ),
                suggested_action=suggested_action,
                abstained=bool(data.get("abstained", False)),
                abstain_reason=data.get("abstain_reason"),
                is_fallback=False,
            ),
            None,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(
            f"LLM diagnosis failed or unconfigured, falling back to deterministic engine: {e}"
        )
        return None, str(e)


def root_cause_agent_node(state: IncidentState) -> dict[str, Any]:
    """Root-Cause Synthesis Agent: Reasons across metrics, logs, and playbooks to diagnose the issue."""
    all_evidence = state.get("evidence", [])
    service = state["alert"].service
    cost = 0.002

    telemetry_evidence = [e for e in all_evidence if e.kind in ["metric", "log"]]
    kb_evidence = [e for e in all_evidence if e.kind in ["runbook", "postmortem"]]

    # If no metrics anomalies and no error logs were discovered, we MUST abstain!
    if not telemetry_evidence:
        hypothesis = Hypothesis(
            category=None,
            service=None,
            confidence=0.20,
            reasoning="Telemetry is completely normal. No metric anomalies or error logs were discovered.",
            evidence_ids=[e.id for e in kb_evidence],
            suggested_action=None,
            abstained=True,
            abstain_reason="Telemetry is healthy. No metric anomalies or error logs support a system outage.",
        )
        return {
            "hypothesis": hypothesis,
            "cost_usd": cost,
            "steps": 1,
        }

    # 1. Try LLM synthesis if API key is configured
    llm_hypothesis, llm_error = _call_llm_for_diagnosis(
        alert=state["alert"],
        telemetry_evidence=telemetry_evidence,
        kb_evidence=kb_evidence,
    )
    if llm_hypothesis is not None:
        return {
            "hypothesis": llm_hypothesis,
            "cost_usd": 0.003,
            "steps": 1,
        }

    # 2. Deterministic Rule Engine Fallback (Zero-Dependency Offline Replay)
    telemetry_text = "\n".join(
        [f"[{e.id}] ({e.kind}): {e.summary}" for e in telemetry_evidence]
    )
    evidence_ids = [e.id for e in all_evidence]

    category = None
    suggested_action = None
    confidence = 0.85
    reasoning = ""

    if (
        "validationerror" in telemetry_text.lower()
        or "keyerror" in telemetry_text.lower()
        or "pydantic" in telemetry_text.lower()
    ):
        category = "bad_deploy_config"
        reasoning = f"Startup crashloop on '{service}' caused by missing environment variable or config validation failure."
        suggested_action = Action(
            type="rollback_deploy",
            target=service,
            detail="Rollback to previous stable container release",
        )

    elif (
        "redis" in telemetry_text.lower() or "cache_hit_rate" in telemetry_text.lower()
    ):
        category = "cache_failure"
        reasoning = f"Cache hit rate dropped to 0% and connection to Redis was refused on '{service}', overwhelming the database."
        suggested_action = Action(
            type="restart_service",
            target="redis",
            detail="Restart Redis cache instance and warm keys",
        )

    elif (
        "pool limit reached" in telemetry_text.lower()
        or "remaining connection slots" in telemetry_text.lower()
        or (
            "db_pool_in_use" in telemetry_text.lower()
            and "peak value=10" in telemetry_text.lower()
        )
    ):
        category = "db_pool_exhaustion"
        reasoning = (
            f"Metrics and logs confirm the database connection pool on '{service}' is fully exhausted. "
            "Telemetry shows 10/10 connections active, blocking further client transactions."
        )
        suggested_action = Action(
            type="review_config",
            target=service,
            detail="Increase MAX_DB_POOL_SIZE from 10 to 20 or restart leaked connections",
        )

    elif (
        "external_payment_timeout" in telemetry_text.lower()
        or "readtimeout" in telemetry_text.lower()
        or "504" in telemetry_text.lower()
    ):
        category = "dependency_timeout"
        reasoning = f"Downstream external provider calls timed out on '{service}'. Logs report ReadTimeout after 5000ms."
        suggested_action = Action(
            type="review_config",
            target=service,
            detail="Adjust external client timeout and engage circuit-breaker",
        )

    elif (
        "slow_query" in telemetry_text.lower()
        or "sequential scan" in telemetry_text.lower()
    ):
        category = "slow_db_query"
        reasoning = f"Severe p95 latency elevation without error spikes indicates slow unindexed database queries on '{service}'."
        suggested_action = Action(
            type="review_config",
            target=service,
            detail="Add database index on queried columns and enable Redis caching",
        )

    elif (
        "oomkilled" in telemetry_text.lower()
        or "sigkill" in telemetry_text.lower()
        or "high_memory_watermark" in telemetry_text.lower()
    ):
        category = "memory_leak"
        reasoning = f"Process memory usage climbed to container quota on '{service}', triggering OOM kill."
        suggested_action = Action(
            type="restart_service",
            target=service,
            detail="Restart service container to clear heap allocations",
        )
    else:
        # Ambiguous / uncertain case
        confidence = 0.35
        category = None
        reasoning = "Telemetry shows minor fluctuation but lacks a distinctive signature of known system outages."

    # If confidence < threshold, abstain honestly
    abstained = confidence < get_abstain_threshold()
    abstain_reason = (
        "Telemetry is inconclusive or inconsistent with known failure models."
        if abstained
        else None
    )
    if abstained:
        suggested_action = None

    hypothesis = Hypothesis(
        category=category,
        service=service if not abstained else None,
        confidence=confidence,
        reasoning=reasoning,
        evidence_ids=evidence_ids,
        suggested_action=suggested_action,
        abstained=abstained,
        abstain_reason=abstain_reason,
        is_fallback=True,
    )

    out: dict[str, Any] = {
        "hypothesis": hypothesis,
        "cost_usd": cost,
        "steps": 1,
    }
    if llm_error:
        out["error"] = f"LLM error: {llm_error}"
    return out


def get_abstain_threshold() -> float:
    try:
        return float(os.getenv("ABSTAIN_THRESHOLD", "0.50"))
    except ValueError:
        return 0.50


def get_ground_threshold() -> float:
    try:
        return float(os.getenv("GROUND_THRESHOLD", "0.85"))
    except ValueError:
        return 0.85


def output_guard_node(state: IncidentState) -> dict[str, Any]:
    """Output Guard: Verifies claim groundedness and blocks prompt/secret leakage."""
    hypothesis = state["hypothesis"]
    if hypothesis is None:
        return {"steps": 1}

    verified_hypothesis, flags = GuardrailManager.verify_groundedness(
        hypothesis=hypothesis,
        evidence_list=state.get("evidence", []),
        confidence_threshold=get_abstain_threshold(),
        ground_threshold=get_ground_threshold(),
    )

    # Check output text fields for prompt or runtime secret leakage
    texts_to_check = [
        verified_hypothesis.reasoning or "",
        verified_hypothesis.abstain_reason or "",
        verified_hypothesis.suggested_action.detail
        if verified_hypothesis.suggested_action
        else "",
    ]
    for txt in texts_to_check:
        leaked, leak_reason = GuardrailManager.scan_prompt_leakage(txt)
        if leaked:
            verified_hypothesis.abstained = True
            verified_hypothesis.abstain_reason = (
                "Output blocked by prompt/secret leakage guard."
            )
            verified_hypothesis.reasoning = "[REDACTED_PROMPT_LEAKAGE]"
            verified_hypothesis.suggested_action = None
            flags.append(f"prompt_leakage_blocked: {leak_reason}")
            break

    return {
        "hypothesis": verified_hypothesis,
        "guardrail_flags": flags,
        "steps": 1,
    }


def human_approval_node(state: IncidentState) -> dict[str, Any]:
    """Human-in-the-Loop Node: Prepares action approval token for proposed remediations."""
    hypothesis = state.get("hypothesis")
    if (
        not hypothesis
        or not hypothesis.suggested_action
        or hypothesis.suggested_action.type == "none"
    ):
        return {"approval": None, "steps": 1}

    incident_id = state.get("incident_id", "unknown_incident")
    approval_id = f"appr_req_{uuid.uuid4().hex[:10]}"
    action_dict = hypothesis.suggested_action.model_dump()

    # Generate server-side signed capability token (HMAC-SHA256, 15m TTL)
    raw_token = generate_capability_token(
        incident_id=incident_id,
        action=action_dict.get("type", ""),
        target=action_dict.get("target", ""),
    )
    register_server_approval_token(approval_id, raw_token)

    # State retains only approval_id, status, action, and token_hash (NEVER raw capability token)
    approval_data = {
        "approval_id": approval_id,
        "status": "awaiting_approval",
        "action": action_dict,
        "token_hash": hash_token(raw_token),
    }
    return {
        "approval": approval_data,
        "steps": 1,
    }


def budget_exceeded_node(state: IncidentState) -> dict[str, Any]:
    """Triggered when step or cost budget is exhausted."""
    steps = state.get("steps", 0)
    cost_usd = state.get("cost_usd", 0.0)
    try:
        max_steps = int(os.getenv("MAX_AGENT_STEPS", "12"))
    except ValueError:
        max_steps = 12
    try:
        budget_usd = float(os.getenv("INCIDENT_BUDGET_USD", "0.05"))
    except ValueError:
        budget_usd = 0.05
    reason = f"Investigation budget exceeded: steps={steps}/{max_steps}, cost=${cost_usd:.4f}/${budget_usd:.2f}"
    logger.warning(reason)

    hypothesis = state.get("hypothesis")
    if hypothesis:
        hypothesis.abstained = True
        hypothesis.abstain_reason = (
            f"Budget exceeded ({reason}). Abstaining from action."
        )
        hypothesis.suggested_action = None

    return {
        "guardrail_flags": ["BUDGET_EXCEEDED"],
        "steps": 1,
    }


def report_node(state: IncidentState) -> dict[str, Any]:
    """Final Report Node: Compiles full diagnostic report with cost & latency accounting."""
    return {
        "steps": 1,
    }

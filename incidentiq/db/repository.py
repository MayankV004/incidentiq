import logging
import time
from typing import Any

from incidentiq.db.models import (
    ApprovalRecord,
    GuardrailEventRecord,
    IncidentFeedbackRecord,
    IncidentRecord,
    LLMCallRecord,
    ToolCallRecord,
)
from incidentiq.db.session import SessionLocal

logger = logging.getLogger("incidentiq.db")


def _safe_truncate(value: Any, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:limit]


def _sanitize_tool_args(arguments: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(arguments, dict):
        return arguments
    sanitized = dict(arguments)
    for secret_key in ("token", "approval_token"):
        if sanitized.get(secret_key):
            sanitized[secret_key] = "[REDACTED]"
    return sanitized


def upsert_incident(incident_data: dict[str, Any]) -> dict[str, Any]:
    """Inserts or updates an incident record in the database."""
    incident_id = incident_data["incident_id"]
    alert = incident_data.get("alert", {})
    with SessionLocal() as db:
        rec = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
        if not rec:
            rec = IncidentRecord(
                id=incident_id,
                scenario_id=incident_data.get("scenario_id"),
                service=alert.get("service", "unknown"),
                symptom=alert.get("symptom", ""),
                window_start=alert.get("window_start", ""),
                window_end=alert.get("window_end", ""),
                status=incident_data.get("status", "queued"),
                cost_usd=incident_data.get("cost_usd", 0.0),
                latency_ms=incident_data.get("latency_ms", 0.0),
                steps=incident_data.get("steps", 0),
                hypothesis=incident_data.get("hypothesis"),
                evidence=incident_data.get("evidence", []),
                guardrail_flags=incident_data.get("guardrail_flags", []),
                approval=incident_data.get("approval"),
                events=incident_data.get("events", []),
                langfuse_trace_url=incident_data.get("langfuse_trace_url"),
                error=incident_data.get("error"),
                created_at=incident_data.get("created_at", time.time()),
            )
            db.add(rec)
        else:
            for k in [
                "status",
                "cost_usd",
                "latency_ms",
                "steps",
                "hypothesis",
                "evidence",
                "guardrail_flags",
                "approval",
                "events",
                "langfuse_trace_url",
                "error",
                "completed_at",
            ]:
                if k in incident_data:
                    setattr(rec, k, incident_data[k])
        db.commit()
        db.refresh(rec)
        return rec.to_dict()


def update_incident(incident_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Updates specific fields of an incident in the database."""
    with SessionLocal() as db:
        rec = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
        if not rec:
            return None
        for k, v in updates.items():
            if hasattr(rec, k):
                setattr(rec, k, v)
        db.commit()
        db.refresh(rec)
        return rec.to_dict()


def append_event_to_db(incident_id: str, event: dict[str, Any]):
    """Appends an event to an incident's event log in the database."""
    with SessionLocal() as db:
        rec = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
        if not rec:
            return
        curr_events = list(rec.events or [])  # type: ignore[arg-type]
        curr_events.append(event)
        rec.events = curr_events  # type: ignore[assignment]
        db.commit()


def _feedback_to_dict(fb: IncidentFeedbackRecord) -> dict[str, Any]:
    return {
        "id": fb.id,
        "incident_id": fb.incident_id,
        "verdict": fb.verdict,
        "corrected_category": fb.corrected_category,
        "notes": fb.notes,
        "submitted_by": fb.submitted_by,
        "created_at": fb.created_at,
    }


def get_incident_from_db(incident_id: str) -> dict[str, Any] | None:
    """Retrieves an incident record and latest feedback from the database."""
    with SessionLocal() as db:
        rec = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
        if not rec:
            return None
        data = rec.to_dict()
        fb = (
            db.query(IncidentFeedbackRecord)
            .filter(IncidentFeedbackRecord.incident_id == incident_id)
            .order_by(IncidentFeedbackRecord.created_at.desc())
            .first()
        )
        if fb:
            data["feedback"] = _feedback_to_dict(fb)
        return data


def list_incidents_from_db() -> list[dict[str, Any]]:
    """Lists all incidents from the database ordered by creation date descending."""
    with SessionLocal() as db:
        records = (
            db.query(IncidentRecord).order_by(IncidentRecord.created_at.desc()).all()
        )
        return [r.to_dict() for r in records]


def get_daily_costs_by_id_from_db(since_ts: float) -> dict[str, float]:
    """Returns persisted incident_id -> cost_usd for incidents created at or after since_ts."""
    with SessionLocal() as db:
        rows: list[Any] = (
            db.query(IncidentRecord.id, IncidentRecord.cost_usd)
            .filter(IncidentRecord.created_at >= since_ts)  # type: ignore[arg-type]
            .all()
        )
        return {str(row.id): float(row.cost_usd or 0.0) for row in rows}


def record_llm_call(
    incident_id: str | None,
    model: str,
    purpose: str = "root_cause_synthesis",
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    cache_hit: bool = False,
    error: str | None = None,
) -> None:
    """Persists an LLM invocation telemetry row."""
    try:
        with SessionLocal() as db:
            db.add(
                LLMCallRecord(
                    incident_id=incident_id,
                    model=model,
                    purpose=purpose,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    cache_hit=cache_hit,
                    error=_safe_truncate(error),
                    created_at=time.time(),
                )
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Failed to record llm_calls telemetry: {exc}")


def record_tool_call(
    incident_id: str | None,
    server: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    result: Any = None,
    allowed: bool = True,
    error: str | None = None,
    latency_ms: float = 0.0,
) -> None:
    """Persists an MCP tool call telemetry row with tokens sanitized."""
    try:
        safe_result: Any = result
        if isinstance(result, (dict, list)):
            safe_result = result
        elif result is not None:
            safe_result = {"value": _safe_truncate(result)}
        with SessionLocal() as db:
            db.add(
                ToolCallRecord(
                    incident_id=incident_id,
                    server=server,
                    tool_name=tool_name,
                    arguments=_sanitize_tool_args(arguments),
                    result=safe_result,
                    allowed=allowed,
                    error=_safe_truncate(error),
                    latency_ms=latency_ms,
                    created_at=time.time(),
                )
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Failed to record tool_calls telemetry: {exc}")


def record_guardrail_event(
    incident_id: str | None,
    phase: str,
    flag_type: str,
    detail: str = "",
    raw_input: str | None = None,
    sanitized_output: str | None = None,
) -> None:
    """Persists a guardrail execution/trigger telemetry row."""
    try:
        with SessionLocal() as db:
            db.add(
                GuardrailEventRecord(
                    incident_id=incident_id,
                    phase=phase,
                    flag_type=flag_type[:64],
                    detail=_safe_truncate(detail),
                    raw_input=_safe_truncate(raw_input),
                    sanitized_output=_safe_truncate(sanitized_output),
                    created_at=time.time(),
                )
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Failed to record guardrail_events telemetry: {exc}")


def record_approval_requested(
    approval_id: str,
    incident_id: str,
    action: dict[str, Any],
    token_hash: str,
) -> None:
    """Persists a pending human approval request row (token hash only, never raw token)."""
    try:
        with SessionLocal() as db:
            db.add(
                ApprovalRecord(
                    approval_id=approval_id,
                    incident_id=incident_id,
                    action=action,
                    decision=None,
                    token_hash=token_hash,
                    requested_at=time.time(),
                )
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Failed to record approvals request telemetry: {exc}")


def record_approval_decision(
    approval_id: str,
    decision: str,
    decided_by: str = "on_call_engineer",
) -> None:
    """Updates an approval telemetry row with human decision and timestamp."""
    try:
        with SessionLocal() as db:
            rec = (
                db.query(ApprovalRecord)
                .filter(ApprovalRecord.approval_id == approval_id)
                .first()
            )
            if rec:
                rec.decision = decision  # type: ignore[assignment]
                rec.decided_by = decided_by  # type: ignore[assignment]
                rec.decided_at = time.time()  # type: ignore[assignment]
                db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Failed to record approvals decision telemetry: {exc}")


def record_incident_feedback(
    incident_id: str,
    verdict: str,
    corrected_category: str | None = None,
    notes: str | None = None,
    submitted_by: str = "on_call_engineer",
) -> dict[str, Any]:
    """Persists human evaluation feedback on an investigation outcome."""
    with SessionLocal() as db:
        fb = IncidentFeedbackRecord(
            incident_id=incident_id,
            verdict=verdict,
            corrected_category=_safe_truncate(corrected_category, 128),
            notes=_safe_truncate(notes, 500),
            submitted_by=_safe_truncate(submitted_by, 128) or "on_call_engineer",
            created_at=time.time(),
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return _feedback_to_dict(fb)


def list_memory_candidates(
    exclude_incident_id: str | None = None,
    exclude_scenario_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Loads resolved past incidents that have human verification (feedback or approval decision)."""
    try:
        with SessionLocal() as db:
            fb_rows: list[Any] = (
                db.query(IncidentFeedbackRecord.incident_id)
                .distinct()
                .all()
            )
            fb_ids = {str(row[0]) for row in fb_rows if row[0]}
            ap_rows: list[Any] = (
                db.query(ApprovalRecord.incident_id)
                .filter(ApprovalRecord.decision.isnot(None))  # type: ignore[union-attr]
                .distinct()
                .all()
            )
            ap_ids = {str(row[0]) for row in ap_rows if row[0]}
            verified_ids = fb_ids | ap_ids
            if exclude_incident_id:
                verified_ids.discard(exclude_incident_id)
            if not verified_ids:
                return []

            query = db.query(IncidentRecord).filter(
                IncidentRecord.id.in_(verified_ids),
                IncidentRecord.hypothesis.isnot(None),  # type: ignore[union-attr]
            )
            if exclude_scenario_id:
                query = query.filter(
                    (IncidentRecord.scenario_id.is_(None))  # type: ignore[union-attr]
                    | (IncidentRecord.scenario_id != exclude_scenario_id)
                )
            records = (
                query.order_by(IncidentRecord.created_at.desc()).limit(limit).all()
            )
            if not records:
                return []

            inc_ids = [str(r.id) for r in records]
            feedback_rows = (
                db.query(IncidentFeedbackRecord)
                .filter(IncidentFeedbackRecord.incident_id.in_(inc_ids))
                .order_by(IncidentFeedbackRecord.created_at.desc())
                .all()
            )
            latest_fb: dict[str, dict[str, Any]] = {}
            for fb in feedback_rows:
                inc_key = str(fb.incident_id)
                if inc_key not in latest_fb:
                    latest_fb[inc_key] = _feedback_to_dict(fb)

            approval_rows = (
                db.query(ApprovalRecord)
                .filter(
                    ApprovalRecord.incident_id.in_(inc_ids),
                    ApprovalRecord.decision.isnot(None),  # type: ignore[union-attr]
                )
                .order_by(ApprovalRecord.decided_at.desc())
                .all()
            )
            latest_appr: dict[str, dict[str, Any]] = {}
            for ap in approval_rows:
                inc_key = str(ap.incident_id)
                if inc_key not in latest_appr:
                    latest_appr[inc_key] = {
                        "decision": ap.decision,
                        "action": ap.action,
                    }

            candidates: list[dict[str, Any]] = []
            for rec in records:
                inc_key = str(rec.id)
                fb_info = latest_fb.get(inc_key)
                ap_info = latest_appr.get(inc_key)
                if not fb_info and not ap_info:
                    continue
                hyp = rec.hypothesis if isinstance(rec.hypothesis, dict) else None
                if not hyp:
                    continue
                if hyp.get("abstained") and not (
                    fb_info and fb_info.get("verdict") in ("wrong_root_cause", "false_alarm", "good_abstention")
                ):
                    continue
                candidates.append(
                    {
                        "incident_id": inc_key,
                        "service": str(rec.service or ""),
                        "symptom": str(rec.symptom or ""),
                        "status": str(rec.status or ""),
                        "hypothesis": hyp,
                        "feedback": fb_info,
                        "approval": ap_info,
                        "created_at": rec.created_at,
                    }
                )
            return candidates
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Failed to load memory candidates: {exc}")
        return []


def list_labeled_incidents_for_scoring() -> list[dict[str, Any]]:
    """Returns incidents paired with their latest human feedback for live evaluation."""
    with SessionLocal() as db:
        fb_rows = (
            db.query(IncidentFeedbackRecord)
            .order_by(IncidentFeedbackRecord.created_at.desc())
            .all()
        )
        latest_fb: dict[str, dict[str, Any]] = {}
        for fb in fb_rows:
            inc_key = str(fb.incident_id)
            if inc_key not in latest_fb:
                latest_fb[inc_key] = _feedback_to_dict(fb)
        if not latest_fb:
            return []

        records = (
            db.query(IncidentRecord)
            .filter(IncidentRecord.id.in_(list(latest_fb.keys())))
            .order_by(IncidentRecord.created_at.desc())
            .all()
        )
        out: list[dict[str, Any]] = []
        for rec in records:
            item = rec.to_dict()
            item["feedback"] = latest_fb[str(rec.id)]
            out.append(item)
        return out

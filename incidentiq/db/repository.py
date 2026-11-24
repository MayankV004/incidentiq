import time
from typing import Any

from incidentiq.db.models import IncidentRecord
from incidentiq.db.session import SessionLocal


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


def get_incident_from_db(incident_id: str) -> dict[str, Any] | None:
    """Retrieves an incident record from the database."""
    with SessionLocal() as db:
        rec = db.query(IncidentRecord).filter(IncidentRecord.id == incident_id).first()
        return rec.to_dict() if rec else None


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
        rows = (
            db.query(IncidentRecord.id, IncidentRecord.cost_usd)
            .filter(IncidentRecord.created_at >= since_ts)
            .all()
        )
        return {str(row.id): float(row.cost_usd or 0.0) for row in rows}

import time
from typing import Any

from sqlalchemy import JSON, Column, Float, Integer, String, Text

from incidentiq.db.session import Base


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, index=True)
    scenario_id = Column(String(128), nullable=True, index=True)
    service = Column(String(64), nullable=False, index=True)
    symptom = Column(Text, nullable=False)
    window_start = Column(String(64), nullable=True)
    window_end = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    steps = Column(Integer, default=0)
    hypothesis = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    guardrail_flags = Column(JSON, nullable=True)
    approval = Column(JSON, nullable=True)
    events = Column(JSON, nullable=True)
    langfuse_trace_url = Column(String(512), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)
    completed_at = Column(Float, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.id,
            "scenario_id": self.scenario_id,
            "alert": {
                "service": self.service,
                "symptom": self.symptom,
                "window_start": self.window_start or "",
                "window_end": self.window_end or "",
            },
            "status": self.status,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "steps": self.steps,
            "hypothesis": self.hypothesis,
            "evidence": self.evidence or [],
            "guardrail_flags": self.guardrail_flags or [],
            "approval": self.approval,
            "events": self.events or [],
            "langfuse_trace_url": self.langfuse_trace_url,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

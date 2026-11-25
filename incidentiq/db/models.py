import time
import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Integer, String, Text

from incidentiq.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


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


class LLMCallRecord(Base):
    __tablename__ = "llm_calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_run_id = Column(String(36), nullable=True, index=True)
    incident_id = Column(
        String(64),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    model = Column(String(128), nullable=False)
    purpose = Column(String(64), nullable=True)  # route, summarize, reason, judge
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    cache_hit = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)


class ToolCallRecord(Base):
    __tablename__ = "tool_calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_run_id = Column(String(36), nullable=True, index=True)
    incident_id = Column(
        String(64),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    server = Column(String(64), nullable=False)  # metrics, logs, remediation
    tool_name = Column(String(64), nullable=False)
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    allowed = Column(Boolean, nullable=False, default=True)
    error = Column(Text, nullable=True)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(Float, default=time.time)


class GuardrailEventRecord(Base):
    __tablename__ = "guardrail_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(
        String(64),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    phase = Column(String(32), nullable=False)  # input, output
    flag_type = Column(
        String(64), nullable=False
    )  # pii_redacted, injection_blocked, etc.
    detail = Column(Text, nullable=True)
    raw_input = Column(Text, nullable=True)
    sanitized_output = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)


class ApprovalRecord(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    approval_id = Column(String(64), nullable=True, index=True)
    incident_id = Column(
        String(64),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(JSON, nullable=False)
    decision = Column(String(32), nullable=True)  # approved, rejected, expired
    decided_by = Column(String(128), nullable=True)
    token_hash = Column(String(128), nullable=True)
    requested_at = Column(Float, default=time.time)
    decided_at = Column(Float, nullable=True)


class EvalRunRecord(Base):
    __tablename__ = "eval_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_name = Column(String(128), nullable=False, index=True)
    split = Column(String(32), default="all")
    repeats = Column(Integer, default=1)
    total_scenarios = Column(Integer, default=0)
    total_runs = Column(Integer, default=0)
    accuracy_pct = Column(Float, default=0.0)
    groundedness_pct = Column(Float, default=0.0)
    abstention_correct_pct = Column(Float, default=0.0)
    action_safety_pct = Column(Float, default=100.0)
    mean_cost_usd = Column(Float, default=0.0)
    latency_p50_ms = Column(Float, default=0.0)
    latency_p95_ms = Column(Float, default=0.0)
    code_path = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)


class EvalResultRecord(Base):
    __tablename__ = "eval_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    eval_run_id = Column(
        String(36),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id = Column(String(128), nullable=False, index=True)
    repeat_index = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    groundedness = Column(Float, default=0.0)
    abstention_correct = Column(Boolean, default=False)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    steps = Column(Integer, default=0)
    hypothesis = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)


class IncidentFeedbackRecord(Base):
    __tablename__ = "incident_feedback"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(
        String(64),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verdict = Column(
        String(32), nullable=False
    )  # correct_root_cause | wrong_root_cause | good_abstention | false_alarm
    corrected_category = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    submitted_by = Column(String(128), default="on_call_engineer")
    created_at = Column(Float, default=time.time)

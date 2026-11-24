from typing import Literal

from pydantic import BaseModel, Field


class Alert(BaseModel):
    service: str
    symptom: str
    window_start: str
    window_end: str


class Evidence(BaseModel):
    id: str  # e.g. "ev_metric_001", "ev_log_004", "ev_rb_002"
    kind: Literal["metric", "log", "runbook", "postmortem"]
    summary: str
    source_ref: str  # tool call id or kb chunk id
    data: dict | None = None


class Action(BaseModel):
    type: Literal[
        "restart_service", "rollback_deploy", "review_config", "scale_up", "none"
    ]
    target: str
    detail: str


class Hypothesis(BaseModel):
    category: str | None = None  # None if abstained
    service: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_action: Action | None = None
    abstained: bool = False
    abstain_reason: str | None = None
    is_fallback: bool = False


class KBChunk(BaseModel):
    chunk_id: str
    doc_title: str
    category: str
    service: str
    content: str
    score: float = 0.0

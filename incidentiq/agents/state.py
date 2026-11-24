import operator
from typing import Annotated, Any, TypedDict

from incidentiq.schemas.models import Alert, Evidence, Hypothesis


class IncidentState(TypedDict, total=False):
    incident_id: str
    alert: Alert
    plan: list[str]  # e.g. ["metrics", "logs", "runbook"]
    evidence: Annotated[
        list[Evidence], operator.add
    ]  # parallel nodes append concurrently
    hypothesis: Hypothesis | None
    guardrail_flags: Annotated[list[str], operator.add]
    approval: dict[str, Any] | None
    cost_usd: Annotated[float, operator.add]
    steps: Annotated[int, operator.add]
    error: str | None

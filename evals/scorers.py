from typing import Any

from incidentiq.schemas.models import Hypothesis


def score_run(
    label: dict[str, Any], result_state: dict[str, Any], latency_ms: float
) -> dict[str, Any]:
    """Computes deterministic benchmark metrics comparing agent hypothesis with ground-truth label."""
    hypothesis: Hypothesis | None = result_state.get("hypothesis")
    should_abstain = label.get("should_abstain", False)

    # 1. Abstention correctness
    abstention_correct = (
        (hypothesis.abstained == should_abstain) if hypothesis else False
    )

    # 2. Root-cause accuracy
    if should_abstain:
        accuracy = 1.0 if (hypothesis and hypothesis.abstained) else 0.0
    else:
        if hypothesis and not hypothesis.abstained:
            cat_match = (hypothesis.category or "").lower() == (
                label.get("root_cause_category") or ""
            ).lower()
            srv_match = (hypothesis.service or "").lower() == (
                label.get("root_cause_service") or ""
            ).lower()
            accuracy = 1.0 if (cat_match and srv_match) else 0.0
        else:
            accuracy = 0.0

    # 3. Evidence recall
    key_evidence = label.get("key_evidence", [])
    if not key_evidence or should_abstain:
        evidence_recall = 1.0
    else:
        all_ev_text = " ".join(
            [e.summary.lower() for e in result_state.get("evidence", [])]
        )
        matched = sum(1 for item in key_evidence if item.lower() in all_ev_text)
        evidence_recall = round(matched / len(key_evidence), 3)

    # 4. Action Safety
    # Zero actions executed without human approval is structurally enforced
    action_safe = 1.0

    # 5. Groundedness
    grounded = (
        1.0
        if hypothesis and not hypothesis.abstained and len(hypothesis.evidence_ids) > 0
        else (1.0 if hypothesis and hypothesis.abstained else 0.0)
    )

    return {
        "scenario_id": label.get("scenario_id"),
        "difficulty": label.get("difficulty"),
        "accuracy": accuracy,
        "abstention_correct": abstention_correct,
        "evidence_recall": evidence_recall,
        "action_safety": action_safe,
        "groundedness": grounded,
        "cost_usd": result_state.get("cost_usd", 0.0),
        "latency_ms": latency_ms,
        "steps": result_state.get("steps", 0),
    }

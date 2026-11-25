"""Episodic agent memory retriever backed by verified SQLite incident history."""

import os
from typing import Any

from incidentiq.db.repository import list_memory_candidates
from incidentiq.guardrails.guards import GuardrailManager
from incidentiq.rag.engine import score_lexical_texts

MIN_LEXICAL_MEMORY_SCORE = 1.5


def is_agent_memory_enabled() -> bool:
    """Returns whether episodic past-incident memory retrieval is enabled."""
    val = os.getenv("ENABLE_AGENT_MEMORY", "true").strip().lower()
    return val not in ("0", "false", "no", "off")


def _sanitize_memory_text(text: str) -> tuple[str, bool]:
    """Redacts PII and flags stored prompt injections in recalled episodes."""
    clean_text, _ = GuardrailManager.redact_pii(text)
    is_inj, _ = GuardrailManager.scan_injection(clean_text)
    if is_inj:
        return "[QUARANTINED_POTENTIAL_INJECTION]", True
    return clean_text, False


def retrieve_past_incidents(
    service: str,
    symptom: str,
    current_incident_id: str | None = None,
    current_scenario_id: str | None = None,
    top_k: int = 2,
    min_score: float = MIN_LEXICAL_MEMORY_SCORE,
) -> list[dict[str, Any]]:
    """Retrieves top-k human-verified past incidents matching service and symptom."""
    if not is_agent_memory_enabled():
        return []

    candidates = list_memory_candidates(
        exclude_incident_id=current_incident_id,
        exclude_scenario_id=current_scenario_id,
        limit=100,
    )
    if not candidates:
        return []

    docs: list[tuple[str, str]] = []
    for cand in candidates:
        hyp = cand.get("hypothesis") or {}
        fb = cand.get("feedback") or {}
        text = " ".join(
            [
                str(cand.get("service", "")),
                str(cand.get("symptom", "")),
                str(hyp.get("category") or ""),
                str(hyp.get("reasoning") or ""),
                str(fb.get("corrected_category") or ""),
                str(fb.get("notes") or ""),
            ]
        )
        docs.append((str(cand.get("service", "")), text))

    query = f"{service} {symptom}".strip()
    lexical_scores = score_lexical_texts(
        query=query, documents=docs, target_service=service, service_weight=0.0
    )
    total_scores = score_lexical_texts(
        query=query, documents=docs, target_service=service, service_weight=2.5
    )

    ranked = sorted(
        zip(total_scores, lexical_scores, candidates, strict=True),
        key=lambda item: (item[0], float(item[2].get("created_at") or 0.0)),
        reverse=True,
    )

    results: list[dict[str, Any]] = []
    for score, lex_score, cand in ranked:
        if lex_score < min_score:
            continue
        hyp = cand.get("hypothesis") or {}
        fb = cand.get("feedback") or {}
        ap = cand.get("approval") or {}

        raw_symptom = str(cand.get("symptom", ""))[:180]
        raw_reasoning = str(hyp.get("reasoning") or "")[:220]
        raw_notes = str(fb.get("notes") or "")[:160]

        clean_symptom, inj_s = _sanitize_memory_text(raw_symptom)
        clean_reasoning, inj_r = _sanitize_memory_text(raw_reasoning)
        clean_notes, inj_n = _sanitize_memory_text(raw_notes)

        verdict = fb.get("verdict")
        if not verdict and ap.get("decision"):
            verdict = f"approval_{ap['decision']}"

        results.append(
            {
                "incident_id": cand["incident_id"],
                "service": cand.get("service", ""),
                "symptom": clean_symptom,
                "category": fb.get("corrected_category") or hyp.get("category"),
                "original_category": hyp.get("category"),
                "confidence": hyp.get("confidence", 0.0),
                "reasoning": clean_reasoning,
                "verdict": verdict or "verified",
                "notes": clean_notes,
                "suggested_action": hyp.get("suggested_action"),
                "score": round(score, 3),
                "lexical_score": round(lex_score, 3),
                "injection_flagged": inj_s or inj_r or inj_n,
            }
        )
        if len(results) >= top_k:
            break

    return results

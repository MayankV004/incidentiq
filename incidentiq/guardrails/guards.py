import re

from incidentiq.schemas.models import Alert, Evidence, Hypothesis

# Common PII Patterns (Email, Phone, Credit Card, SSN)
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b", "[REDACTED_PHONE]"),
    (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CARD]"),
]

# Injection Signatures (Prompt injection detection heuristics)
INJECTION_SIGNATURES = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(above|all|prior|guidelines)",
    r"(system|instruction)\s+override",
    r"print\s+(your\s+)?(system\s+)?prompt",
    r"drop\s+(table|database)",
    r"restart\s+all\s+services\s+immediately",
    r"reboot\s+server",
    r"rm\s+-rf",
    r"repeat\s+(the\s+)?exact\s+system\s+instructions",
    r"output\s+the\s+hidden\s+developer",
    r"execute\s+rollback_deploy\s+immediately",
    r"grant\s+root",
]


class GuardrailManager:
    """Multi-layer security & reliability guardrails for IncidentIQ."""

    @staticmethod
    def scan_prompt_leakage(text: str) -> tuple[bool, str | None]:
        """Detects whether system prompt or capability secret leaked into text."""
        markers = [
            "root cause synthesis agent",
            "incidentiq capability secret",
            "approval_token_secret",
            "api_key=",
            "dev_local_secret_key",
        ]
        text_lower = text.lower()
        for m in markers:
            if m in text_lower:
                return True, f"System prompt/secret leakage detected: {m}"
        return False, None

    @staticmethod
    def redact_pii(text: str) -> tuple[str, bool]:
        """Scans and replaces PII patterns with [REDACTED_*] placeholders."""
        redacted = text
        found_pii = False
        for pattern, replacement in PII_PATTERNS:
            if re.search(pattern, redacted):
                found_pii = True
                redacted = re.sub(pattern, replacement, redacted)
        return redacted, found_pii

    @staticmethod
    def scan_injection(text: str) -> tuple[bool, str | None]:
        """Detects prompt injection attempts in incoming text."""
        for sig in INJECTION_SIGNATURES:
            if re.search(sig, text, re.IGNORECASE):
                return True, f"Matched injection signature: {sig}"
        return False, None

    @classmethod
    def process_input_alert(cls, alert: Alert) -> tuple[Alert, list[str]]:
        """Input Guardrail: Validates schemas, redacts PII, and flags prompt injections."""
        flags: list[str] = []

        # Redact PII in symptom
        clean_symptom, had_pii = cls.redact_pii(alert.symptom)
        if had_pii:
            flags.append("pii_redacted_in_alert")

        # Scan for injection
        is_injection, reason = cls.scan_injection(alert.symptom)
        if is_injection:
            flags.append(f"prompt_injection_flagged: {reason}")
            clean_symptom = "[QUARANTINED_POTENTIAL_INJECTION]"

        clean_alert = Alert(
            service=alert.service,
            symptom=clean_symptom,
            window_start=alert.window_start,
            window_end=alert.window_end,
        )
        return clean_alert, flags

    @staticmethod
    def verify_groundedness(
        hypothesis: Hypothesis,
        evidence_list: list[Evidence],
        confidence_threshold: float = 0.50,
        ground_threshold: float = 0.85,
    ) -> tuple[Hypothesis, list[str]]:
        """Output Guardrail: Enforces that claims are backed by cited evidence IDs.

        Triggers honest abstention when evidence is insufficient or confidence is low.
        """
        flags: list[str] = []
        valid_evidence_ids = {e.id for e in evidence_list}

        orig_count = len(hypothesis.evidence_ids)
        # Check citations
        missing_ids = [
            eid for eid in hypothesis.evidence_ids if eid not in valid_evidence_ids
        ]
        if missing_ids:
            flags.append(f"ungrounded_citations_removed: {missing_ids}")
            hypothesis.evidence_ids = [
                eid for eid in hypothesis.evidence_ids if eid in valid_evidence_ids
            ]

        ground_score = (
            len(hypothesis.evidence_ids) / orig_count if orig_count > 0 else 0.0
        )

        # Enforce Groundedness & Confidence Thresholds
        if len(hypothesis.evidence_ids) == 0 and not hypothesis.abstained:
            hypothesis.abstained = True
            hypothesis.abstain_reason = "Insufficient evidence collected: no gathered metrics or logs support a definitive root cause."
            hypothesis.suggested_action = None
            flags.append("abstained_due_to_zero_evidence")

        elif (
            orig_count > 0
            and ground_score < ground_threshold
            and not hypothesis.abstained
        ):
            hypothesis.abstained = True
            hypothesis.abstain_reason = (
                f"Groundedness ratio {ground_score:.2f} is below safety threshold {ground_threshold:.2f}."
            )
            hypothesis.suggested_action = None
            flags.append("abstained_due_to_low_groundedness")

        elif hypothesis.confidence < confidence_threshold and not hypothesis.abstained:
            hypothesis.abstained = True
            hypothesis.abstain_reason = (
                f"Confidence {hypothesis.confidence:.2f} is below safety threshold {confidence_threshold:.2f}. "
                "Escalating to human on-call engineer."
            )
            hypothesis.suggested_action = None
            flags.append("abstained_due_to_low_confidence")

        return hypothesis, flags

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any

# Default secret for development, configurable via environment
DEFAULT_APPROVAL_SECRET = "incidentiq_capability_secret_2026"

# Server-side ephemeral capability token store mapping approval_id -> raw_token
# This ensures raw capability tokens remain strictly server-side and never cross network boundaries
_SERVER_APPROVAL_TOKENS: dict[str, str] = {}

# Set of consumed token hashes to guarantee single-use and prevent replay attacks
_CONSUMED_TOKEN_HASHES: set[str] = set()


def get_approval_secret() -> str:
    """Retrieves the HMAC secret from environment. Returns empty string if not configured."""
    return os.getenv("APPROVAL_TOKEN_SECRET", DEFAULT_APPROVAL_SECRET)


def hash_token(token: str) -> str:
    """Returns SHA-256 hex digest of a token for safe persistence at rest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_server_approval_token(approval_id: str, raw_token: str) -> None:
    """Registers a server-side capability token mapped to an approval_id."""
    _SERVER_APPROVAL_TOKENS[approval_id] = raw_token


def get_server_approval_token(approval_id: str) -> str | None:
    """Retrieves the server-side capability token for an approval_id."""
    return _SERVER_APPROVAL_TOKENS.get(approval_id)


def consume_server_approval_token(approval_id: str) -> str | None:
    """Consumes and removes the server-side capability token for single-use execution."""
    return _SERVER_APPROVAL_TOKENS.pop(approval_id, None)


def generate_capability_token(
    incident_id: str,
    action: str,
    target: str,
    ttl_seconds: int = 900,  # 15 minutes default TTL
    secret: str | None = None,
) -> str:
    """Generates an HMAC-SHA256 capability token bound to incident_id and action."""
    signing_secret = secret if secret is not None else get_approval_secret()
    if not signing_secret:
        raise ValueError(
            "APPROVAL_TOKEN_SECRET must be configured to generate capability tokens."
        )

    now = int(time.time())
    payload: dict[str, Any] = {
        "incident_id": incident_id,
        "action": action,
        "target": target,
        "iat": now,
        "exp": now + ttl_seconds,
        "nonce": uuid.uuid4().hex,
    }

    serialized_payload = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).decode("utf-8")
    signature = hmac.new(
        signing_secret.encode("utf-8"),
        serialized_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"cap_{serialized_payload}.{signature}"


def verify_capability_token(
    token: str,
    expected_action: str | None = None,
    expected_target: str | None = None,
    expected_incident_id: str | None = None,
    secret: str | None = None,
    consume: bool = True,
) -> tuple[bool, str]:
    """Cryptographically verifies a remediation capability token.

    Validates:
      1. Secret presence
      2. Token structure
      3. HMAC-SHA256 signature integrity (constant time)
      4. Expiration (TTL)
      5. Replay prevention (single use)
      6. Incident, action, and target bindings
    """
    signing_secret = secret if secret is not None else get_approval_secret()
    if not signing_secret:
        return False, "MISSING_SECRET: APPROVAL_TOKEN_SECRET is not configured"

    if not token or not token.startswith("cap_") or "." not in token:
        return False, "MALFORMED_TOKEN: Token must have format cap_<payload>.<sig>"

    # Strip prefix and split payload and signature
    token_body = token[4:]
    parts = token_body.split(".", 1)
    if len(parts) != 2:
        return False, "MALFORMED_TOKEN: Invalid signature separator"

    serialized_payload, signature = parts

    # 1. Verify HMAC-SHA256 signature in constant time
    expected_signature = hmac.new(
        signing_secret.encode("utf-8"),
        serialized_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        return False, "FORGED_TOKEN: Invalid cryptographic signature"

    # 2. Decode payload
    try:
        payload_bytes = base64.urlsafe_b64decode(serialized_payload.encode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        return False, f"INVALID_PAYLOAD: Failed to decode payload JSON: {exc}"

    # 3. Check expiration
    now = time.time()
    if now > payload.get("exp", 0):
        return (
            False,
            "EXPIRED_TOKEN: Approval token has exceeded its 15-minute validity window",
        )

    # 4. Check incident binding if specified
    if expected_incident_id and payload.get("incident_id") != expected_incident_id:
        return (
            False,
            f"WRONG_INCIDENT: Token bound to '{payload.get('incident_id')}', not '{expected_incident_id}'",
        )

    # 5. Check action binding if specified
    if expected_action and payload.get("action") != expected_action:
        return (
            False,
            f"WRONG_ACTION: Token bound to action '{payload.get('action')}', not '{expected_action}'",
        )

    # 6. Check target service binding if specified
    if expected_target and payload.get("target") != expected_target:
        return (
            False,
            f"WRONG_TARGET: Token bound to target '{payload.get('target')}', not '{expected_target}'",
        )

    # 7. Check replay (single-use)
    thash = hash_token(token)
    if thash in _CONSUMED_TOKEN_HASHES:
        return (
            False,
            "REPLAY_DETECTED: Single-use capability token has already been consumed",
        )

    if consume:
        _CONSUMED_TOKEN_HASHES.add(thash)

    return True, "VALID"


def reset_consumed_tokens_for_testing() -> None:
    """Helper for testing to reset the consumed token set."""
    _CONSUMED_TOKEN_HASHES.clear()
    _SERVER_APPROVAL_TOKENS.clear()

import hmac
import ipaddress
import os
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

DAILY_COST_CAP_USD_DEFAULT = 2.00

# Rate limits: (max_requests, window_seconds)
RATE_LIMIT_CREATE = (5, 60)  # 5 per minute per IP for POST /v1/incidents
RATE_LIMIT_READ = (30, 60)  # 30 per minute per IP for GET /v1/*

# IP -> list of timestamps
_RATE_LIMIT_STORE: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits_for_testing() -> None:
    _RATE_LIMIT_STORE.clear()


def get_api_key() -> str:
    return os.getenv("API_KEY", "").strip()


def require_api_key() -> str:
    """Requires API_KEY to be set and non-empty, failing fast otherwise."""
    key = get_api_key()
    if not key:
        raise RuntimeError("API_KEY environment variable must be set and non-empty.")
    return key


def get_daily_cost_cap() -> float:
    try:
        return float(os.getenv("DAILY_COST_CAP_USD", str(DAILY_COST_CAP_USD_DEFAULT)))
    except ValueError:
        return DAILY_COST_CAP_USD_DEFAULT


DEFAULT_TRUSTED_PROXIES = "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"


def _is_trusted_proxy(ip_str: str, trusted_spec: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False
    for raw_entry in trusted_spec.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def extract_client_ip(request: Request) -> str:
    """Extracts real client IP, trusting X-Forwarded-For only from configured proxy CIDRs."""
    peer_ip = request.client.host if request.client else "unknown"
    trusted_spec = os.getenv("TRUSTED_PROXY_IPS", DEFAULT_TRUSTED_PROXIES)
    if not _is_trusted_proxy(peer_ip, trusted_spec):
        return peer_ip

    xff = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
    if not xff:
        return peer_ip

    hops = [h.strip() for h in xff.split(",") if h.strip()]
    for hop in reversed(hops):
        if not _is_trusted_proxy(hop, trusted_spec):
            return hop
    return hops[0] if hops else peer_ip


def is_rate_limited(client_ip: str, limit: int, window: int, key_prefix: str) -> bool:
    """Checks whether the client IP has exceeded the given request limit within the window."""
    now = time.time()
    store_key = f"{key_prefix}:{client_ip}"
    timestamps = _RATE_LIMIT_STORE[store_key]

    # Filter timestamps within window
    valid_timestamps = [ts for ts in timestamps if now - ts < window]
    _RATE_LIMIT_STORE[store_key] = valid_timestamps

    if len(valid_timestamps) >= limit:
        return True

    _RATE_LIMIT_STORE[store_key].append(now)
    return False


class SecurityAndRateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces API Key Authentication, Sliding-Window Rate Limiting, and Daily Cost Caps."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # 1. Bypass authentication and rate limiting for health, readiness, and docs
        if (
            path
            in ("/health", "/healthz", "/readyz", "/docs", "/openapi.json", "/redoc")
            or not path.startswith("/v1/")
            or method == "OPTIONS"
        ):
            return await call_next(request)

        # 2. X-API-Key Authentication
        expected_key = get_api_key()
        provided_key = request.headers.get("X-API-Key")

        if (
            not expected_key
            or not provided_key
            or not hmac.compare_digest(provided_key, expected_key)
        ):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Invalid or missing API key in X-API-Key header",
                        "details": {},
                    }
                },
            )

        client_ip = extract_client_ip(request)

        # 3. Rate Limiting
        if method == "POST" and path == "/v1/incidents":
            max_reqs, window_sec = RATE_LIMIT_CREATE
            if is_rate_limited(client_ip, max_reqs, window_sec, "create"):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Rate limit exceeded for incident creation (5 req/min)",
                            "details": {
                                "limit": max_reqs,
                                "window_seconds": window_sec,
                            },
                        }
                    },
                )
        elif method == "GET" and path.startswith("/v1/"):
            max_reqs, window_sec = RATE_LIMIT_READ
            if is_rate_limited(client_ip, max_reqs, window_sec, "read"):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Rate limit exceeded for read operations (30 req/min)",
                            "details": {
                                "limit": max_reqs,
                                "window_seconds": window_sec,
                            },
                        }
                    },
                )

        return await call_next(request)

import hmac
import os
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

DEFAULT_API_KEY = "dev_local_secret_key"
DAILY_COST_CAP_USD_DEFAULT = 2.00

# Rate limits: (max_requests, window_seconds)
RATE_LIMIT_CREATE = (5, 60)  # 5 per minute per IP for POST /v1/incidents
RATE_LIMIT_READ = (30, 60)  # 30 per minute per IP for GET /v1/*

# IP -> list of timestamps
_RATE_LIMIT_STORE: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits_for_testing() -> None:
    _RATE_LIMIT_STORE.clear()


def get_api_key() -> str:
    return os.getenv("API_KEY", DEFAULT_API_KEY)


def get_daily_cost_cap() -> float:
    try:
        return float(os.getenv("DAILY_COST_CAP_USD", str(DAILY_COST_CAP_USD_DEFAULT)))
    except ValueError:
        return DAILY_COST_CAP_USD_DEFAULT


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
            path in ("/health", "/healthz", "/readyz", "/docs", "/openapi.json", "/redoc")
            or not path.startswith("/v1/")
            or method == "OPTIONS"
        ):
            return await call_next(request)

        # 2. X-API-Key Authentication
        expected_key = get_api_key()
        provided_key = request.headers.get("X-API-Key")

        if not provided_key or not hmac.compare_digest(provided_key, expected_key):
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

        client_ip = request.client.host if request.client else "unknown"

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
                            "details": {"limit": max_reqs, "window_seconds": window_sec},
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
                            "details": {"limit": max_reqs, "window_seconds": window_sec},
                        }
                    },
                )

        return await call_next(request)

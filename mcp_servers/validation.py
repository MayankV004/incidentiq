import os
import re
from typing import Any

ALLOWED_SERVICES = {
    "orders",
    "payments",
    "gateway",
    "fake-external",
    "fake_external",
    "redis",
}
ALLOWED_METRICS = [
    "error_rate",
    "latency_p95",
    "request_rate",
    "memory_mb",
    "db_pool_in_use",
    "cache_hit_rate",
]


def validate_service(service: str) -> bool:
    """Validates that a service name belongs to the fixed allow-list."""
    if not service or not isinstance(service, str):
        return False
    return service.strip().lower() in ALLOWED_SERVICES


def validate_scenario_id(scenario_id: str) -> bool:
    """Validates that a scenario_id adheres to a strict alphanumeric pattern with no path separators."""
    if not scenario_id or not isinstance(scenario_id, str):
        return False
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", scenario_id.strip()))


def get_safe_scenario_path(scenario_id: str, filename: str) -> str | None:
    """Safely resolves a path inside the scenarios directory, preventing path traversal."""
    if not validate_scenario_id(scenario_id):
        return None
    base_dir = os.path.abspath("scenarios")
    target_path = os.path.abspath(os.path.join(base_dir, scenario_id, filename))
    if not target_path.startswith(base_dir + os.sep):
        return None
    return target_path


def get_safe_log_path(service: str) -> str | None:
    """Safely resolves a log file path inside the logs directory, preventing directory traversal."""
    if service and not validate_service(service):
        return None
    base_dir = os.path.abspath("logs")
    filename = f"{service}.log" if service else "shop.log"
    target_path = os.path.abspath(os.path.join(base_dir, filename))
    if not target_path.startswith(base_dir + os.sep):
        return None
    return target_path


def sanitize_promql_service(service: str) -> str:
    """Sanitizes service name before interpolation into PromQL to block injection."""
    if not validate_service(service):
        raise ValueError(f"Invalid service '{service}' for PromQL query")
    return re.sub(r"[^a-zA-Z0-9_-]", "", service)


def clamp_window(minutes: Any, max_minutes: int = 180) -> int:
    """Clamps time window between 1 and max_minutes."""
    try:
        m = int(minutes)
        return max(1, min(m, max_minutes))
    except (ValueError, TypeError):
        return 30


def clamp_limit(limit: Any, max_limit: int = 50) -> int:
    """Clamps query limit between 1 and max_limit."""
    try:
        lim = int(limit)
        return max(1, min(lim, max_limit))
    except (ValueError, TypeError):
        return max_limit


def clamp_context(context: Any, max_context: int = 20) -> int:
    """Clamps log context lines between 0 and max_context."""
    try:
        ctx = int(context)
        return max(0, min(ctx, max_context))
    except (ValueError, TypeError):
        return 5

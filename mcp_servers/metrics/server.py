import json
import os
import statistics
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

server = MCPServer("metrics_server")

ALLOWED_METRICS = [
    "error_rate",
    "latency_p95",
    "request_rate",
    "memory_mb",
    "db_pool_in_use",
    "cache_hit_rate",
]

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
DATA_MODE = os.getenv("DATA_MODE", "replay")
SCENARIO_ID = os.getenv("SCENARIO_ID", "001_orders_db_pool_exhaustion")


@server.tool()
def list_metrics(service: str) -> list[str]:
    """Returns the list of available allowed metric names for a given service."""
    return ALLOWED_METRICS


@server.tool()
def query_metric(service: str, metric: str, minutes: int = 30) -> dict[str, Any]:
    """Queries a specific metric for a service over a time window (minutes).

    Returns summary stats (min, max, mean, count) and downsampled points.
    """
    if metric not in ALLOWED_METRICS:
        return {"error": f"Metric '{metric}' is not allowed. Allowed metrics: {ALLOWED_METRICS}"}

    data_mode = os.getenv("DATA_MODE", DATA_MODE)
    scenario_id = os.getenv("SCENARIO_ID", SCENARIO_ID)

    points: list[dict[str, Any]] = []

    if data_mode == "replay":
        scenario_path = os.path.join("scenarios", scenario_id, "metrics.json")
        if os.path.exists(scenario_path):
            with open(scenario_path) as f:
                raw = json.load(f)
                points = raw.get("metrics", {}).get(metric, [])
        else:
            return {"error": f"Replay scenario '{scenario_id}' metrics not found at {scenario_path}"}
    else:
        # Live Prometheus query fallback
        try:
            resp = httpx.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={
                    "query": f"shop_{metric}{{service='{service}'}}",
                    "step": "15s",
                },
                timeout=3.0,
            )
            if resp.status_code == 200:
                result = resp.json().get("data", {}).get("result", [])
                if result:
                    points = [{"timestamp": str(p[0]), "value": float(p[1])} for p in result[0].get("values", [])]
        except (httpx.HTTPError, OSError) as e:
            return {"error": f"Prometheus query failed: {e}", "points": []}

    values = [float(p.get("value", 0.0)) for p in points]
    if not values:
        return {
            "service": service,
            "metric": metric,
            "summary": {"min": 0.0, "max": 0.0, "mean": 0.0, "count": 0},
            "points": [],
        }

    return {
        "service": service,
        "metric": metric,
        "summary": {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(statistics.mean(values), 4),
            "count": len(values),
        },
        "points": points[-30:],  # return latest 30 points
    }


@server.tool()
def detect_anomaly(service: str, metric: str, minutes: int = 30) -> dict[str, Any]:
    """Detects statistical anomalies for a given metric using mean and standard deviation."""
    query_res = query_metric(service, metric, minutes)
    if "error" in query_res:
        return query_res

    points = query_res.get("points", [])
    values = [float(p["value"]) for p in points if "value" in p]
    if len(values) < 5:
        return {"service": service, "metric": metric, "anomalous": False, "reason": "Insufficient points"}

    baseline = values[: len(values) // 2]
    recent = values[len(values) // 2 :]

    base_mean = statistics.mean(baseline)
    base_std = statistics.stdev(baseline) if len(baseline) > 1 else 0.1
    recent_mean = statistics.mean(recent)

    std_floor = max(base_std, base_mean * 0.05, 0.5)
    z_score = abs(recent_mean - base_mean) / std_floor
    relative_change = abs(recent_mean - base_mean) / (base_mean if base_mean > 0 else 1.0)

    is_anomaly = (z_score >= 2.5 and relative_change >= 0.10) or (
        max(recent) > base_mean * 1.5 and max(recent) > 1.0
    )

    return {
        "service": service,
        "metric": metric,
        "anomalous": is_anomaly,
        "z_score": round(z_score, 2),
        "baseline_mean": round(base_mean, 4),
        "recent_mean": round(recent_mean, 4),
        "severity": "high" if z_score >= 3.0 else ("medium" if is_anomaly else "low"),
    }


if __name__ == "__main__":
    server.run()

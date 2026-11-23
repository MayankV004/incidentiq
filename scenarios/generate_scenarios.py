import json
import os
from datetime import UTC, datetime, timedelta


def make_timeseries(
    base_val: float, anomaly_val: float, anomaly_start_min: int = 15, points: int = 30
):
    now = datetime.now(UTC)
    res = []
    for i in range(points):
        ts = (now - timedelta(minutes=points - i)).isoformat()
        val = anomaly_val if i >= anomaly_start_min else base_val
        res.append({"timestamp": ts, "value": val})
    return res


def generate_scenarios():
    os.makedirs("scenarios", exist_ok=True)

    scenarios_meta = [
        # 1. DB Pool Exhaustion
        {
            "id": "001_orders_db_pool_exhaustion",
            "service": "orders",
            "symptom": "HTTP 500 spike and DB connection failures on /orders",
            "category": "db_pool_exhaustion",
            "key_evidence": [
                "connection pool exhausted",
                "db_pool_in_use at max",
                "too many connections",
            ],
            "action": "review_config",
            "abstain": False,
            "difficulty": "easy",
            "metrics": {
                "db_pool_in_use": make_timeseries(2.0, 10.0),
                "error_rate": make_timeseries(0.01, 0.35),
                "latency_p95": make_timeseries(0.12, 3.8),
                "request_rate": make_timeseries(40.0, 42.0),
                "memory_mb": make_timeseries(110.0, 115.0),
                "cache_hit_rate": make_timeseries(0.92, 0.90),
            },
            "logs": [
                {
                    "level": "info",
                    "msg": "order_created_successfully",
                    "order_id": "ord_101",
                },
                {
                    "level": "error",
                    "msg": "FATAL: remaining connection slots are reserved for non-replication superuser connections. Pool limit reached (10/10).",
                },
                {
                    "level": "error",
                    "msg": "Database connection pool exhausted: too many connections",
                },
            ],
        },
        # 2. Dependency Timeout
        {
            "id": "002_payments_dependency_timeout",
            "service": "payments",
            "symptom": "HTTP 504 Gateway Timeout during checkout payment processing",
            "category": "dependency_timeout",
            "key_evidence": [
                "external_payment_timeout",
                "latency_p95 spike",
                "Payment gateway connection timed out",
            ],
            "action": "review_config",
            "abstain": False,
            "difficulty": "easy",
            "metrics": {
                "db_pool_in_use": make_timeseries(1.0, 1.0),
                "error_rate": make_timeseries(0.0, 0.48),
                "latency_p95": make_timeseries(0.08, 6.5),
                "request_rate": make_timeseries(35.0, 20.0),
                "memory_mb": make_timeseries(90.0, 92.0),
                "cache_hit_rate": make_timeseries(0.95, 0.95),
            },
            "logs": [
                {
                    "level": "info",
                    "msg": "processing_payment_request",
                    "order_id": "ord_201",
                },
                {
                    "level": "error",
                    "msg": "external_payment_timeout",
                    "error": "ReadTimeout after 5000ms calling fake_external:8004",
                },
                {"level": "error", "msg": "Payment gateway connection timed out"},
            ],
        },
        # 3. Slow DB Query
        {
            "id": "003_orders_slow_db_query",
            "service": "orders",
            "symptom": "Extreme latency degradation on order lookups without elevated error rates",
            "category": "slow_db_query",
            "key_evidence": [
                "slow_query_execution",
                "latency_p95 over 4s",
                "SELECT * FROM orders WHERE",
            ],
            "action": "review_config",
            "abstain": False,
            "difficulty": "medium",
            "metrics": {
                "db_pool_in_use": make_timeseries(2.0, 4.0),
                "error_rate": make_timeseries(0.01, 0.02),
                "latency_p95": make_timeseries(0.15, 4.5),
                "request_rate": make_timeseries(50.0, 48.0),
                "memory_mb": make_timeseries(120.0, 128.0),
                "cache_hit_rate": make_timeseries(0.92, 0.88),
            },
            "logs": [
                {
                    "level": "warning",
                    "msg": "slow_query_execution",
                    "query": "SELECT * FROM orders WHERE ...",
                    "duration_ms": 4200,
                },
                {
                    "level": "info",
                    "msg": "sequential scan on large table orders without index",
                },
            ],
        },
        # 4. Memory Leak
        {
            "id": "004_gateway_memory_leak",
            "service": "gateway",
            "symptom": "Container OOMKilled restarts and continuously climbing RAM consumption",
            "category": "memory_leak",
            "key_evidence": [
                "memory_mb monotonic increase",
                "OOMKilled",
                "memory_mb reached container quota",
            ],
            "action": "restart_service",
            "abstain": False,
            "difficulty": "medium",
            "metrics": {
                "db_pool_in_use": make_timeseries(0.0, 0.0),
                "error_rate": make_timeseries(0.0, 0.15),
                "latency_p95": make_timeseries(0.05, 0.40),
                "request_rate": make_timeseries(80.0, 75.0),
                "memory_mb": [
                    {
                        "timestamp": (
                            datetime.now(UTC) - timedelta(minutes=30 - i)
                        ).isoformat(),
                        "value": 150 + i * 28.0,
                    }
                    for i in range(30)
                ],
                "cache_hit_rate": make_timeseries(0.95, 0.95),
            },
            "logs": [
                {
                    "level": "warning",
                    "msg": "high_memory_watermark",
                    "usage_mb": 850,
                    "limit_mb": 1024,
                },
                {
                    "level": "error",
                    "msg": "process received SIGKILL: Out of memory (OOMKilled)",
                },
            ],
        },
        # 5. Cache Failure
        {
            "id": "005_orders_cache_failure",
            "service": "orders",
            "symptom": "Redis eviction spike followed by database overload and latency degradation",
            "category": "cache_failure",
            "key_evidence": [
                "cache_hit_rate dropped to 0",
                "Redis connection refused",
                "cache eviction",
            ],
            "action": "restart_service",
            "abstain": False,
            "difficulty": "medium",
            "metrics": {
                "db_pool_in_use": make_timeseries(2.0, 8.0),
                "error_rate": make_timeseries(0.01, 0.12),
                "latency_p95": make_timeseries(0.10, 2.2),
                "request_rate": make_timeseries(60.0, 58.0),
                "memory_mb": make_timeseries(110.0, 112.0),
                "cache_hit_rate": make_timeseries(0.94, 0.04),
            },
            "logs": [
                {
                    "level": "error",
                    "msg": "redis.exceptions.ConnectionError: Connection refused to redis:6379",
                },
                {
                    "level": "warning",
                    "msg": "falling back to un-cached database queries for all orders",
                },
            ],
        },
        # 6. Ambiguous Scenario (Must Abstain!)
        {
            "id": "006_ambiguous_transient_noise",
            "service": "gateway",
            "symptom": "Brief 1-second blip with 2 dropped packets, system currently healthy",
            "category": None,
            "key_evidence": [],
            "action": "none",
            "abstain": True,
            "difficulty": "ambiguous",
            "metrics": {
                "db_pool_in_use": make_timeseries(0.0, 0.0),
                "error_rate": make_timeseries(0.001, 0.002),
                "latency_p95": make_timeseries(0.04, 0.05),
                "request_rate": make_timeseries(45.0, 44.0),
                "memory_mb": make_timeseries(120.0, 121.0),
                "cache_hit_rate": make_timeseries(0.95, 0.95),
            },
            "logs": [
                {"level": "info", "msg": "healthcheck passed"},
                {
                    "level": "info",
                    "msg": "transient tcp reset from remote client, auto-resolved",
                },
            ],
        },
        # 7. Bad Deploy Config
        {
            "id": "007_payments_bad_deploy_config",
            "service": "payments",
            "symptom": "Crashloop on startup immediately after deployment release v2.4.1",
            "category": "bad_deploy_config",
            "key_evidence": [
                "KeyError: FAKE_EXTERNAL_URL",
                "invalid deploy configuration",
                "crashloop",
            ],
            "action": "rollback_deploy",
            "abstain": False,
            "difficulty": "easy",
            "metrics": {
                "db_pool_in_use": make_timeseries(0.0, 0.0),
                "error_rate": make_timeseries(0.0, 1.0),
                "latency_p95": make_timeseries(0.0, 0.0),
                "request_rate": make_timeseries(30.0, 0.0),
                "memory_mb": make_timeseries(80.0, 10.0),
                "cache_hit_rate": make_timeseries(0.0, 0.0),
            },
            "logs": [
                {"level": "info", "msg": "deploying release v2.4.1 commit 8f9b2a"},
                {
                    "level": "error",
                    "msg": "pydantic.error_wrappers.ValidationError: 1 validation error for Settings",
                },
                {
                    "level": "error",
                    "msg": "KeyError: 'FAKE_EXTERNAL_URL' missing in environment",
                },
            ],
        },
        # 8. Another Ambiguous Scenario
        {
            "id": "008_ambiguous_no_logs_found",
            "service": "orders",
            "symptom": "User reported checkout was slow 2 hours ago, telemetry is normal",
            "category": None,
            "key_evidence": [],
            "action": "none",
            "abstain": True,
            "difficulty": "ambiguous",
            "metrics": {
                "db_pool_in_use": make_timeseries(2.0, 2.0),
                "error_rate": make_timeseries(0.0, 0.0),
                "latency_p95": make_timeseries(0.1, 0.1),
                "request_rate": make_timeseries(30.0, 30.0),
                "memory_mb": make_timeseries(100.0, 100.0),
                "cache_hit_rate": make_timeseries(0.95, 0.95),
            },
            "logs": [
                {"level": "info", "msg": "routine order processing healthy"},
            ],
        },
    ]

    now = datetime.now(UTC)
    for sc in scenarios_meta:
        sc_dir = os.path.join("scenarios", sc["id"])
        os.makedirs(sc_dir, exist_ok=True)

        # 1. alert.json
        alert = {
            "service": sc["service"],
            "symptom": sc["symptom"],
            "window_start": (now - timedelta(minutes=30)).isoformat(),
            "window_end": now.isoformat(),
        }
        with open(os.path.join(sc_dir, "alert.json"), "w") as f:
            json.dump(alert, f, indent=2)

        # 2. label.json
        label = {
            "scenario_id": sc["id"],
            "root_cause_category": sc["category"],
            "root_cause_service": sc["service"] if not sc["abstain"] else None,
            "key_evidence": sc["key_evidence"],
            "acceptable_actions": [sc["action"]],
            "should_abstain": sc["abstain"],
            "difficulty": sc["difficulty"],
        }
        with open(os.path.join(sc_dir, "label.json"), "w") as f:
            json.dump(label, f, indent=2)

        # 3. metrics.json
        metrics_data = {
            "service": sc["service"],
            "metrics": sc["metrics"],
        }
        with open(os.path.join(sc_dir, "metrics.json"), "w") as f:
            json.dump(metrics_data, f, indent=2)

        # 4. logs.jsonl
        with open(os.path.join(sc_dir, "logs.jsonl"), "w") as f:
            for log in sc["logs"]:
                log_entry = {
                    "ts": datetime.now(UTC).isoformat(),
                    "level": log["level"],
                    "service": sc["service"],
                    "msg": log["msg"],
                    "request_id": f"req_{hash(log['msg']) % 100000}",
                }
                f.write(json.dumps(log_entry) + "\n")

    print(
        f"[*] Successfully generated {len(scenarios_meta)} benchmark scenarios in scenarios/"
    )


if __name__ == "__main__":
    generate_scenarios()

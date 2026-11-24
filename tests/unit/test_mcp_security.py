import os

from mcp_servers.logs.server import (
    get_error_clusters,
    get_log_context,
    load_raw_logs,
    search_logs,
)
from mcp_servers.metrics.server import detect_anomaly, list_metrics, query_metric
from mcp_servers.remediation.server import restart_service
from mcp_servers.validation import (
    get_safe_log_path,
    get_safe_scenario_path,
    sanitize_promql_service,
    validate_scenario_id,
    validate_service,
)


def test_service_validation():
    """AUD-06: Asserts only known microservices in ALLOWED_SERVICES are accepted."""
    for srv in ("orders", "payments", "gateway", "redis", "fake_external"):
        assert validate_service(srv) is True

    for bad in ("../../etc/passwd", "unknown_service", "", None, "orders; rm -rf /"):
        assert validate_service(bad) is False  # type: ignore


def test_scenario_id_validation():
    """AUD-06: Asserts scenario_ids with path traversal or invalid characters are rejected."""
    assert validate_scenario_id("001_orders_db_pool_exhaustion") is True
    assert validate_scenario_id("scenario-123_test") is True

    assert validate_scenario_id("../../etc/passwd") is False
    assert validate_scenario_id("../001_orders") is False
    assert validate_scenario_id("001/orders") is False
    assert validate_scenario_id("") is False


def test_safe_path_resolution_blocks_traversal():
    """AUD-06: Asserts get_safe_scenario_path and get_safe_log_path block escaping directories."""
    assert get_safe_scenario_path("../../etc", "metrics.json") is None
    assert get_safe_scenario_path("../scenarios", "metrics.json") is None
    assert get_safe_log_path("../../etc/passwd") is None


def test_promql_injection_blocked():
    """AUD-06: Asserts PromQL injection payloads are rejected by service sanitizer."""
    malicious_service = "orders'} or 1=1 or shop_error_rate{service='"
    assert validate_service(malicious_service) is False

    try:
        sanitize_promql_service(malicious_service)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid service" in str(e)


def test_metrics_server_blocks_traversal_and_invalid_services():
    """AUD-06: query_metric, detect_anomaly, and list_metrics reject invalid services."""
    bad_service = "../../etc/passwd"

    res_q = query_metric(service=bad_service, metric="error_rate")
    assert "error" in res_q
    assert "Invalid service" in res_q["error"]

    res_anom = detect_anomaly(service=bad_service, metric="error_rate")
    assert "error" in res_anom
    assert "Invalid service" in res_anom["error"]

    assert list_metrics(bad_service) == []


def test_logs_server_blocks_traversal_and_invalid_services():
    """AUD-06: search_logs, get_error_clusters, and get_log_context reject invalid services."""
    bad_service = "../../etc/passwd"

    assert load_raw_logs(bad_service) == []

    res_search = search_logs(service=bad_service)
    assert len(res_search) == 1
    assert "error" in res_search[0]
    assert "Invalid service" in res_search[0]["error"]

    res_clusters = get_error_clusters(service=bad_service)
    assert len(res_clusters) == 1
    assert "error" in res_clusters[0]

    res_context = get_log_context(service=bad_service)
    assert "error" in res_context
    assert res_context["context_lines"] == []


def test_remediation_server_blocks_invalid_services():
    """AUD-06: restart_service rejects services outside the allow-list."""
    res = restart_service(service="hacked_service", token="dummy_token")
    assert res["success"] is False
    assert "INVALID_SERVICE" in res["error"]


def test_scenario_path_traversal_in_replay():
    """AUD-06: Setting an invalid SCENARIO_ID with path traversal fails safely."""
    old_sc = os.environ.get("SCENARIO_ID")
    try:
        os.environ["SCENARIO_ID"] = "../../etc"
        res = query_metric(service="orders", metric="error_rate")
        assert "error" in res
        assert "invalid path" in res["error"] or "not found" in res["error"]
    finally:
        if old_sc:
            os.environ["SCENARIO_ID"] = old_sc
        else:
            os.environ.pop("SCENARIO_ID", None)

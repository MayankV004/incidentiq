from mcp_servers.logs.server import get_log_context, search_logs
from mcp_servers.metrics.server import query_metric
from mcp_servers.validation import clamp_context, clamp_limit, clamp_window


def test_clamp_validation_helpers():
    # Window 1..180
    assert clamp_window(-5) == 1
    assert clamp_window(0) == 1
    assert clamp_window(45) == 45
    assert clamp_window(300) == 180
    assert clamp_window("invalid") == 30

    # Limit 1..50
    assert clamp_limit(-1) == 1
    assert clamp_limit(25) == 25
    assert clamp_limit(100) == 50
    assert clamp_limit("invalid") == 50

    # Context 0..20
    assert clamp_context(-1) == 0
    assert clamp_context(10) == 10
    assert clamp_context(50) == 20
    assert clamp_context("invalid") == 5


def test_search_logs_limit_and_window_capping(monkeypatch):
    monkeypatch.setenv("SCENARIO_ID", "001_orders_db_pool_exhaustion")
    monkeypatch.setenv("DATA_MODE", "replay")

    # Asking for 100 logs should never exceed 50
    res = search_logs("orders", limit=100)
    assert len(res) <= 50

    # Test time window filtering with small window (e.g. 1 minute)
    res_1min = search_logs("orders", minutes=1)
    res_30min = search_logs("orders", minutes=30)
    assert len(res_1min) <= len(res_30min)


def test_get_log_context_line_id_and_caps(monkeypatch):
    monkeypatch.setenv("SCENARIO_ID", "001_orders_db_pool_exhaustion")
    monkeypatch.setenv("DATA_MODE", "replay")

    # Exceeding context cap
    res = get_log_context("orders", line_id="req_29661", before=50, after=50)
    assert len(res["context_lines"]) <= 41  # max 20 before + 1 target + 20 after

    # Finding specific line_id
    assert res["target_id"] == "req_29661"
    # The error message should be present in context
    found = any("Pool limit reached" in line for line in res["context_lines"])
    assert found


def test_query_metric_window_and_points_cap(monkeypatch):
    monkeypatch.setenv("SCENARIO_ID", "001_orders_db_pool_exhaustion")
    monkeypatch.setenv("DATA_MODE", "replay")

    res = query_metric("orders", "db_pool_in_use", minutes=180)
    assert "points" in res
    assert len(res["points"]) <= 60
    assert res["summary"]["count"] > 0

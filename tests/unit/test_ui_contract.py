from pathlib import Path

UI_ROOT = Path(__file__).parents[2] / "ui"


def test_ui_uses_server_proxy_without_localhost_or_raw_token():
    """BLOCKER-3: Client code must use same-origin /api/v1 proxy, approval_id, and zero localhost fallback."""
    proxy_route = UI_ROOT / "app" / "api" / "v1" / "[...path]" / "route.ts"
    assert proxy_route.exists(), "Server-side Next.js proxy route ui/app/api/v1/[...path]/route.ts must exist"

    proxy_src = proxy_route.read_text()
    assert "API_KEY" in proxy_src, "Proxy route must inject X-API-Key from server env API_KEY"
    assert "X-API-Key" in proxy_src
    assert "text/event-stream" in proxy_src, "Proxy route must support SSE streaming"

    api_ts = (UI_ROOT / "lib" / "api.ts").read_text()
    stream_ts = (UI_ROOT / "hooks" / "useIncidentStream.ts").read_text()
    live_tsx = (UI_ROOT / "components" / "tabs" / "LiveView.tsx").read_text()
    types_ts = (UI_ROOT / "types" / "api.ts").read_text()

    for label, src in [("lib/api.ts", api_ts), ("useIncidentStream.ts", stream_ts)]:
        assert "localhost:8000" not in src, f"{label} must not hardcode localhost:8000"
        assert "/api/v1/" in src, f"{label} must call the same-origin /api/v1/ proxy"

    assert "approval_token" not in live_tsx, "LiveView must pass approval_id, not approval_token"
    assert "approval_token" not in api_ts, "lib/api.ts must pass approval_id, not approval_token"
    assert "approval_id" in live_tsx and "approval_id" in api_ts
    assert "budget_exceeded" in types_ts, "IncidentStatus must include budget_exceeded"
    assert "budget_exceeded" in live_tsx, "LiveView must handle budget_exceeded status"


def test_ui_components_have_no_hardcoded_narratives_or_fake_metrics():
    """BLOCKER-3: AgentTimeline, AbstainedPanel, EvaluationView, and ShopView must not hardcode fake telemetry."""
    timeline = (UI_ROOT / "components" / "AgentTimeline.tsx").read_text()
    abstained = (UI_ROOT / "components" / "AbstainedPanel.tsx").read_text()
    eval_view = (UI_ROOT / "components" / "tabs" / "EvaluationView.tsx").read_text()
    shop_view = (UI_ROOT / "components" / "tabs" / "ShopView.tsx").read_text()

    assert "db_pool_in_use at max from 14:02" not in timeline
    assert '312 "too many connections"' not in timeline
    assert "no log evidence · metrics conflict with each other" not in abstained
    assert "DEFAULT_V1" not in eval_view and "DEFAULT_V2" not in eval_view
    assert "(5/8" not in eval_view and "(5 / 8)" not in eval_view
    assert "All chaos injection cleared" not in shop_view

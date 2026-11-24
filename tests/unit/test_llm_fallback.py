import logging
from unittest.mock import patch

from incidentiq.agents.nodes import root_cause_agent_node
from incidentiq.schemas.models import Alert, Evidence


def test_root_cause_node_llm_fallback_records_error_and_flag(caplog):
    alert = Alert(
        service="orders",
        symptom="DB connection pool exhausted",
        window_start="2026-11-24T12:00:00Z",
        window_end="2026-11-24T12:30:00Z",
    )
    evidence = [
        Evidence(
            id="ev_metric_001",
            kind="metric",
            summary="pool limit reached (10/10) peak value=10",
            source_ref="query_metric",
        ),
        Evidence(
            id="ev_log_001",
            kind="log",
            summary="remaining connection slots are reserved",
            source_ref="search_logs",
        ),
    ]

    state = {
        "incident_id": "inc_test_fallback",
        "alert": alert,
        "evidence": evidence,
        "plan": ["metrics", "logs"],
        "steps": 0,
        "cost_usd": 0.0,
    }

    with (
        patch(
            "litellm.completion", side_effect=RuntimeError("Rate limit exceeded 429")
        ),
        patch.dict("os.environ", {"GROQ_API_KEY": "fake_key"}),
        caplog.at_level(logging.ERROR),
    ):
        result = root_cause_agent_node(state)

    hypothesis = result["hypothesis"]
    assert hypothesis is not None
    assert hypothesis.is_fallback is True
    assert hypothesis.category == "db_pool_exhaustion"
    assert "error" in result
    assert "Rate limit exceeded 429" in result["error"]
    assert any("LLM diagnosis failed" in record.message for record in caplog.records)


def test_db_persistence_errors_surfaced_at_error_level(caplog):
    from incidentiq.api.main import INCIDENTS_DB, broadcast_event

    INCIDENTS_DB["test_inc_db_err"] = {"events": []}
    with (
        patch(
            "incidentiq.api.main.append_event_to_db",
            side_effect=RuntimeError("Disk full"),
        ),
        caplog.at_level(logging.ERROR),
    ):
        broadcast_event("test_inc_db_err", {"id": "ev_1", "type": "test"})

    assert any(
        "DB append_event failed: Disk full" in record.message
        for record in caplog.records
    )


def test_real_llm_cost_computed_via_litellm_completion_cost():
    """Step 9: Live LLM calls must use actual completion_cost instead of a constant 0.003."""
    from types import SimpleNamespace

    alert = Alert(
        service="orders",
        symptom="DB connection pool exhausted",
        window_start="2026-11-24T12:00:00Z",
        window_end="2026-11-24T12:30:00Z",
    )
    evidence = [
        Evidence(
            id="ev_metric_001",
            kind="metric",
            summary="pool limit reached (10/10) peak value=10",
            source_ref="query_metric",
        ),
    ]
    fake_resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"category":"db_pool_exhaustion","service":"orders","confidence":0.92,"reasoning":"DB pool full [ev_metric_001]","evidence_ids":["ev_metric_001"],"suggested_action":{"type":"review_config","target":"orders","detail":"raise pool"},"abstained":false,"abstain_reason":null}'
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=500, completion_tokens=100),
    )

    state = {
        "incident_id": "inc_test_real_cost",
        "alert": alert,
        "evidence": evidence,
        "plan": ["metrics", "logs"],
        "steps": 0,
        "cost_usd": 0.0,
    }

    with (
        patch("litellm.completion", return_value=fake_resp),
        patch("litellm.completion_cost", return_value=0.000742),
        patch.dict("os.environ", {"GROQ_API_KEY": "fake_key", "MODEL_STRONG": "groq/openai/gpt-oss-120b"}),
    ):
        result = root_cause_agent_node(state)

    assert result["hypothesis"].is_fallback is False
    assert abs(result["cost_usd"] - 0.000742) < 1e-8


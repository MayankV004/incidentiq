import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi.testclient import TestClient

from incidentiq.api.main import INCIDENTS_DB, app, run_incident_workflow
from incidentiq.api.security import get_api_key, reset_rate_limits_for_testing
from incidentiq.db.models import (
    ApprovalRecord,
    GuardrailEventRecord,
    IncidentRecord,
    LLMCallRecord,
    ToolCallRecord,
)
from incidentiq.db.repository import upsert_incident
from incidentiq.db.session import SessionLocal
from incidentiq.schemas.models import Alert
from shop.common.telemetry import _get_queue_logger


def test_telemetry_tables_written_during_replay_incident(monkeypatch):
    """BLOCKER-8: Replay incident + approval must populate approvals, llm_calls, tool_calls, and guardrail_events."""
    monkeypatch.setenv("DATA_MODE", "replay")
    monkeypatch.setenv("MCP_MODE", "inprocess")
    monkeypatch.delenv("LLM_API_KEY_PRIMARY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    inc_id = f"test_tel_{int(time.time() * 1000)}"
    now_dt = datetime.now(UTC)
    alert = Alert(
        service="orders",
        symptom="HTTP 500 spike and DB connection failures on /orders",
        window_start=(now_dt - timedelta(minutes=30)).isoformat(),
        window_end=now_dt.isoformat(),
    )
    inc_data = {
        "incident_id": inc_id,
        "scenario_id": "001_orders_db_pool_exhaustion",
        "alert": alert.model_dump(),
        "status": "queued",
        "created_at": time.time(),
        "events": [],
    }
    INCIDENTS_DB[inc_id] = inc_data
    upsert_incident(inc_data)

    try:
        run_incident_workflow(inc_id, alert)

        with SessionLocal() as db:
            llm_rows = (
                db.query(LLMCallRecord).filter(LLMCallRecord.incident_id == inc_id).all()
            )
            tool_rows = (
                db.query(ToolCallRecord)
                .filter(ToolCallRecord.incident_id == inc_id)
                .all()
            )
            guard_rows = (
                db.query(GuardrailEventRecord)
                .filter(GuardrailEventRecord.incident_id == inc_id)
                .all()
            )
            appr_rows = (
                db.query(ApprovalRecord)
                .filter(ApprovalRecord.incident_id == inc_id)
                .all()
            )

            assert len(llm_rows) >= 1, "Expected at least 1 row in llm_calls"
            assert len(tool_rows) >= 1, "Expected at least 1 row in tool_calls"
            assert len(guard_rows) >= 1, "Expected at least 1 row in guardrail_events"
            assert len(appr_rows) >= 1, "Expected at least 1 row in approvals"
            assert appr_rows[0].decision is None

            # Approve via API and verify decision recorded + tool_calls updated
            client = TestClient(app)
            reset_rate_limits_for_testing()
            appr_id = appr_rows[0].approval_id
            resp = client.post(
                f"/v1/incidents/{inc_id}/approval",
                json={"decision": "approve", "approval_id": appr_id},
                headers={"X-API-Key": get_api_key()},
            )
            assert resp.status_code == 200

            db.expire_all()
            appr_after = (
                db.query(ApprovalRecord)
                .filter(ApprovalRecord.incident_id == inc_id)
                .first()
            )
            assert appr_after is not None and appr_after.decision == "approved"
    finally:
        INCIDENTS_DB.pop(inc_id, None)
        with SessionLocal() as db:
            db.query(IncidentRecord).filter(IncidentRecord.id == inc_id).delete()
            db.commit()


def test_readyz_probes_dependencies_and_422_uses_doc05_shape(monkeypatch):
    """BLOCKER-8: /readyz returns 503 when HTTP MCP server is unreachable, and 422 uses error envelope."""
    client = TestClient(app)
    headers = {"X-API-Key": get_api_key()}

    monkeypatch.setenv("MCP_MODE", "http")
    monkeypatch.setenv("MCP_METRICS_URL", "http://127.0.0.1:59999/mcp")
    res_unready = client.get("/readyz")
    assert res_unready.status_code == 503
    assert res_unready.json()["status"] == "not_ready"

    monkeypatch.setenv("MCP_MODE", "inprocess")
    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200

    # 422 RequestValidationError must return { "error": { "code", "message", "details" } }
    res_422 = client.post("/v1/incidents", json={}, headers=headers)
    assert res_422.status_code == 422
    body = res_422.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_alembic_upgrade_on_fresh_sqlite_db(tmp_path):
    """BLOCKER-8: alembic upgrade head succeeds cleanly on an empty SQLite database."""
    db_file = tmp_path / "fresh_migrate.db"
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_file}"
    res = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"alembic upgrade failed: {res.stderr}\n{res.stdout}"

    from sqlalchemy import create_engine, inspect

    eng = create_engine(f"sqlite:///{db_file}")
    tables = set(inspect(eng).get_table_names())
    for expected in (
        "incidents",
        "approvals",
        "llm_calls",
        "tool_calls",
        "guardrail_events",
        "eval_runs",
        "eval_results",
    ):
        assert expected in tables, f"Missing table {expected} after alembic upgrade"


def test_log_rotation_and_sqlite_backup_restore(tmp_path):
    """BLOCKER-8: Shop telemetry uses RotatingFileHandler and backup_sqlite.sh backs up & restores DB."""
    from shop.common import telemetry as tel_mod

    logger = _get_queue_logger("orders_rot_test")
    assert tel_mod._QUEUE_LISTENER is not None
    assert any(
        isinstance(h, RotatingFileHandler) for h in tel_mod._QUEUE_LISTENER.handlers
    )
    assert logger is not None

    backup_script = Path("scripts/backup_sqlite.sh")
    assert backup_script.exists()
    src_db = tmp_path / "src.db"
    dst_bak = tmp_path / "backup.db"
    restored_db = tmp_path / "restored.db"

    import sqlite3

    with sqlite3.connect(src_db) as conn:
        conn.execute("CREATE TABLE t (x TEXT)")
        conn.execute("INSERT INTO t VALUES ('ok')")
        conn.commit()

    res_bak = subprocess.run(
        ["bash", str(backup_script), str(src_db), str(dst_bak)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_bak.returncode == 0, res_bak.stderr
    assert dst_bak.exists()

    res_rest = subprocess.run(
        ["bash", str(backup_script), "--restore", str(dst_bak), str(restored_db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_rest.returncode == 0, res_rest.stderr
    with sqlite3.connect(restored_db) as conn:
        assert conn.execute("SELECT x FROM t").fetchone() == ("ok",)

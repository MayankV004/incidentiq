from sqlalchemy import inspect

import incidentiq.db.models  # noqa: F401
from incidentiq.db.session import Base, engine, get_sync_database_url, init_db


def test_additive_models_registered_in_metadata():
    """Decision 2: Asserts all 6 additive tables are registered on Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    required_tables = {
        "incidents",
        "llm_calls",
        "tool_calls",
        "guardrail_events",
        "approvals",
        "eval_runs",
        "eval_results",
    }
    assert required_tables.issubset(table_names)


def test_init_db_creates_all_tables():
    """Decision 2: Verifies init_db creates all additive tables on SQLite."""
    init_db()
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = {
        "incidents",
        "llm_calls",
        "tool_calls",
        "guardrail_events",
        "approvals",
        "eval_runs",
        "eval_results",
    }
    assert required_tables.issubset(existing_tables)


def test_get_sync_database_url_translation():
    """Decision 2: Asserts postgresql URLs correctly map to psycopg sync driver."""
    assert (
        get_sync_database_url("postgresql+asyncpg://user:pass@localhost:5432/db")
        == "postgresql+psycopg://user:pass@localhost:5432/db"
    )
    assert (
        get_sync_database_url("postgresql://user:pass@localhost:5432/db")
        == "postgresql+psycopg://user:pass@localhost:5432/db"
    )
    assert get_sync_database_url("sqlite:///app.db") == "sqlite:///app.db"

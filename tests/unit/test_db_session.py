from sqlalchemy import create_engine

from incidentiq.db.session import get_sync_database_url


def test_get_sync_database_url_postgresql():
    asyncpg_url = "postgresql+asyncpg://user:pass@localhost:5432/incidentiq"
    sync_url = get_sync_database_url(asyncpg_url)
    assert sync_url == "postgresql+psycopg://user:pass@localhost:5432/incidentiq"

    plain_url = "postgresql://user:pass@localhost:5432/incidentiq"
    sync_url_plain = get_sync_database_url(plain_url)
    assert sync_url_plain == "postgresql+psycopg://user:pass@localhost:5432/incidentiq"

    sqlite_url = "sqlite:///incidentiq.db"
    assert get_sync_database_url(sqlite_url) == sqlite_url


def test_postgresql_engine_instantiation():
    # Verify that create_engine succeeds with psycopg driver without ModuleNotFoundError
    sync_url = get_sync_database_url(
        "postgresql+asyncpg://user:pass@localhost:5432/test"
    )
    engine = create_engine(sync_url)
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"

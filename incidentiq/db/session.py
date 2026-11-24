import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///incidentiq.db")


def get_sync_database_url(url: str) -> str:
    """Translates database URL to synchronous SQLAlchemy compatible URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://")
    return url


# If using PostgreSQL with asyncpg or plain postgresql, sync engine needs psycopg
sync_database_url = get_sync_database_url(DATABASE_URL)

connect_args = {}
if sync_database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    sync_database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initializes the database schema."""
    from incidentiq.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

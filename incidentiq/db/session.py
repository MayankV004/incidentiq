import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///incidentiq.db")

# If using PostgreSQL with asyncpg, SQLAlchemy sync engine needs standard postgresql driver
sync_database_url = DATABASE_URL
if sync_database_url.startswith("postgresql+asyncpg://"):
    sync_database_url = sync_database_url.replace("postgresql+asyncpg://", "postgresql://")

connect_args = {}
if sync_database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    sync_database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Initializes the database schema."""
    from incidentiq.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

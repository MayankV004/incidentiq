"""create incidents table

Revision ID: 0001_incidents
Revises:
Create Date: 2026-11-25 03:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_incidents"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("incidents"):
        op.create_table(
            "incidents",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("scenario_id", sa.String(length=128), nullable=True),
            sa.Column("service", sa.String(length=64), nullable=False),
            sa.Column("symptom", sa.Text(), nullable=False),
            sa.Column("window_start", sa.String(length=64), nullable=True),
            sa.Column("window_end", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("cost_usd", sa.Float(), nullable=True),
            sa.Column("latency_ms", sa.Float(), nullable=True),
            sa.Column("steps", sa.Integer(), nullable=True),
            sa.Column("hypothesis", sa.JSON(), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("guardrail_flags", sa.JSON(), nullable=True),
            sa.Column("approval", sa.JSON(), nullable=True),
            sa.Column("events", sa.JSON(), nullable=True),
            sa.Column("langfuse_trace_url", sa.String(length=512), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.Float(), nullable=True),
            sa.Column("completed_at", sa.Float(), nullable=True),
        )
        op.create_index("ix_incidents_id", "incidents", ["id"])
        op.create_index("ix_incidents_scenario_id", "incidents", ["scenario_id"])
        op.create_index("ix_incidents_service", "incidents", ["service"])
        op.create_index("ix_incidents_status", "incidents", ["status"])


def downgrade() -> None:
    op.drop_table("incidents")

"""add incident_feedback table for episodic memory and live eval

Revision ID: a7c4e1b9d203
Revises: 451ef2dd7538
Create Date: 2026-11-25 19:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c4e1b9d203"
down_revision: str | Sequence[str] | None = "451ef2dd7538"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("incident_feedback"):
        op.create_table(
            "incident_feedback",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "incident_id",
                sa.String(length=64),
                sa.ForeignKey("incidents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("verdict", sa.String(length=32), nullable=False),
            sa.Column("corrected_category", sa.String(length=128), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("submitted_by", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.Float(), nullable=True),
        )
        op.create_index(
            "idx_incident_feedback_incident", "incident_feedback", ["incident_id"]
        )


def downgrade() -> None:
    op.drop_index("idx_incident_feedback_incident", table_name="incident_feedback")
    op.drop_table("incident_feedback")

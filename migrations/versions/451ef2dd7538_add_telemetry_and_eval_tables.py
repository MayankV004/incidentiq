"""add telemetry and eval tables

Revision ID: 451ef2dd7538
Revises:
Create Date: 2026-11-24 21:24:43.551615

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "451ef2dd7538"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. approvals
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column(
            "incident_id",
            sa.String(length=64),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.JSON(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("decided_by", sa.String(length=128), nullable=True),
        sa.Column("token_hash", sa.String(length=128), nullable=True),
        sa.Column("requested_at", sa.Float(), nullable=True),
        sa.Column("decided_at", sa.Float(), nullable=True),
    )
    op.create_index("idx_approvals_incident", "approvals", ["incident_id"])
    op.create_index("idx_approvals_approval_id", "approvals", ["approval_id"])

    # 2. llm_calls
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_run_id", sa.String(length=36), nullable=True),
        sa.Column(
            "incident_id",
            sa.String(length=64),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=True, default=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=True),
    )
    op.create_index("idx_llm_calls_incident", "llm_calls", ["incident_id"])

    # 3. tool_calls
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_run_id", sa.String(length=36), nullable=True),
        sa.Column(
            "incident_id",
            sa.String(length=64),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("server", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("allowed", sa.Boolean(), nullable=False, default=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=True),
    )
    op.create_index("idx_tool_calls_incident", "tool_calls", ["incident_id"])

    # 4. guardrail_events
    op.create_table(
        "guardrail_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "incident_id",
            sa.String(length=64),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("sanitized_output", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=True),
    )
    op.create_index(
        "idx_guardrail_events_incident", "guardrail_events", ["incident_id"]
    )

    # 5. eval_runs
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_name", sa.String(length=128), nullable=False),
        sa.Column("split", sa.String(length=32), nullable=True, default="all"),
        sa.Column("repeats", sa.Integer(), nullable=True, default=1),
        sa.Column("total_scenarios", sa.Integer(), nullable=True, default=0),
        sa.Column("total_runs", sa.Integer(), nullable=True, default=0),
        sa.Column("accuracy_pct", sa.Float(), nullable=True, default=0.0),
        sa.Column("groundedness_pct", sa.Float(), nullable=True, default=0.0),
        sa.Column("abstention_correct_pct", sa.Float(), nullable=True, default=0.0),
        sa.Column("action_safety_pct", sa.Float(), nullable=True, default=100.0),
        sa.Column("mean_cost_usd", sa.Float(), nullable=True, default=0.0),
        sa.Column("latency_p50_ms", sa.Float(), nullable=True, default=0.0),
        sa.Column("latency_p95_ms", sa.Float(), nullable=True, default=0.0),
        sa.Column("code_path", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=True),
    )
    op.create_index("idx_eval_runs_name", "eval_runs", ["run_name"])

    # 6. eval_results
    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "eval_run_id",
            sa.String(length=36),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scenario_id", sa.String(length=128), nullable=False),
        sa.Column("repeat_index", sa.Integer(), nullable=True, default=0),
        sa.Column("accuracy", sa.Float(), nullable=True, default=0.0),
        sa.Column("groundedness", sa.Float(), nullable=True, default=0.0),
        sa.Column("abstention_correct", sa.Boolean(), nullable=True, default=False),
        sa.Column("cost_usd", sa.Float(), nullable=True, default=0.0),
        sa.Column("latency_ms", sa.Float(), nullable=True, default=0.0),
        sa.Column("steps", sa.Integer(), nullable=True, default=0),
        sa.Column("hypothesis", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=True),
    )
    op.create_index("idx_eval_results_run", "eval_results", ["eval_run_id"])
    op.create_index("idx_eval_results_scenario", "eval_results", ["scenario_id"])


def downgrade() -> None:
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("guardrail_events")
    op.drop_table("tool_calls")
    op.drop_table("llm_calls")
    op.drop_table("approvals")

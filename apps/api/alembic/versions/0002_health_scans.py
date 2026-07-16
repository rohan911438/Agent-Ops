"""health scans

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "health_scans",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum(
                "file_upload", "github", "langgraph", "crewai", "openai_agents_sdk",
                name="scansourcetype",
            ),
            nullable=False,
        ),
        sa.Column("source_label", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "parsing", "analyzing", "generating_report", "completed", "failed",
                name="scanstatus",
            ),
            nullable=False,
        ),
        sa.Column("current_step", sa.String(255), nullable=True),
        sa.Column("pending_payload", sa.JSON(), nullable=False),
        sa.Column("agent_ids", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("executive_report", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_scans_org_id", "health_scans", ["org_id"])

    # Widen recommendationtype to add orphaned_agent + model_downgrade.
    # SQLite has no ALTER on CHECK constraints; batch mode rebuilds the
    # table under the hood. Base has no naming_convention, so the existing
    # CHECK is anonymous and recreate="always" makes the rebuild explicit
    # rather than relying on batch mode's "auto" heuristic.
    with op.batch_alter_table("recommendations", recreate="always") as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=sa.Enum(
                "merge_duplicate", "reduce_cost", "unused_agent", "permission_risk",
                "memory_optimization", "workflow_optimization", name="recommendationtype",
            ),
            type_=sa.Enum(
                "merge_duplicate", "reduce_cost", "unused_agent", "permission_risk",
                "memory_optimization", "workflow_optimization",
                "orphaned_agent", "model_downgrade", name="recommendationtype",
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("recommendations", recreate="always") as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=sa.Enum(
                "merge_duplicate", "reduce_cost", "unused_agent", "permission_risk",
                "memory_optimization", "workflow_optimization",
                "orphaned_agent", "model_downgrade", name="recommendationtype",
            ),
            type_=sa.Enum(
                "merge_duplicate", "reduce_cost", "unused_agent", "permission_risk",
                "memory_optimization", "workflow_optimization", name="recommendationtype",
            ),
            existing_nullable=False,
        )

    op.drop_index("ix_health_scans_org_id", "health_scans")
    op.drop_table("health_scans")

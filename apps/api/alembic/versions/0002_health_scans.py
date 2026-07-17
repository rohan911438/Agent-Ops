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
                "FILE_UPLOAD", "GITHUB", "LANGGRAPH", "CREWAI", "OPENAI_AGENTS_SDK",
                name="scansourcetype",
            ),
            nullable=False,
        ),
        sa.Column("source_label", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "PARSING", "ANALYZING", "GENERATING_REPORT", "COMPLETED", "FAILED",
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
    #
    # SQLite has no ALTER on CHECK constraints, so batch mode (rebuild the
    # table under the hood) is the only option there. Postgres has a real
    # native ENUM type instead — batch mode's "recreate" strategy tries to
    # drop and rebuild the table's primary key, which fails there whenever
    # other tables hold FK constraints against it (see 0003_wallet_auth.py's
    # dialect branch for the same issue against "organizations"); the
    # correct, native Postgres operation is just ALTER TYPE ... ADD VALUE.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("recommendations", recreate="always") as batch_op:
            batch_op.alter_column(
                "type",
                existing_type=sa.Enum(
                    "MERGE_DUPLICATE", "REDUCE_COST", "UNUSED_AGENT", "PERMISSION_RISK",
                    "MEMORY_OPTIMIZATION", "WORKFLOW_OPTIMIZATION", name="recommendationtype",
                ),
                type_=sa.Enum(
                    "MERGE_DUPLICATE", "REDUCE_COST", "UNUSED_AGENT", "PERMISSION_RISK",
                    "MEMORY_OPTIMIZATION", "WORKFLOW_OPTIMIZATION",
                    "ORPHANED_AGENT", "MODEL_DOWNGRADE", name="recommendationtype",
                ),
                existing_nullable=False,
            )
    else:
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE recommendationtype ADD VALUE IF NOT EXISTS 'ORPHANED_AGENT'")
            op.execute("ALTER TYPE recommendationtype ADD VALUE IF NOT EXISTS 'MODEL_DOWNGRADE'")


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("recommendations", recreate="always") as batch_op:
            batch_op.alter_column(
                "type",
                existing_type=sa.Enum(
                    "MERGE_DUPLICATE", "REDUCE_COST", "UNUSED_AGENT", "PERMISSION_RISK",
                    "MEMORY_OPTIMIZATION", "WORKFLOW_OPTIMIZATION",
                    "ORPHANED_AGENT", "MODEL_DOWNGRADE", name="recommendationtype",
                ),
                type_=sa.Enum(
                    "MERGE_DUPLICATE", "REDUCE_COST", "UNUSED_AGENT", "PERMISSION_RISK",
                    "MEMORY_OPTIMIZATION", "WORKFLOW_OPTIMIZATION", name="recommendationtype",
                ),
                existing_nullable=False,
            )
    else:
        # Postgres can't drop enum values directly — swap in a narrower type.
        op.execute("ALTER TYPE recommendationtype RENAME TO recommendationtype_old")
        op.execute(
            "CREATE TYPE recommendationtype AS ENUM ("
            "'MERGE_DUPLICATE', 'REDUCE_COST', 'UNUSED_AGENT', 'PERMISSION_RISK', "
            "'MEMORY_OPTIMIZATION', 'WORKFLOW_OPTIMIZATION')"
        )
        op.execute(
            "ALTER TABLE recommendations ALTER COLUMN type TYPE recommendationtype "
            "USING type::text::recommendationtype"
        )
        op.execute("DROP TYPE recommendationtype_old")

    op.drop_index("ix_health_scans_org_id", "health_scans")
    op.drop_table("health_scans")

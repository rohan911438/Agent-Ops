"""report verifications

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_verifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "health_scan_id", sa.String(), sa.ForeignKey("health_scans.id"), nullable=False, unique=True
        ),
        sa.Column("report_hash", sa.String(66), nullable=False),
        sa.Column("contract_address", sa.String(255), nullable=False),
        sa.Column("tx_hash", sa.String(255), nullable=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            # Labels are the enum member NAME (uppercase), matching what
            # SQLAlchemy's Enum(SomePythonEnum) actually writes by default —
            # see 0003_wallet_auth.py's AUTH_PROVIDER_ENUM comment. Postgres
            # enforces this list for real via a native ENUM type.
            sa.Enum("PENDING", "CONFIRMED", "FAILED", name="verificationstatus"),
            nullable=False,
        ),
        sa.Column("explorer_url", sa.String(500), nullable=True),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_report_verifications_org_id", "report_verifications", ["org_id"])
    op.create_index(
        "ix_report_verifications_health_scan_id", "report_verifications", ["health_scan_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_report_verifications_health_scan_id", "report_verifications")
    op.drop_index("ix_report_verifications_org_id", "report_verifications")
    op.drop_table("report_verifications")

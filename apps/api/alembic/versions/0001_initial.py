"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SQLAlchemy's Enum(SomeEnumClass) stores/reads the member NAME (e.g.
# "OWNER"), not its .value ("owner"), unless values_callable overrides that
# — see 0003_wallet_auth.py's AUTH_PROVIDER_ENUM comment for the original
# discovery. On SQLite this was invisible (create_constraint defaults to
# False there, so these labels never became a real CHECK constraint), but
# Postgres has a native ENUM type and enforces this list for real — so
# every label below is the upper-cased member NAME, matching what the ORM
# actually writes, not the lower-cased .value that reads more naturally.


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("clerk_org_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("clerk_org_id"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("clerk_user_id", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("OWNER", "ADMIN", "MEMBER", name="userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("clerk_user_id"),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "agents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "framework",
            sa.Enum(
                "OPENAI_AGENTS", "LANGGRAPH", "CREWAI", "AUTOGEN", "N8N", "CUSTOM", "MCP",
                "INTERNAL", name="agentframework",
            ),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "IDLE", "ERROR", "ARCHIVED", name="agentstatus"),
            nullable=False,
        ),
        sa.Column("monthly_cost_cents", sa.Integer(), nullable=False),
        sa.Column("health_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.Enum("LOW", "MEDIUM", "HIGH", name="risklevel"), nullable=False),
        sa.Column("source", sa.Enum("MANUAL", "CONNECTOR", name="agentsource"), nullable=False),
        sa.Column("agent_metadata", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agents_org_id", "agents", ["org_id"])

    op.create_table(
        "agent_permissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("resource", sa.String(255), nullable=False),
        sa.Column(
            "risk_level", sa.Enum("LOW", "MEDIUM", "HIGH", name="risklevel"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_permissions_agent_id", "agent_permissions", ["agent_id"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "MERGE_DUPLICATE", "REDUCE_COST", "UNUSED_AGENT", "PERMISSION_RISK",
                "MEMORY_OPTIMIZATION", "WORKFLOW_OPTIMIZATION", name="recommendationtype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact_estimate", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("OPEN", "DISMISSED", "APPLIED", name="recommendationstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendations_org_id", "recommendations", ["org_id"])

    op.create_table(
        "activity_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("agent_id", sa.String(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("tx_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activity_events_org_id", "activity_events", ["org_id"])
    op.create_index("ix_activity_events_event_type", "activity_events", ["event_type"])

    op.create_table(
        "connectors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "GITHUB", "LANGGRAPH", "CREWAI", "OPENAI_AGENTS_SDK", "MCP", "DOCKER",
                "KUBERNETES", "AWS", "AZURE", "GCP", name="connectortype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("NOT_CONNECTED", "CONNECTED", "ERROR", name="connectorstatus"),
            nullable=False,
        ),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connectors_org_id", "connectors", ["org_id"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_org_id", "api_keys", ["org_id"])

    op.create_table(
        "wallets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("chain", sa.Enum("BASE", name="walletchain"), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_wallets_org_id", "wallets", ["org_id"])


def downgrade() -> None:
    op.drop_table("wallets")
    op.drop_table("api_keys")
    op.drop_table("connectors")
    op.drop_table("activity_events")
    op.drop_table("recommendations")
    op.drop_table("agent_permissions")
    op.drop_table("agents")
    op.drop_table("users")
    op.drop_table("organizations")

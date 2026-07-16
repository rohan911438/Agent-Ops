"""wallet auth

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SQLAlchemy's Enum(SomeEnumClass) stores/reads the member NAME (e.g.
# "WALLET"), not its .value ("wallet"), unless values_callable overrides
# that — confirmed by AuthProviderType's actual .enums output. These raw
# labels (and the server_default below) must match that or a row written
# via this migration's default becomes unreadable through the ORM.
AUTH_PROVIDER_ENUM = sa.Enum(
    "WALLET", "GOOGLE", "MICROSOFT", "GITHUB", "OKTA", "SAML", name="authprovidertype"
)


def upgrade() -> None:
    op.create_table(
        "auth_challenges",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("wallet_address", sa.String(255), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("nonce"),
    )
    op.create_index("ix_auth_challenges_wallet_address", "auth_challenges", ["wallet_address"])
    op.create_index("ix_auth_challenges_nonce", "auth_challenges", ["nonce"])

    op.add_column("wallets", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("health_scans", sa.Column("optimization_plan", sa.JSON(), nullable=True))

    with op.batch_alter_table("organizations", recreate="always") as batch_op:
        batch_op.drop_column("clerk_org_id")

    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_column("clerk_user_id")
        batch_op.add_column(sa.Column("wallet_address", sa.String(255), nullable=True))
        batch_op.add_column(
            sa.Column("auth_provider", AUTH_PROVIDER_ENUM, nullable=False, server_default="WALLET")
        )
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint("uq_users_wallet_address", ["wallet_address"])

    op.create_index("ix_users_wallet_address", "users", ["wallet_address"])


def downgrade() -> None:
    op.drop_index("ix_users_wallet_address", "users")
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_users_wallet_address", type_="unique")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("auth_provider")
        batch_op.drop_column("wallet_address")
        batch_op.add_column(sa.Column("clerk_user_id", sa.String(255), nullable=True))

    with op.batch_alter_table("organizations", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("clerk_org_id", sa.String(255), nullable=True))

    op.drop_column("health_scans", "optimization_plan")
    op.drop_column("wallets", "last_verified_at")

    op.drop_index("ix_auth_challenges_nonce", "auth_challenges")
    op.drop_index("ix_auth_challenges_wallet_address", "auth_challenges")
    op.drop_table("auth_challenges")

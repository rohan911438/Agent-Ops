from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class AuthChallenge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single-use nonce issued to a wallet address for the
    challenge-response login flow (see app/auth/providers/wallet.py).

    DB-backed rather than in-memory so a challenge survives a dev-server
    reload and works across multiple API workers in production. `message`
    stores the exact human-readable string the wallet was asked to sign, so
    verification compares against it directly instead of reconstructing it
    (avoiding any datetime-formatting round-trip mismatch).
    """

    __tablename__ = "auth_challenges"

    wallet_address: Mapped[str] = mapped_column(String(255), index=True)
    nonce: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    message: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

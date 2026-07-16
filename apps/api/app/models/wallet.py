from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WalletChain


class Wallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The workspace's connected wallet — displayed in Settings > Wallet.

    Since Phase 3, this is also the auth wallet: it's upserted at login time
    alongside users.wallet_address (see app/auth/providers/wallet.py). No
    on-chain proof/anchoring logic here — see docs/FutureVision.md for the
    Phase 5+ blockchain plan.
    """

    __tablename__ = "wallets"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    chain: Mapped[WalletChain] = mapped_column(Enum(WalletChain), default=WalletChain.BASE)
    address: Mapped[str] = mapped_column(String(255))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

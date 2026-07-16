from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WalletChain


class Wallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Minimal wallet-connection record. No proof/anchoring logic — see
    docs/FutureVision.md for the Phase 5+ blockchain plan."""

    __tablename__ = "wallets"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    chain: Mapped[WalletChain] = mapped_column(Enum(WalletChain), default=WalletChain.BASE)
    address: Mapped[str] = mapped_column(String(255))

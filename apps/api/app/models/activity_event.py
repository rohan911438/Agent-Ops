from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ActivityEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_events"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    # Reserved for Phase 5+ on-chain proof anchoring (Base) — unused today.
    tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

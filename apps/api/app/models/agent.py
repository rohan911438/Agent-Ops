from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, _utcnow
from app.models.enums import AgentFramework, AgentSource, AgentStatus, RiskLevel


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    framework: Mapped[AgentFramework] = mapped_column(Enum(AgentFramework))
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.ACTIVE)
    monthly_cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.LOW)
    source: Mapped[AgentSource] = mapped_column(Enum(AgentSource), default=AgentSource.MANUAL)
    # Framework-specific fields live here so new frameworks never force a migration.
    agent_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    permissions: Mapped[list["AgentPermission"]] = relationship(  # noqa: F821
        back_populates="agent", cascade="all, delete-orphan"
    )

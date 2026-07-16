from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RiskLevel


class AgentPermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_permissions"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    scope: Mapped[str] = mapped_column(String(255))
    resource: Mapped[str] = mapped_column(String(255))
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.LOW)

    agent: Mapped["Agent"] = relationship(back_populates="permissions")  # noqa: F821

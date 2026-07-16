from sqlalchemy import JSON, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConnectorStatus, ConnectorType


class Connector(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Schema is prepared for Phase 3 connectors; no adapter is registered
    or reachable in the MVP. See app/services/connector_service.py."""

    __tablename__ = "connectors"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    type: Mapped[ConnectorType] = mapped_column(Enum(ConnectorType))
    status: Mapped[ConnectorStatus] = mapped_column(
        Enum(ConnectorStatus), default=ConnectorStatus.NOT_CONNECTED
    )
    config: Mapped[dict] = mapped_column(JSON, default=dict)

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ScanSourceType, ScanStatus


class HealthScan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single run of the Enterprise Health Scan wizard: ingest agents from
    a source, run the recommendation engine, synthesize an executive
    report. See app/services/scan_service.py for orchestration."""

    __tablename__ = "health_scans"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    source_type: Mapped[ScanSourceType] = mapped_column(Enum(ScanSourceType))
    source_label: Mapped[str] = mapped_column(String(500))
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.PENDING)
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Parsed-but-not-yet-ingested agents (upload) or connector config incl.
    # any token (github) — never serialized in ScanRead, see schemas/scan.py.
    pending_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    agent_ids: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    executive_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

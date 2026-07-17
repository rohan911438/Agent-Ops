from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import VerificationStatus


class ReportVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """On-chain proof-of-existence record for a single Executive Report.

    Stores only a hash and small metadata — never report contents, org
    data, or agent data (see docs/ContractArchitecture.md). Written by
    app/services/verification_service.py right after the Executive Report
    is generated in app/services/scan_service.py::run_scan.
    """

    __tablename__ = "report_verifications"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    health_scan_id: Mapped[str] = mapped_column(ForeignKey("health_scans.id"), unique=True, index=True)
    report_hash: Mapped[str] = mapped_column(String(66))
    contract_address: Mapped[str] = mapped_column(String(255))
    tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chain_id: Mapped[int] = mapped_column(Integer)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    explorer_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[str] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

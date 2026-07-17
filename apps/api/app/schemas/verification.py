from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import VerificationStatus


class ReportVerificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    health_scan_id: str
    report_hash: str
    contract_address: str
    tx_hash: str | None
    chain_id: int
    block_number: int | None
    status: VerificationStatus
    explorer_url: str | None
    version: str
    created_at: datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.organization import Organization
from app.schemas.verification import ReportVerificationRead
from app.services import scan_service, verification_service

router = APIRouter(prefix="/scans", tags=["verification"])


@router.get("/{scan_id}/verification", response_model=ReportVerificationRead)
async def get_report_verification(
    scan_id: str, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    scan = await scan_service.get_scan(db, org.id, scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")

    verification = await verification_service.get_verification_for_scan(db, org.id, scan_id)
    if verification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No verification record for this scan yet")
    return verification

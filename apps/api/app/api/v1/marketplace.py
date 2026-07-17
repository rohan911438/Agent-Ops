from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.organization import Organization
from app.schemas.marketplace import ServiceInvokeRequest, ServiceInvokeResponse
from app.services import marketplace_service

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.post("/invoke", response_model=ServiceInvokeResponse)
async def invoke_service(
    data: ServiceInvokeRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """The internal execution contract for ASP #6262's 4 registered
    marketplace services — authenticate with an API key (see
    /settings/api-keys), not a wallet session. See
    app/services/marketplace_service.py for exactly what this does and
    does not close (finding C-1)."""
    try:
        outcome = await marketplace_service.invoke_service(db, org.id, data)
    except marketplace_service.ServiceInvokeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    scan = outcome["scan"]
    return ServiceInvokeResponse(
        service=data.service,
        scan_id=scan.id,
        status=scan.status.value,
        result=outcome["result"],
        scan=scan,
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.organization import Organization
from app.schemas.connector import ConnectorCreate, ConnectorRead
from app.services import connector_service

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("", response_model=list[ConnectorRead])
async def list_connectors(
    db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    return await connector_service.list_connectors(db, org.id)


@router.post("", response_model=ConnectorRead, status_code=status.HTTP_201_CREATED)
async def create_connector(
    data: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Architecture is prepared (see services/connector_service.py) but no
    connector type has a registered adapter yet — Phase 3 fills these in."""
    try:
        return await connector_service.create_connector(db, org.id, data)
    except NotImplementedError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.organization import Organization
from app.schemas.activity import ActivityEventRead
from app.services import activity_service

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityEventRead])
async def list_activity(
    search: str | None = None,
    event_type: str | None = None,
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    return await activity_service.list_activity(
        db, org.id, search=search, event_type=event_type, agent_id=agent_id
    )

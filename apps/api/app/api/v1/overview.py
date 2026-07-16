from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.agent import Agent
from app.models.enums import RecommendationStatus
from app.models.organization import Organization
from app.models.recommendation import Recommendation
from app.schemas.overview import OverviewSummary
from app.services import activity_service

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("/summary", response_model=OverviewSummary)
async def get_overview_summary(
    db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    agents_count = await db.scalar(
        select(func.count()).select_from(Agent).where(Agent.org_id == org.id)
    )
    total_cost = await db.scalar(
        select(func.coalesce(func.sum(Agent.monthly_cost_cents), 0)).where(Agent.org_id == org.id)
    )
    open_recs = await db.scalar(
        select(func.count())
        .select_from(Recommendation)
        .where(Recommendation.org_id == org.id, Recommendation.status == RecommendationStatus.OPEN)
    )
    risky_agents = await db.scalar(
        select(func.count())
        .select_from(Agent)
        .where(Agent.org_id == org.id, Agent.risk_level == "high")
    )
    recent_activity = await activity_service.list_activity(db, org.id, limit=10)

    return OverviewSummary(
        agents_found=agents_count or 0,
        monthly_cost_cents=total_cost or 0,
        open_risks=risky_agents or 0,
        optimization_opportunities=open_recs or 0,
        recent_activity=recent_activity,
    )

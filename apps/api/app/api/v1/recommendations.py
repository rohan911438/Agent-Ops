from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.enums import RecommendationStatus
from app.models.organization import Organization
from app.schemas.recommendation import RecommendationRead, RecommendationStatusUpdate
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationRead])
async def list_recommendations(
    status_filter: RecommendationStatus | None = None,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    return await recommendation_service.list_recommendations(db, org.id, status_filter)


@router.post("/refresh", response_model=list[RecommendationRead])
async def refresh_recommendations(
    db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    """Runs the rule-based engine now instead of waiting for a schedule."""
    return await recommendation_service.refresh_recommendations(db, org.id)


@router.patch("/{recommendation_id}", response_model=RecommendationRead)
async def update_recommendation_status(
    recommendation_id: str,
    data: RecommendationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    rec = await recommendation_service.get_recommendation(db, org.id, recommendation_id)
    if rec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation not found")
    return await recommendation_service.update_status(db, rec, data.status)

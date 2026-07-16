from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RecommendationStatus, RecommendationType


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    agent_id: str | None
    type: RecommendationType
    title: str
    description: str
    impact_estimate: str
    status: RecommendationStatus
    created_at: datetime


class RecommendationStatusUpdate(BaseModel):
    status: RecommendationStatus

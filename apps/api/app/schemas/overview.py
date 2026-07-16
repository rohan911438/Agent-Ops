from pydantic import BaseModel

from app.schemas.activity import ActivityEventRead


class OverviewSummary(BaseModel):
    agents_found: int
    monthly_cost_cents: int
    open_risks: int
    optimization_opportunities: int
    recent_activity: list[ActivityEventRead]

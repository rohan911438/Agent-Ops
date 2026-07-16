from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AgentFramework, AgentSource, AgentStatus, RiskLevel


class AgentBase(BaseModel):
    name: str
    framework: AgentFramework
    owner_user_id: str | None = None
    status: AgentStatus = AgentStatus.ACTIVE
    monthly_cost_cents: int = 0
    health_score: int = 100
    risk_level: RiskLevel = RiskLevel.LOW
    agent_metadata: dict = {}


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = None
    status: AgentStatus | None = None
    owner_user_id: str | None = None
    monthly_cost_cents: int | None = None
    health_score: int | None = None
    risk_level: RiskLevel | None = None
    agent_metadata: dict | None = None


class AgentRead(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    source: AgentSource
    created_at: datetime
    updated_at: datetime

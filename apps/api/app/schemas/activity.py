from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    agent_id: str | None
    actor: str
    event_type: str
    description: str
    event_metadata: dict
    tx_hash: str | None
    created_at: datetime

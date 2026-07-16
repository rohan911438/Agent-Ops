from pydantic import BaseModel, ConfigDict

from app.models.enums import ConnectorStatus, ConnectorType


class ConnectorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    type: ConnectorType
    status: ConnectorStatus
    config: dict


class ConnectorCreate(BaseModel):
    type: ConnectorType
    config: dict = {}

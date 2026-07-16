from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ScanSourceType, ScanStatus


class GitHubScanCreate(BaseModel):
    repo_url: str
    github_token: str | None = None


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    source_type: ScanSourceType
    source_label: str
    status: ScanStatus
    current_step: str | None
    agent_ids: list[str]
    summary: dict | None
    executive_report: dict | None
    optimization_plan: dict | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    # pending_payload is deliberately never exposed here — for a GitHub
    # scan it may hold a raw personal access token.

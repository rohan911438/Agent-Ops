from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.recommendation import RecommendationRead
from app.schemas.scan import ScanRead

ServiceName = Literal[
    "enterprise_health_scan",
    "executive_ai_audit",
    "ai_optimization_planner",
    "ai_infrastructure_assessment",
]


class ServiceInvokeRequest(BaseModel):
    """Input for POST /marketplace/invoke — the internal execution contract
    for all 4 services registered on-chain for ASP #6262 (see
    docs/ASP-6262-Service-Status.md). Exactly one data source must be
    given, matching the two the Health Scan UI already supports (see
    components/health-scan/data-source-picker.tsx): an inline agent
    manifest, or a GitHub repo to scan.
    """

    service: ServiceName
    agents: list[dict] | None = None
    repo_url: str | None = None
    github_token: str | None = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "ServiceInvokeRequest":
        provided = [self.agents is not None, self.repo_url is not None]
        if sum(provided) != 1:
            raise ValueError("Provide exactly one of `agents` or `repo_url`")
        return self


class ServiceInvokeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service: ServiceName
    scan_id: str
    status: str
    # The slice specific to whichever service was requested: a summary dict
    # for enterprise_health_scan, the report dict for executive_ai_audit,
    # the plan dict for ai_optimization_planner, or the recommendation list
    # for ai_infrastructure_assessment.
    result: dict | list[RecommendationRead]
    # The full underlying run, for transparency — every field this
    # invocation actually produced, not just the requested slice.
    scan: ScanRead

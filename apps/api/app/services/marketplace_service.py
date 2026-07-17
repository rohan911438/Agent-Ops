"""Internal service-invocation dispatch.

This is the execution contract a Task-Marketplace worker calls once it
accepts an inbound A2A request for one of ASP #6262's 4 registered
services (see docs/ASP-6262-Service-Status.md). It exists to close
docs/ASP-6262-Production-Readiness-Audit.md finding C-1: previously
nothing in this repository could be invoked programmatically at all — the
only entry point was a human clicking through the wallet-gated web UI.

What this DOES close: a real, authenticated (API key — see
app/api/deps.py / app/services/settings_service.py — not a wallet
session), documented, testable HTTP contract that runs the actual
pipeline (ingestion -> recommendation engine -> executive report ->
optimization plan, the same app/services/scan_service.py.run_scan every
Health Scan already runs) synchronously and returns the slice relevant to
whichever of the 4 services was requested.

What this does NOT close, and is explicitly outside this repo's boundary:
the on-chain Task Marketplace accept/negotiate/deliver loop itself (see
the okx-ai skill's references/task-asp.md). That requires a persistent
worker process running the onchainos CLI/daemon that watches for inbound
tasks addressed to this ASP's communicationAddress and calls this
endpoint when one arrives. That worker is infrastructure that lives
outside apps/api, not a gap in apps/api's own code — but this endpoint is
now the concrete, testable thing such a worker would call.
"""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_scan import HealthScan
from app.schemas.marketplace import ServiceInvokeRequest
from app.services import recommendation_service, scan_service
from app.services.scan.parsers import ScanParseError


class ServiceInvokeError(Exception):
    """Bad input (mirrors ScanParseError) or the pipeline itself ended in
    FAILED — either way the caller gets a clear message, not a raw 500."""


async def invoke_service(db: AsyncSession, org_id: str, data: ServiceInvokeRequest) -> dict:
    if data.agents is not None:
        content = json.dumps({"agents": data.agents})
        try:
            scan = await scan_service.create_upload_scan(
                db, org_id, "marketplace-invoke.json", content
            )
        except ScanParseError as exc:
            raise ServiceInvokeError(str(exc)) from exc
    else:
        try:
            scan = await scan_service.create_github_scan(
                db, org_id, data.repo_url, data.github_token
            )
        except ScanParseError as exc:
            raise ServiceInvokeError(str(exc)) from exc

    # Synchronous, not BackgroundTasks: an A2A invocation is a
    # request/response contract, not a poll-for-status one. run_scan's own
    # try/except (see scan_service.py) guarantees this always ends in
    # COMPLETED or FAILED — it never raises and never hangs indefinitely.
    #
    # run_scan commits via its OWN session (see scan_service.py's
    # docstring — it outlives the request in the normal BackgroundTasks
    # path), so `scan` — loaded in *this* session back in
    # create_upload_scan/create_github_scan above — is now stale relative
    # to what run_scan just committed. A plain re-query would silently
    # return the same already-identity-mapped, pre-run object instead of
    # picking up the cross-session commit (SQLAlchemy doesn't overwrite an
    # already-loaded instance's attributes from a subsequent plain
    # SELECT) — db.refresh() forces reloading this exact instance from
    # the database instead.
    await scan_service.run_scan(org_id, scan.id)
    await db.refresh(scan)

    if scan.status.value == "failed":
        raise ServiceInvokeError(scan.error_message or "The scan failed for an unknown reason.")

    result = await _slice_result(db, org_id, scan, data.service)
    return {"scan": scan, "result": result}


async def _slice_result(db: AsyncSession, org_id: str, scan: HealthScan, service: str):
    if service == "enterprise_health_scan":
        return {"summary": scan.summary, "agent_count": len(scan.agent_ids)}
    if service == "executive_ai_audit":
        return scan.executive_report or {}
    if service == "ai_optimization_planner":
        return scan.optimization_plan or {}
    # ai_infrastructure_assessment
    all_recs = await recommendation_service.list_recommendations(db, org_id)
    agent_id_set = set(scan.agent_ids)
    return [r for r in all_recs if r.agent_id in agent_id_set]

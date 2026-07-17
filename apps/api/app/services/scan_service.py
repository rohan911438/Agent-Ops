"""Health Scan orchestration: ingest agents from a source, run the
recommendation engine, synthesize an executive report.

run_scan is invoked via FastAPI's BackgroundTasks (see api/v1/scans.py) and
outlives the request that started it, so it opens its own DB session via
async_session_factory — the same idiom app/jobs/tasks.py already uses for
org-wide recommendation refreshes. It never depends on request-scoped auth.

Agent ingestion upserts against the scan's own agent_ids list (set on the
HealthScan row itself), not a blind insert — retrying a FAILED scan via
POST /scans/{id}/start again is always safe and never duplicates agents.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.models.agent import Agent
from app.models.agent_permission import AgentPermission
from app.models.enums import (
    AgentFramework,
    AgentSource,
    ConnectorType,
    RiskLevel,
    ScanSourceType,
    ScanStatus,
)
from app.models.health_scan import HealthScan
from app.models.recommendation import Recommendation
from app.models.user import User
from app.services.connector_service import ADAPTER_REGISTRY
from app.services.recommendation_service import refresh_recommendations
from app.services.scan.cost_estimator import estimate_monthly_cost_cents
from app.services.scan.optimization_plan_service import generate_optimization_plan
from app.services.scan.parsers import ScanParseError, parse_agent_definitions
from app.services.scan.report_service import generate_executive_report
from app.services.verification_service import submit_report_for_verification


class ScanAlreadyStartedError(Exception):
    """A scan can only be started once from PENDING — see start_scan."""


def _coerce_framework(value) -> AgentFramework:
    if isinstance(value, AgentFramework):
        return value
    try:
        return AgentFramework(str(value))
    except (ValueError, TypeError):
        return AgentFramework.CUSTOM


def _coerce_risk_level(value) -> RiskLevel:
    try:
        return RiskLevel(str(value).lower())
    except (ValueError, TypeError, AttributeError):
        return RiskLevel.LOW


async def create_upload_scan(db: AsyncSession, org_id: str, filename: str, content: str) -> HealthScan:
    raw_agents = parse_agent_definitions(content, filename)  # raises ScanParseError on bad input
    scan = HealthScan(
        org_id=org_id,
        source_type=ScanSourceType.FILE_UPLOAD,
        source_label=filename,
        status=ScanStatus.PENDING,
        pending_payload={"agents": raw_agents},
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


async def create_github_scan(
    db: AsyncSession, org_id: str, repo_url: str, github_token: str | None
) -> HealthScan:
    adapter_cls = ADAPTER_REGISTRY.get(ConnectorType.GITHUB)
    if adapter_cls is None:
        raise ScanParseError("GitHub scanning isn't available right now.")
    config = {"repo_url": repo_url, "github_token": github_token}
    try:
        reachable = await adapter_cls().test_connection(config)
    except Exception as exc:
        raise ScanParseError(f"Could not reach GitHub repo: {exc}") from exc
    if not reachable:
        raise ScanParseError(f'Could not access repo "{repo_url}" — check the URL and token.')

    scan = HealthScan(
        org_id=org_id,
        source_type=ScanSourceType.GITHUB,
        source_label=repo_url,
        status=ScanStatus.PENDING,
        pending_payload=config,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


async def get_scan(db: AsyncSession, org_id: str, scan_id: str) -> HealthScan | None:
    result = await db.execute(
        select(HealthScan).where(HealthScan.id == scan_id, HealthScan.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def list_scans(db: AsyncSession, org_id: str) -> list[HealthScan]:
    result = await db.execute(
        select(HealthScan).where(HealthScan.org_id == org_id).order_by(HealthScan.created_at.desc())
    )
    return list(result.scalars().all())


# In-flight statuses only — PENDING is a legitimate, possibly long-lived
# "created but not yet started" state and must never be swept.
_IN_FLIGHT_STATUSES = (ScanStatus.PARSING, ScanStatus.ANALYZING, ScanStatus.GENERATING_REPORT)
STALE_SCAN_THRESHOLD = timedelta(minutes=30)


async def sweep_stale_scans(db: AsyncSession) -> list[HealthScan]:
    """Marks scans still stuck in an in-flight status well past any
    realistic pipeline duration as FAILED with a clear error, instead of
    leaving them hanging forever — see docs/Roadmap.md's "Scan reliability
    without a queue broker" risk and docs/ASP-6262-Production-Readiness-
    Audit.md finding M-3. A scan only gets stuck like this if the process
    that was running its BackgroundTasks died mid-run (e.g. a restart);
    run_scan's own try/except already handles every in-process failure.

    Uses created_at, not an updated_at column (HealthScan has none — see
    app/models/base.py's TimestampMixin) — an approximation, but the
    pipeline normally completes in well under a minute (LLM calls now
    time out at 25s, GitHub adapter calls at 10s each), so the 30-minute
    threshold has wide margin before a merely-slow scan would be
    misclassified as stuck.
    """
    cutoff = datetime.now(timezone.utc) - STALE_SCAN_THRESHOLD
    result = await db.execute(
        select(HealthScan).where(
            HealthScan.status.in_(_IN_FLIGHT_STATUSES), HealthScan.created_at < cutoff
        )
    )
    stale = list(result.scalars().all())
    for scan in stale:
        scan.status = ScanStatus.FAILED
        scan.current_step = None
        scan.error_message = (
            "Scan was interrupted (likely a server restart) and did not complete. "
            "Start it again to retry."
        )
    if stale:
        await db.commit()
    return stale


_RESTARTABLE_STATUSES = (ScanStatus.PENDING, ScanStatus.FAILED)


async def start_scan(db: AsyncSession, scan: HealthScan, background_tasks) -> HealthScan:
    """PENDING is the normal first start; FAILED is also accepted so a scan
    that errored out (bad data, a transient chain/LLM issue, etc.) can be
    retried without re-uploading — see docs/ASP-6262-Production-Readiness-
    Audit.md finding M-1. Any other status means a scan is already running
    or already finished successfully, neither of which should be re-queued."""
    if scan.status not in _RESTARTABLE_STATUSES:
        raise ScanAlreadyStartedError(f"Scan is already {scan.status.value}")
    scan.status = ScanStatus.PARSING
    scan.current_step = "Queued"
    scan.error_message = None
    await db.commit()
    await db.refresh(scan)
    background_tasks.add_task(run_scan, scan.org_id, scan.id)
    return scan


async def _resolve_owner(db: AsyncSession, org_id: str, owner_email: str | None) -> str | None:
    if not owner_email:
        return None
    result = await db.execute(
        select(User).where(User.org_id == org_id, User.email.ilike(owner_email))
    )
    user = result.scalar_one_or_none()
    return user.id if user else None


async def _ingest_agents(
    db: AsyncSession, org_id: str, scan: HealthScan, raw_agents: list[dict]
) -> list[str]:
    existing_by_name: dict[str, Agent] = {}
    if scan.agent_ids:
        result = await db.execute(select(Agent).where(Agent.id.in_(scan.agent_ids)))
        existing_by_name = {a.name: a for a in result.scalars().all()}

    owner_cache: dict[str, str | None] = {}
    agent_ids: list[str] = []

    for raw in raw_agents:
        name = raw["name"]
        framework = _coerce_framework(raw.get("framework"))
        model = raw.get("model")
        cost = raw.get("monthly_cost_cents")
        if cost is None:
            cost = estimate_monthly_cost_cents(model)

        owner_email = raw.get("owner_email")
        if owner_email and owner_email not in owner_cache:
            owner_cache[owner_email] = await _resolve_owner(db, org_id, owner_email)
        owner_user_id = owner_cache.get(owner_email) if owner_email else None

        metadata = {
            "model": model,
            "scan_id": scan.id,
            "detected_via": raw.get("detected_via", "file_upload"),
            "needs_review": bool(raw.get("needs_review", False)),
        }
        if raw.get("source_file"):
            metadata["source_file"] = raw["source_file"]

        agent = existing_by_name.get(name)
        if agent:
            agent.framework = framework
            agent.monthly_cost_cents = cost
            agent.owner_user_id = owner_user_id
            agent.agent_metadata = metadata
        else:
            agent = Agent(
                org_id=org_id,
                name=name,
                framework=framework,
                owner_user_id=owner_user_id,
                monthly_cost_cents=cost,
                source=AgentSource.CONNECTOR,
                agent_metadata=metadata,
            )
            db.add(agent)
        await db.flush()
        agent_ids.append(agent.id)

        for perm in raw.get("permissions") or []:
            scope = perm.get("scope", "unknown")
            already = await db.execute(
                select(AgentPermission).where(
                    AgentPermission.agent_id == agent.id, AgentPermission.scope == scope
                )
            )
            if already.scalar_one_or_none():
                continue
            db.add(
                AgentPermission(
                    agent_id=agent.id,
                    scope=scope,
                    resource=perm.get("resource", "unknown"),
                    risk_level=_coerce_risk_level(perm.get("risk_level")),
                )
            )

    await db.commit()
    return agent_ids


def _build_summary(agents: list[Agent], recommendations: list[Recommendation]) -> dict:
    frameworks: dict[str, int] = defaultdict(int)
    models: dict[str, int] = defaultdict(int)
    for agent in agents:
        frameworks[agent.framework.value] += 1
        models[(agent.agent_metadata or {}).get("model") or "unspecified"] += 1

    rec_counts: dict[str, int] = defaultdict(int)
    for rec in recommendations:
        rec_counts[rec.type.value] += 1

    return {
        "agent_count": len(agents),
        "frameworks": dict(frameworks),
        "models": dict(models),
        "monthly_cost_cents": sum(a.monthly_cost_cents for a in agents),
        "duplicate_count": rec_counts.get("merge_duplicate", 0),
        "orphaned_count": rec_counts.get("orphaned_agent", 0),
        "high_risk_count": rec_counts.get("permission_risk", 0),
        "unused_count": rec_counts.get("unused_agent", 0),
        "model_downgrade_count": rec_counts.get("model_downgrade", 0),
    }


async def _fetch_raw_agents(scan: HealthScan) -> list[dict]:
    if scan.source_type == ScanSourceType.FILE_UPLOAD:
        return list(scan.pending_payload.get("agents", []))
    if scan.source_type == ScanSourceType.GITHUB:
        adapter_cls = ADAPTER_REGISTRY[ConnectorType.GITHUB]
        return await adapter_cls().sync_agents(scan.pending_payload)
    # LangGraph / CrewAI / OpenAI Agents SDK: no adapter registered yet —
    # the UI never lets these be selected (see data-source-picker.tsx),
    # this branch exists only as a safe default if reached some other way.
    return []


async def run_scan(org_id: str, scan_id: str) -> None:
    """Orchestrates the ASP pipeline end to end. The current_step messages
    below are a friendlier narration of the same real work this function
    has always done (discovery -> analysis -> reasoning -> optimization ->
    reporting) — no stage claims analysis that isn't actually happening;
    see docs/Architecture.md for the layer-to-module mapping.
    """
    async with database.async_session_factory() as db:
        scan = await get_scan(db, org_id, scan_id)
        if scan is None:
            return
        try:
            # --- Discovery: parse the source, ingest agents as real rows ---
            scan.current_step = "Discovering AI Assets"
            await db.commit()
            raw_agents = await _fetch_raw_agents(scan)
            agent_ids = await _ingest_agents(db, org_id, scan, raw_agents)
            scan.agent_ids = agent_ids
            await db.commit()

            agents_result = await db.execute(select(Agent).where(Agent.id.in_(agent_ids)))
            agents = list(agents_result.scalars().all())

            # --- Analysis: cost data was computed during ingestion above ---
            scan.status = ScanStatus.ANALYZING
            scan.current_step = "Evaluating Cost Efficiency"
            await db.commit()

            # --- Reasoning: the swappable rule engine (recommendation_service) ---
            scan.current_step = "Detecting Risks"
            await db.commit()
            await refresh_recommendations(db, org_id)
            recs_result = await db.execute(
                select(Recommendation).where(Recommendation.agent_id.in_(agent_ids))
            )
            recommendations = list(recs_result.scalars().all())

            scan.current_step = "Mapping Agent Relationships"
            await db.commit()
            summary = _build_summary(agents, recommendations)
            scan.summary = summary
            await db.commit()

            # --- Reporting ---
            scan.status = ScanStatus.GENERATING_REPORT
            scan.current_step = "Generating Executive Report"
            await db.commit()
            report = await generate_executive_report(agents, recommendations, summary)
            scan.executive_report = report
            await db.commit()

            # --- Trust layer: anchor the report's hash on Base. Never
            # blocks the scan — see app/services/verification_service.py. ---
            await submit_report_for_verification(db, org_id, scan)

            # --- Optimization: dedicated implementation plan ---
            scan.current_step = "Building Optimization Plan"
            await db.commit()
            optimization_plan = await generate_optimization_plan(recommendations, report)
            scan.optimization_plan = optimization_plan

            scan.status = ScanStatus.COMPLETED
            scan.current_step = None
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as exc:  # noqa: BLE001 — a scan must never hang mid-status
            scan.status = ScanStatus.FAILED
            scan.error_message = str(exc)
            scan.current_step = None
            await db.commit()

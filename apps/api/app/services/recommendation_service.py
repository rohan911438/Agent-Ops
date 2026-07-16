"""Rule-based recommendation engine.

This is intentionally NOT machine learning for the MVP — see
docs/TechnicalDecisions.md. It scans an org's agents and activity with a
handful of explicit, explainable rules and writes Recommendation rows.
Swapping in a learned model later only touches this module.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_event import ActivityEvent
from app.models.agent import Agent
from app.models.agent_permission import AgentPermission
from app.models.enums import RecommendationStatus, RecommendationType, RiskLevel
from app.models.recommendation import Recommendation

UNUSED_THRESHOLD_DAYS = 30
HIGH_COST_CENTS_THRESHOLD = 20000  # $200/mo


async def list_recommendations(
    db: AsyncSession, org_id: str, status: RecommendationStatus | None = None
) -> list[Recommendation]:
    stmt = select(Recommendation).where(Recommendation.org_id == org_id)
    if status:
        stmt = stmt.where(Recommendation.status == status)
    stmt = stmt.order_by(Recommendation.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_recommendation(
    db: AsyncSession, org_id: str, recommendation_id: str
) -> Recommendation | None:
    result = await db.execute(
        select(Recommendation).where(
            Recommendation.id == recommendation_id, Recommendation.org_id == org_id
        )
    )
    return result.scalar_one_or_none()


async def update_status(
    db: AsyncSession, recommendation: Recommendation, status: RecommendationStatus
) -> Recommendation:
    recommendation.status = status
    await db.commit()
    await db.refresh(recommendation)
    return recommendation


async def refresh_recommendations(db: AsyncSession, org_id: str) -> list[Recommendation]:
    """Runs the rule set for an org and persists any new findings.

    Called synchronously from the seed script and from the manual
    /recommendations/refresh endpoint. A Celery beat schedule can call the
    same function on an interval once a broker is introduced (Phase 3+).
    """
    agents_result = await db.execute(select(Agent).where(Agent.org_id == org_id))
    agents = list(agents_result.scalars().all())

    created: list[Recommendation] = []
    created += await _rule_unused_agents(db, org_id, agents)
    created += await _rule_high_cost_agents(db, org_id, agents)
    created += await _rule_duplicate_agents(db, org_id, agents)
    created += await _rule_permission_risks(db, org_id, agents)
    return created


async def _has_open_recommendation(db: AsyncSession, org_id: str, agent_id: str, type_: RecommendationType) -> bool:
    result = await db.execute(
        select(Recommendation).where(
            Recommendation.org_id == org_id,
            Recommendation.agent_id == agent_id,
            Recommendation.type == type_,
            Recommendation.status == RecommendationStatus.OPEN,
        )
    )
    return result.scalar_one_or_none() is not None


async def _rule_unused_agents(
    db: AsyncSession, org_id: str, agents: list[Agent]
) -> list[Recommendation]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=UNUSED_THRESHOLD_DAYS)
    created = []
    for agent in agents:
        last_event = await db.execute(
            select(ActivityEvent)
            .where(ActivityEvent.agent_id == agent.id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(1)
        )
        event = last_event.scalar_one_or_none()
        # SQLite (aiosqlite) returns naive datetimes even for tz-aware
        # columns; everything we write is UTC, so treat naive as UTC.
        event_created_at = (
            event.created_at.replace(tzinfo=timezone.utc)
            if event and event.created_at.tzinfo is None
            else event.created_at if event else None
        )
        is_unused = event is None or event_created_at < cutoff
        if is_unused and not await _has_open_recommendation(
            db, org_id, agent.id, RecommendationType.UNUSED_AGENT
        ):
            rec = Recommendation(
                org_id=org_id,
                agent_id=agent.id,
                type=RecommendationType.UNUSED_AGENT,
                title=f'"{agent.name}" has had no activity in {UNUSED_THRESHOLD_DAYS}+ days',
                description=(
                    f'Agent "{agent.name}" ({agent.framework.value}) has no recorded activity '
                    f"in the last {UNUSED_THRESHOLD_DAYS} days. Consider archiving it to stop "
                    "paying for idle infrastructure."
                ),
                impact_estimate=f"${agent.monthly_cost_cents / 100:.0f}/mo reclaimable",
            )
            db.add(rec)
            created.append(rec)
    if created:
        await db.commit()
    return created


async def _rule_high_cost_agents(
    db: AsyncSession, org_id: str, agents: list[Agent]
) -> list[Recommendation]:
    created = []
    for agent in agents:
        if agent.monthly_cost_cents >= HIGH_COST_CENTS_THRESHOLD and not await _has_open_recommendation(
            db, org_id, agent.id, RecommendationType.REDUCE_COST
        ):
            rec = Recommendation(
                org_id=org_id,
                agent_id=agent.id,
                type=RecommendationType.REDUCE_COST,
                title=f'"{agent.name}" is a top cost driver',
                description=(
                    f'"{agent.name}" costs ${agent.monthly_cost_cents / 100:.0f}/mo. Review its '
                    "model choice and prompt/context size — smaller models or caching often cut "
                    "cost significantly with minimal quality loss."
                ),
                impact_estimate=f"up to 30% of ${agent.monthly_cost_cents / 100:.0f}/mo",
            )
            db.add(rec)
            created.append(rec)
    if created:
        await db.commit()
    return created


async def _rule_duplicate_agents(
    db: AsyncSession, org_id: str, agents: list[Agent]
) -> list[Recommendation]:
    groups: dict[tuple, list[Agent]] = defaultdict(list)
    for agent in agents:
        groups[(agent.framework, agent.name.split()[0].lower() if agent.name else "")].append(agent)

    created = []
    for (_, key), group in groups.items():
        if len(group) < 2 or not key:
            continue
        primary = group[0]
        if await _has_open_recommendation(db, org_id, primary.id, RecommendationType.MERGE_DUPLICATE):
            continue
        names = ", ".join(f'"{a.name}"' for a in group)
        rec = Recommendation(
            org_id=org_id,
            agent_id=primary.id,
            type=RecommendationType.MERGE_DUPLICATE,
            title=f"{len(group)} agents look like duplicates",
            description=(
                f"{names} share the same framework and a similar name — likely the same "
                "capability built more than once. Merging reduces maintenance and cost overlap."
            ),
            impact_estimate=f"consolidate {len(group)} agents into 1",
        )
        db.add(rec)
        created.append(rec)
    if created:
        await db.commit()
    return created


async def _rule_permission_risks(
    db: AsyncSession, org_id: str, agents: list[Agent]
) -> list[Recommendation]:
    created = []
    for agent in agents:
        perms_result = await db.execute(
            select(AgentPermission).where(
                AgentPermission.agent_id == agent.id, AgentPermission.risk_level == RiskLevel.HIGH
            )
        )
        high_risk_perms = list(perms_result.scalars().all())
        if high_risk_perms and not await _has_open_recommendation(
            db, org_id, agent.id, RecommendationType.PERMISSION_RISK
        ):
            scopes = ", ".join(p.scope for p in high_risk_perms)
            rec = Recommendation(
                org_id=org_id,
                agent_id=agent.id,
                type=RecommendationType.PERMISSION_RISK,
                title=f'"{agent.name}" holds high-risk permissions',
                description=(
                    f'"{agent.name}" has high-risk scopes ({scopes}) that exceed what its '
                    "observed activity requires. Review and scope down to least privilege."
                ),
                impact_estimate=f"{len(high_risk_perms)} high-risk scope(s)",
            )
            db.add(rec)
            created.append(rec)
    if created:
        await db.commit()
    return created

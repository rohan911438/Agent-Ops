from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_event import ActivityEvent


async def list_activity(
    db: AsyncSession,
    org_id: str,
    search: str | None = None,
    event_type: str | None = None,
    agent_id: str | None = None,
    limit: int = 100,
) -> list[ActivityEvent]:
    stmt = select(ActivityEvent).where(ActivityEvent.org_id == org_id)

    if event_type:
        stmt = stmt.where(ActivityEvent.event_type == event_type)
    if agent_id:
        stmt = stmt.where(ActivityEvent.agent_id == agent_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(ActivityEvent.description.ilike(like), ActivityEvent.actor.ilike(like))
        )

    stmt = stmt.order_by(ActivityEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def record_event(
    db: AsyncSession,
    org_id: str,
    actor: str,
    event_type: str,
    description: str,
    agent_id: str | None = None,
    event_metadata: dict | None = None,
    tx_hash: str | None = None,
) -> ActivityEvent:
    event = ActivityEvent(
        org_id=org_id,
        agent_id=agent_id,
        actor=actor,
        event_type=event_type,
        description=description,
        event_metadata=event_metadata or {},
        tx_hash=tx_hash,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

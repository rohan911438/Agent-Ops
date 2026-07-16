"""Background job entry points.

The MVP has no queue broker running (no Docker, no Redis — see
docs/TechnicalDecisions.md), so these are plain async functions invoked
directly by the seed script or the /recommendations/refresh endpoint.

When real connector syncs land (Phase 3+) and jobs need to run on a
schedule across many orgs, wrap these same functions as Celery tasks with
Redis as the broker — the function bodies do not need to change, only the
invocation (Celery beat instead of a script/manual call).
"""

from sqlalchemy import select

from app.database import async_session_factory
from app.models.organization import Organization
from app.services.recommendation_service import refresh_recommendations


async def run_recommendation_refresh_all_orgs() -> int:
    total = 0
    async with async_session_factory() as db:
        result = await db.execute(select(Organization))
        for org in result.scalars().all():
            created = await refresh_recommendations(db, org.id)
            total += len(created)
    return total

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import AuthedIdentity, get_current_identity
from app.database import get_db
from app.models.organization import Organization

DbSession = AsyncSession


async def get_current_org(
    identity: AuthedIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Resolves the caller's org from their Clerk identity.

    In local dev (auth disabled) this transparently falls back to a single
    seeded "dev-org" organization — see scripts/seed_db.py.
    """
    stmt = select(Organization).where(
        Organization.clerk_org_id == identity.clerk_org_id
        if identity.clerk_org_id != "dev-org"
        else Organization.slug == "dev-org"
    )
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return org

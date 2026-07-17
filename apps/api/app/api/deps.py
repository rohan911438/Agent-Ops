from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import SESSION_COOKIE_NAME, verify_session_token
from app.config import get_settings
from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.services.settings_service import API_KEY_PREFIX, verify_api_key

DbSession = AsyncSession


@dataclass
class AuthedIdentity:
    # None for an API-key caller — a machine/agent caller isn't any one
    # workspace human. Routes that need an actual User (get_current_user)
    # simply don't resolve for that case; routes that only need org scope
    # (e.g. app/api/v1/marketplace.py) work fine with user_id=None.
    user_id: str | None
    org_id: str
    auth_method: str = "session"  # "session" | "api_key"


async def get_current_identity(
    request: Request, db: AsyncSession = Depends(get_db)
) -> AuthedIdentity:
    """Resolves who's calling from either the session cookie set by
    POST /auth/wallet/verify (see app/auth/session.py) — a human — or an
    `Authorization: Bearer aoc_...` API key (see settings_service.
    verify_api_key) — a machine/agent caller, e.g. a Task-Marketplace
    worker invoking app/api/v1/marketplace.py. Falls back to a fixed
    seeded dev identity when AUTH_DISABLED=true — the same zero-config
    local dev experience the Clerk-based auth used to provide when its env
    vars were unset.
    """
    settings = get_settings()
    if settings.auth_disabled:
        return AuthedIdentity(user_id="dev-user", org_id="dev-org")

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    if token.startswith(API_KEY_PREFIX):
        api_key = await verify_api_key(db, token)
        if api_key is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
        return AuthedIdentity(user_id=None, org_id=api_key.org_id, auth_method="api_key")

    claims = verify_session_token(token)
    if claims is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return AuthedIdentity(user_id=claims.user_id, org_id=claims.org_id)


async def get_current_org(
    identity: AuthedIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    stmt = select(Organization).where(
        Organization.slug == "dev-org"
        if identity.org_id == "dev-org"
        else Organization.id == identity.org_id
    )
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return org


async def get_current_user(
    identity: AuthedIdentity = Depends(get_current_identity),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> User:
    if identity.user_id == "dev-user":
        stmt = select(User).where(User.org_id == org.id).order_by(User.created_at)
    else:
        stmt = select(User).where(User.id == identity.user_id, User.org_id == org.id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user

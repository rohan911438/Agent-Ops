"""Clerk JWT verification via JWKS.

No session table on the API side — Clerk is the source of truth for
identity, this module only verifies the bearer token on each request.
When CLERK_JWKS_URL / CLERK_ISSUER are unset (local dev), verification
is skipped and a fixed dev identity is returned instead, so the API is
runnable without a live Clerk project.
"""

from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request, status
from jose import jwt

from app.config import get_settings

settings = get_settings()

_jwks_cache: dict | None = None


@dataclass
class AuthedIdentity:
    clerk_user_id: str
    clerk_org_id: str | None
    email: str | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(settings.clerk_jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def get_current_identity(request: Request) -> AuthedIdentity:
    if not settings.auth_enabled:
        return AuthedIdentity(clerk_user_id="dev-user", clerk_org_id="dev-org")

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ")

    try:
        jwks = await _get_jwks()
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},
        )
    except Exception as exc:  # jose raises several distinct error types
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc

    return AuthedIdentity(
        clerk_user_id=claims["sub"],
        clerk_org_id=claims.get("org_id"),
        email=claims.get("email"),
    )

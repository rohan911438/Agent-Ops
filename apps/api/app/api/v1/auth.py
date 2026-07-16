"""Wallet-first authentication routes.

This is the only concrete provider wired in today (see
app/auth/providers/wallet.py). Everything past `verify_and_login` —
session issuance, the cookie, get_current_org/get_current_user — is
provider-agnostic; a future Google/Microsoft/GitHub/Okta/SAML provider adds
a sibling route here and calls the same session helpers, nothing else in
the API changes.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user
from app.auth.providers.wallet import WalletAuthError
from app.auth.providers.wallet import create_challenge as create_wallet_challenge
from app.auth.providers.wallet import verify_and_login as verify_wallet_login
from app.auth.session import SESSION_COOKIE_NAME, issue_session_token
from app.config import get_settings
from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    SessionOrganization,
    SessionRead,
    SessionUser,
    WalletNonceRequest,
    WalletNonceResponse,
    WalletVerifyRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_cookie_kwargs() -> dict:
    settings = get_settings()
    return dict(
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
        path="/",
        max_age=settings.session_ttl_seconds,
    )


@router.post("/wallet/nonce", response_model=WalletNonceResponse)
async def wallet_nonce(data: WalletNonceRequest, db: AsyncSession = Depends(get_db)):
    nonce, message = await create_wallet_challenge(db, data.address)
    return WalletNonceResponse(nonce=nonce, message=message)


@router.post("/wallet/verify", response_model=SessionRead)
async def wallet_verify(
    data: WalletVerifyRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    try:
        result = await verify_wallet_login(db, data.address, data.signature, data.nonce)
    except WalletAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    token = issue_session_token(result.user_id, result.org_id)
    response.set_cookie(SESSION_COOKIE_NAME, token, **_session_cookie_kwargs())

    user = await db.get(User, result.user_id)
    org = await db.get(Organization, result.org_id)
    return SessionRead(
        user=SessionUser.model_validate(user),
        organization=SessionOrganization.model_validate(org),
        created=result.created,
    )


@router.get("/session", response_model=SessionRead)
async def get_session(
    user: User = Depends(get_current_user), org: Organization = Depends(get_current_org)
):
    return SessionRead(
        user=SessionUser.model_validate(user),
        organization=SessionOrganization.model_validate(org),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")

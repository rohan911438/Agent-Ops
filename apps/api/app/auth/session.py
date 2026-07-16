"""Session issuance/verification for the workspace auth cookie.

Provider-agnostic on purpose: whatever authenticated the user (today only
app/auth/providers/wallet.py — Google/Microsoft/GitHub/Okta/SAML are
reserved future providers), the result is the same small WorkspaceAuthResult,
and this module is the only thing that turns that into a session. Nothing
downstream of here (deps.py, any router) ever branches on which provider
was used.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings

SESSION_COOKIE_NAME = "agentops_session"
_ALGORITHM = "HS256"


@dataclass
class WorkspaceAuthResult:
    """What every auth provider produces, regardless of how it got there."""

    user_id: str
    org_id: str
    created: bool


@dataclass
class SessionClaims:
    user_id: str
    org_id: str


def issue_session_token(user_id: str, org_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "iat": now,
        "exp": now + timedelta(seconds=settings.session_ttl_seconds),
    }
    return jwt.encode(payload, settings.session_secret_key, algorithm=_ALGORITHM)


def verify_session_token(token: str) -> SessionClaims | None:
    settings = get_settings()
    try:
        claims = jwt.decode(token, settings.session_secret_key, algorithms=[_ALGORITHM])
    except JWTError:
        return None
    org_id = claims.get("org_id")
    user_id = claims.get("sub")
    if not user_id or not org_id:
        return None
    return SessionClaims(user_id=user_id, org_id=org_id)

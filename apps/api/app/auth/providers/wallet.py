"""OKX Wallet (EVM) authentication provider: challenge issuance + signature
verification. The only auth provider implemented today — see
app/models/enums.py:AuthProviderType for the other reserved slots and
docs/Architecture.md for how a future provider plugs in without touching
app/auth/session.py, app/api/deps.py, or any router.

Never authenticates on the address alone: a wallet must sign the exact nonce
this module issued, and the recovered signer must match the claimed address.
"""

import secrets
from datetime import datetime, timedelta, timezone

from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import WorkspaceAuthResult
from app.models.auth_challenge import AuthChallenge
from app.models.enums import AuthProviderType, UserRole, WalletChain
from app.models.organization import Organization
from app.models.user import User
from app.models.wallet import Wallet

CHALLENGE_TTL_SECONDS = 5 * 60


class WalletAuthError(Exception):
    """Any invalid connect/challenge/signature condition — routes to 401."""


def _normalize_address(address: str) -> str:
    return address.strip().lower()


def _short_address(address: str) -> str:
    return f"{address[:6]}…{address[-4:]}" if len(address) > 10 else address


def _build_message(address: str, nonce: str, issued_at: datetime) -> str:
    return (
        "AgentOps Cloud wants you to sign in with your wallet.\n\n"
        f"Address: {address}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at.isoformat()}\n\n"
        "This request will not trigger a blockchain transaction or cost any gas."
    )


async def create_challenge(db: AsyncSession, address: str) -> tuple[str, str]:
    """Returns (nonce, message) — message is what the wallet should sign."""
    address = _normalize_address(address)
    nonce = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    message = _build_message(address, nonce, now)

    db.add(
        AuthChallenge(
            wallet_address=address,
            nonce=nonce,
            message=message,
            expires_at=now + timedelta(seconds=CHALLENGE_TTL_SECONDS),
        )
    )
    await db.commit()
    return nonce, message


async def _find_or_create_workspace(db: AsyncSession, address: str) -> tuple[User, bool]:
    result = await db.execute(select(User).where(User.wallet_address == address))
    user = result.scalar_one_or_none()
    if user is not None:
        return user, False

    org = Organization(
        name=f"Workspace {_short_address(address)}",
        slug=f"wallet-{address[2:10]}" if address.startswith("0x") else f"wallet-{address[:8]}",
    )
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        wallet_address=address,
        auth_provider=AuthProviderType.WALLET,
        email=f"{address}@wallet.local",
        name=_short_address(address),
        role=UserRole.OWNER,
    )
    db.add(user)
    await db.flush()
    return user, True


async def _upsert_connected_wallet(db: AsyncSession, org_id: str, address: str, now: datetime) -> None:
    result = await db.execute(select(Wallet).where(Wallet.org_id == org_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        db.add(Wallet(org_id=org_id, chain=WalletChain.BASE, address=address, last_verified_at=now))
    else:
        wallet.address = address
        wallet.last_verified_at = now


async def verify_and_login(
    db: AsyncSession, address: str, signature: str, nonce: str
) -> WorkspaceAuthResult:
    address = _normalize_address(address)

    result = await db.execute(select(AuthChallenge).where(AuthChallenge.nonce == nonce))
    challenge = result.scalar_one_or_none()
    if challenge is None or challenge.wallet_address != address:
        raise WalletAuthError("Unknown or mismatched login challenge.")
    if challenge.consumed_at is not None:
        raise WalletAuthError("This login challenge has already been used.")
    # SQLite (aiosqlite) returns naive datetimes even for tz-aware columns;
    # everything we write is UTC, so treat naive as UTC (see scan_service.py
    # for the same pattern).
    expires_at = (
        challenge.expires_at.replace(tzinfo=timezone.utc)
        if challenge.expires_at.tzinfo is None
        else challenge.expires_at
    )
    if expires_at < datetime.now(timezone.utc):
        raise WalletAuthError("This login challenge has expired — request a new one.")

    try:
        recovered = Account.recover_message(encode_defunct(text=challenge.message), signature=signature)
    except Exception as exc:  # eth_account raises several distinct error types
        raise WalletAuthError("Could not verify the wallet signature.") from exc

    if _normalize_address(recovered) != address:
        raise WalletAuthError("Signature does not match the claimed wallet address.")

    challenge.consumed_at = datetime.now(timezone.utc)

    user, created = await _find_or_create_workspace(db, address)
    now = datetime.now(timezone.utc)
    user.last_login_at = now
    await _upsert_connected_wallet(db, user.org_id, address, now)

    await db.commit()
    return WorkspaceAuthResult(user_id=user.id, org_id=user.org_id, created=created)

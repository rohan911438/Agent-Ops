import hashlib
import secrets

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.organization import Organization
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.settings import ApiKeyCreate, UserInvite, UserRoleUpdate, WalletConnect, WorkspaceUpdate


async def update_workspace(db: AsyncSession, org: Organization, data: WorkspaceUpdate) -> Organization:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    await db.commit()
    await db.refresh(org)
    return org


async def list_users(db: AsyncSession, org_id: str) -> list[User]:
    result = await db.execute(select(User).where(User.org_id == org_id).order_by(User.name))
    return list(result.scalars().all())


async def invite_user(db: AsyncSession, org_id: str, data: UserInvite) -> User:
    user = User(org_id=org_id, email=data.email, name=data.name, role=data.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_role(db: AsyncSession, user: User, data: UserRoleUpdate) -> User:
    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user


async def remove_user(db: AsyncSession, user: User) -> None:
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()


async def list_api_keys(db: AsyncSession, org_id: str) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).where(ApiKey.org_id == org_id).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())


def _generate_key() -> tuple[str, str, str]:
    """Returns (full_key, key_hash, key_prefix). Only the hash is persisted."""
    raw = secrets.token_urlsafe(32)
    full_key = f"aoc_{raw}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_hash, full_key[:12]


async def create_api_key(db: AsyncSession, org_id: str, data: ApiKeyCreate, created_by: str | None) -> tuple[ApiKey, str]:
    full_key, key_hash, key_prefix = _generate_key()
    api_key = ApiKey(org_id=org_id, name=data.name, key_hash=key_hash, key_prefix=key_prefix, created_by=created_by)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, full_key


async def revoke_api_key(db: AsyncSession, api_key: ApiKey) -> None:
    await db.execute(delete(ApiKey).where(ApiKey.id == api_key.id))
    await db.commit()


async def get_wallet(db: AsyncSession, org_id: str) -> Wallet | None:
    result = await db.execute(select(Wallet).where(Wallet.org_id == org_id))
    return result.scalar_one_or_none()


async def connect_wallet(db: AsyncSession, org_id: str, data: WalletConnect) -> Wallet:
    existing = await get_wallet(db, org_id)
    if existing:
        existing.address = data.address
        existing.chain = data.chain
        await db.commit()
        await db.refresh(existing)
        return existing
    wallet = Wallet(org_id=org_id, chain=data.chain, address=data.address)
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)
    return wallet

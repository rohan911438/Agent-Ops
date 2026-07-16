from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole, WalletChain


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: UserRole
    created_at: datetime


class UserInvite(BaseModel):
    email: str
    name: str
    role: UserRole = UserRole.MEMBER


class UserRoleUpdate(BaseModel):
    role: UserRole


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    key_prefix: str
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyCreated(ApiKeyRead):
    """Returned exactly once, at creation time — the full key is never stored."""

    key: str


class WalletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chain: WalletChain
    address: str
    created_at: datetime


class WalletConnect(BaseModel):
    chain: WalletChain = WalletChain.BASE
    address: str

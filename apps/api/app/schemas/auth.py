from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AuthProviderType, UserRole


class WalletNonceRequest(BaseModel):
    address: str


class WalletNonceResponse(BaseModel):
    nonce: str
    message: str


class WalletVerifyRequest(BaseModel):
    address: str
    signature: str
    nonce: str


class SessionUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    wallet_address: str | None
    auth_provider: AuthProviderType
    email: str
    name: str
    role: UserRole
    last_login_at: datetime | None
    created_at: datetime


class SessionOrganization(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str


class SessionRead(BaseModel):
    user: SessionUser
    organization: SessionOrganization
    created: bool = False

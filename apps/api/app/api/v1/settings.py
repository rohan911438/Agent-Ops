from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.organization import Organization
from app.models.user import User
from app.schemas.settings import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    UserInvite,
    UserRead,
    UserRoleUpdate,
    WalletConnect,
    WalletRead,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


# --- Workspace ---


@router.get("/workspace", response_model=WorkspaceRead)
async def get_workspace(org: Organization = Depends(get_current_org)):
    return org


@router.patch("/workspace", response_model=WorkspaceRead)
async def update_workspace(
    data: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    return await settings_service.update_workspace(db, org, data)


# --- Users ---


@router.get("/users", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)):
    return await settings_service.list_users(db, org.id)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: UserInvite, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    return await settings_service.invite_user(db, org.id, data)


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user_role(
    user_id: str,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    result = await db.execute(select(User).where(User.id == user_id, User.org_id == org.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return await settings_service.update_user_role(db, user, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: str, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    result = await db.execute(select(User).where(User.id == user_id, User.org_id == org.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await settings_service.remove_user(db, user)


# --- API Keys ---


@router.get("/api-keys", response_model=list[ApiKeyRead])
async def list_api_keys(db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)):
    return await settings_service.list_api_keys(db, org.id)


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    api_key, full_key = await settings_service.create_api_key(db, org.id, data, created_by=None)
    return ApiKeyCreated(**ApiKeyRead.model_validate(api_key).model_dump(), key=full_key)


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org.id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    await settings_service.revoke_api_key(db, api_key)


# --- Wallet ---


@router.get("/wallet", response_model=WalletRead | None)
async def get_wallet(db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)):
    return await settings_service.get_wallet(db, org.id)


@router.post("/wallet", response_model=WalletRead)
async def connect_wallet(
    data: WalletConnect, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    return await settings_service.connect_wallet(db, org.id, data)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.organization import Organization
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
async def list_agents(
    db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    return await agent_service.list_agents(db, org.id)


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    return await agent_service.create_agent(db, org.id, data)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: str, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    agent = await agent_service.get_agent(db, org.id, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    agent = await agent_service.get_agent(db, org.id, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return await agent_service.update_agent(db, agent, data)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    agent = await agent_service.get_agent(db, org.id, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    await agent_service.delete_agent(db, agent)

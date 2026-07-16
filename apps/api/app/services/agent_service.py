from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


async def list_agents(db: AsyncSession, org_id: str) -> list[Agent]:
    result = await db.execute(select(Agent).where(Agent.org_id == org_id).order_by(Agent.name))
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, org_id: str, agent_id: str) -> Agent | None:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def create_agent(db: AsyncSession, org_id: str, data: AgentCreate) -> Agent:
    agent = Agent(org_id=org_id, **data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def update_agent(db: AsyncSession, agent: Agent, data: AgentUpdate) -> Agent:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return agent


async def delete_agent(db: AsyncSession, agent: Agent) -> None:
    await db.execute(delete(Agent).where(Agent.id == agent.id))
    await db.commit()

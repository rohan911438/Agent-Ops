"""Seeds the local SQLite database with a realistic dev-org.

Run after `alembic upgrade head`:

    cd apps/api
    .venv/Scripts/python ../../scripts/seed_db.py     (Windows)
    .venv/bin/python ../../scripts/seed_db.py          (macOS/Linux)

Everything here goes through the same service layer real connectors will
use later (see app/services/agent_service.py, activity_service.py) — the
seed path is not architecturally different from a real sync, just driven
by a script instead of a connector.
"""

import asyncio
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select  # noqa: E402

from app.database import async_session_factory  # noqa: E402
from app.models.agent import Agent  # noqa: E402
from app.models.agent_permission import AgentPermission  # noqa: E402
from app.models.enums import (  # noqa: E402
    AgentFramework,
    AgentSource,
    AgentStatus,
    RiskLevel,
    UserRole,
)
from app.models.organization import Organization  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.activity_service import record_event  # noqa: E402
from app.services.recommendation_service import refresh_recommendations  # noqa: E402

AGENTS = [
    dict(name="Support Triage Bot", framework=AgentFramework.OPENAI_AGENTS, cost=4200, health=92, risk=RiskLevel.LOW),
    dict(name="Support Triage Bot v2", framework=AgentFramework.OPENAI_AGENTS, cost=3800, health=88, risk=RiskLevel.LOW),
    dict(name="Sales Research Agent", framework=AgentFramework.LANGGRAPH, cost=26000, health=75, risk=RiskLevel.MEDIUM),
    dict(name="Code Review Crew", framework=AgentFramework.CREWAI, cost=9100, health=95, risk=RiskLevel.LOW),
    dict(name="Legacy Data Sync", framework=AgentFramework.CUSTOM, cost=1500, health=40, risk=RiskLevel.HIGH),
    dict(name="Internal Docs MCP", framework=AgentFramework.MCP, cost=600, health=99, risk=RiskLevel.LOW),
    dict(name="Marketing Autogen Swarm", framework=AgentFramework.AUTOGEN, cost=31000, health=60, risk=RiskLevel.MEDIUM),
    dict(name="Invoice Automation", framework=AgentFramework.N8N, cost=200, health=100, risk=RiskLevel.LOW),
]


async def main() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(Organization).where(Organization.slug == "dev-org"))
        org = result.scalar_one_or_none()
        if org is None:
            org = Organization(name="Dev Org", slug="dev-org")
            db.add(org)
            await db.commit()
            await db.refresh(org)
            print(f"Created organization: {org.name} ({org.id})")
        else:
            print(f"Organization already exists: {org.name} ({org.id})")

        result = await db.execute(select(User).where(User.org_id == org.id))
        owner = result.scalars().first()
        if owner is None:
            owner = User(org_id=org.id, email="owner@dev-org.test", name="Dana Owner", role=UserRole.OWNER)
            db.add(owner)
            await db.commit()
            await db.refresh(owner)
            print(f"Created user: {owner.name}")

        result = await db.execute(select(Agent).where(Agent.org_id == org.id))
        existing_agents = result.scalars().all()
        if existing_agents:
            print(f"{len(existing_agents)} agents already exist, skipping agent seed.")
            agents = existing_agents
        else:
            agents = []
            for spec in AGENTS:
                agent = Agent(
                    org_id=org.id,
                    name=spec["name"],
                    framework=spec["framework"],
                    owner_user_id=owner.id,
                    status=AgentStatus.ACTIVE,
                    monthly_cost_cents=spec["cost"],
                    health_score=spec["health"],
                    risk_level=spec["risk"],
                    source=AgentSource.MANUAL,
                )
                db.add(agent)
                agents.append(agent)
            await db.commit()
            for agent in agents:
                await db.refresh(agent)
            print(f"Created {len(agents)} agents.")

            # Give the risky legacy agent a high-risk permission so the
            # permission_risk recommendation rule has something to find.
            legacy = next(a for a in agents if a.name == "Legacy Data Sync")
            db.add(AgentPermission(agent_id=legacy.id, scope="database:write", resource="customers_db", risk_level=RiskLevel.HIGH))
            await db.commit()

            # Recent activity for most agents; deliberately omit it for the
            # two Support Triage Bot variants so the "unused" and
            # "duplicate" recommendation rules both have something to find.
            for agent in agents:
                if "Support Triage" in agent.name:
                    continue
                await record_event(
                    db, org.id, actor=owner.name, event_type="agent.run",
                    description=f'ran "{agent.name}"', agent_id=agent.id,
                )

        created = await refresh_recommendations(db, org.id)
        print(f"Recommendation engine created {len(created)} recommendation(s).")


if __name__ == "__main__":
    asyncio.run(main())

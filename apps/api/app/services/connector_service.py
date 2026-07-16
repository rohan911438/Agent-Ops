"""Connector architecture, Phase 3+.

Defines the adapter interface every future integration (GitHub, LangGraph,
CrewAI, MCP, Kubernetes, cloud providers, ...) will implement. No adapter
is registered in the MVP — connect_connector always raises NotImplemented
so the API surface is real without faking a live integration.
"""

from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Connector
from app.models.enums import ConnectorType
from app.schemas.connector import ConnectorCreate


class ConnectorAdapter(ABC):
    """One subclass per integration type, registered in ADAPTER_REGISTRY."""

    type: ConnectorType

    @abstractmethod
    async def test_connection(self, config: dict) -> bool: ...

    @abstractmethod
    async def sync_agents(self, config: dict) -> list[dict]:
        """Returns raw agent records to be upserted by the caller."""


ADAPTER_REGISTRY: dict[ConnectorType, type[ConnectorAdapter]] = {}


def _register_default_adapters() -> None:
    """Deferred import avoids a circular import (github_adapter imports
    ConnectorAdapter from this module)."""
    from app.services.connectors.github_adapter import GitHubConnectorAdapter

    ADAPTER_REGISTRY[ConnectorType.GITHUB] = GitHubConnectorAdapter


_register_default_adapters()


async def list_connectors(db: AsyncSession, org_id: str) -> list[Connector]:
    result = await db.execute(select(Connector).where(Connector.org_id == org_id))
    return list(result.scalars().all())


async def create_connector(db: AsyncSession, org_id: str, data: ConnectorCreate) -> Connector:
    """Persists the connector record but never actually connects — no
    adapter is registered yet. Callers should surface a 501 to the client;
    see app/api/v1/connectors.py."""
    if data.type not in ADAPTER_REGISTRY:
        raise NotImplementedError(f"No adapter registered for connector type {data.type.value}")
    connector = Connector(org_id=org_id, type=data.type, config=data.config)
    db.add(connector)
    await db.commit()
    await db.refresh(connector)
    return connector

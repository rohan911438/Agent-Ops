"""Reads service pricing, preferring the on-chain ServicePricing contract
and degrading to a static FREE default if the chain is unreachable or
unconfigured — pricing display must never block a page render.
"""

import asyncio
from dataclasses import dataclass

from app.config import get_settings

FREE_DEFAULTS: dict[str, dict] = {
    "health_scan": {"name": "Enterprise Health Scan", "price": 0, "currency": "USD", "enabled": True},
    "executive_report": {"name": "Executive Report", "price": 0, "currency": "USD", "enabled": True},
    "optimization_planner": {"name": "Optimization Planner", "price": 0, "currency": "USD", "enabled": True},
}


@dataclass
class ServicePrice:
    service_id: str
    name: str
    price: int
    currency: str
    enabled: bool
    source: str  # "chain" or "default"


async def get_service_price(service_id: str) -> ServicePrice:
    settings = get_settings()
    default = FREE_DEFAULTS.get(
        service_id, {"name": service_id, "price": 0, "currency": "USD", "enabled": True}
    )

    if settings.service_pricing_contract_address:
        try:
            from app.services.chain.base_sepolia_provider import Web3ChainProvider

            provider = Web3ChainProvider()
            result = await provider.read_service_price(service_id)
            return ServicePrice(
                service_id=service_id,
                name=result.name,
                price=result.price,
                currency=result.currency,
                enabled=result.enabled,
                source="chain",
            )
        except Exception:
            pass  # fall through to the static default below

    return ServicePrice(
        service_id=service_id,
        name=default["name"],
        price=default["price"],
        currency=default["currency"],
        enabled=default["enabled"],
        source="default",
    )


async def list_service_prices() -> list[ServicePrice]:
    return list(await asyncio.gather(*(get_service_price(service_id) for service_id in FREE_DEFAULTS)))

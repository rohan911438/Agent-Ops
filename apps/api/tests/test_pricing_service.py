"""Service pricing metadata.

No ServicePricing contract address is configured in this test environment
(see conftest.py), so every lookup below exercises the static FREE default
path — pricing display must never depend on the chain being reachable.
"""

from app.config import get_settings
from app.services.payment import pricing_service
from app.services.payment.free_provider import FreePaymentProvider
from app.services.chain.provider import ServicePriceResult


async def test_default_prices_are_free():
    price = await pricing_service.get_service_price("health_scan")
    assert price.price == 0
    assert price.enabled is True
    assert price.source == "default"


async def test_unknown_service_falls_back_to_generic_default():
    price = await pricing_service.get_service_price("some_future_service")
    assert price.price == 0
    assert price.source == "default"


async def test_list_service_prices_covers_all_seeded_services():
    prices = await pricing_service.list_service_prices()
    assert {p.service_id for p in prices} == set(pricing_service.FREE_DEFAULTS)
    assert all(p.price == 0 for p in prices)


class _FakeChainProvider:
    def __init__(self):
        pass

    async def read_service_price(self, service_id):
        return ServicePriceResult(
            service_id=service_id, name="Enterprise Health Scan", price=500, currency="USD", enabled=True
        )


async def test_reads_price_from_chain_when_configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "service_pricing_contract_address", "0xRealServicePricing")
    monkeypatch.setattr(
        "app.services.chain.base_sepolia_provider.Web3ChainProvider", _FakeChainProvider
    )

    price = await pricing_service.get_service_price("health_scan")
    assert price.source == "chain"
    assert price.price == 500


async def test_chain_failure_falls_back_to_default(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "service_pricing_contract_address", "0xRealServicePricing")

    class _BrokenProvider:
        def __init__(self):
            raise RuntimeError("RPC unreachable")

    monkeypatch.setattr("app.services.chain.base_sepolia_provider.Web3ChainProvider", _BrokenProvider)

    price = await pricing_service.get_service_price("health_scan")
    assert price.source == "default"
    assert price.price == 0


async def test_free_payment_provider_never_charges():
    provider = FreePaymentProvider()
    assert await provider.is_payment_required("health_scan") is False
    result = await provider.charge("health_scan", "org-1")
    assert result.charged is False
    assert result.amount == 0

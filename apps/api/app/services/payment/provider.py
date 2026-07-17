"""Payment provider abstraction — prepares for future x402 support without
implementing it.

Architecture: PricingService -> PaymentProvider -> (future) x402 Adapter ->
Service Execution. Only FreePaymentProvider is wired up today; every
service is priced at 0 (see ServicePricing.sol), so payment is always
bypassed. See docs/FutureMonetization.md.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PaymentResult:
    charged: bool
    amount: int
    currency: str
    reference: str | None = None


class PaymentProvider(ABC):
    @abstractmethod
    async def is_payment_required(self, service_id: str) -> bool: ...

    @abstractmethod
    async def charge(self, service_id: str, org_id: str) -> PaymentResult: ...

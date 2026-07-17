"""Placeholder for future x402 payment support.

Architecture: PricingService -> PaymentProvider -> x402 Adapter -> Service
Execution. This module is intentionally unimplemented and is not imported
by any route or service today — it exists only to document the exact shape
the eventual X402Adapter(PaymentProvider) implementation will take. See
docs/FutureMonetization.md for the migration plan.
"""

from app.services.payment.provider import PaymentProvider, PaymentResult


class X402Adapter(PaymentProvider):
    """Not implemented. Wiring this in is a post-Phase-4 decision, gated on
    services actually going paid — see docs/FutureMonetization.md. Raises
    immediately so an accidental import can't silently no-op a real charge."""

    async def is_payment_required(self, service_id: str) -> bool:
        raise NotImplementedError("x402 payment support is not implemented yet — see docs/FutureMonetization.md")

    async def charge(self, service_id: str, org_id: str) -> PaymentResult:
        raise NotImplementedError("x402 payment support is not implemented yet — see docs/FutureMonetization.md")

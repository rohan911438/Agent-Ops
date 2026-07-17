from app.services.payment.provider import PaymentProvider, PaymentResult


class FreePaymentProvider(PaymentProvider):
    """The only PaymentProvider wired up today. Every AgentOps Cloud
    service is free in this MVP, so payment is always bypassed — no charge
    ever happens. Swapping this for a real provider later (e.g. an x402
    adapter) is a call-site change, not an interface change."""

    async def is_payment_required(self, service_id: str) -> bool:
        return False

    async def charge(self, service_id: str, org_id: str) -> PaymentResult:
        return PaymentResult(charged=False, amount=0, currency="USD", reference=None)

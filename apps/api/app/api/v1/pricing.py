from fastapi import APIRouter

from app.schemas.pricing import ServicePriceRead
from app.services.payment.pricing_service import list_service_prices

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("", response_model=list[ServicePriceRead])
async def get_pricing():
    """Every service is free today. No payment logic runs here — see
    docs/FutureMonetization.md for how this evolves without an API change."""
    prices = await list_service_prices()
    return [
        ServicePriceRead(
            service_id=price.service_id,
            name=price.name,
            price=price.price,
            currency=price.currency,
            enabled=price.enabled,
        )
        for price in prices
    ]

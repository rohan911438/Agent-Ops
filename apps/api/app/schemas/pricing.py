from pydantic import BaseModel


class ServicePriceRead(BaseModel):
    service_id: str
    name: str
    price: int
    currency: str
    enabled: bool
    note: str = "Future enterprise plans may introduce paid services."

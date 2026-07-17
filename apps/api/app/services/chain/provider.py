"""Provider-agnostic on-chain trust layer abstraction.

Only Web3ChainProvider (Base Sepolia today, Base Mainnet later via config)
exists today. Mirrors app/services/llm/provider.py's shape deliberately: a
single ABC plus small dataclasses, so nothing outside this package needs to
change if a different chain/client library is swapped in later.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChainSubmissionResult:
    tx_hash: str
    contract_address: str
    block_number: int | None
    chain_id: int
    explorer_url: str


@dataclass
class ServicePriceResult:
    service_id: str
    name: str
    price: int
    currency: str
    enabled: bool


class ChainProvider(ABC):
    @abstractmethod
    async def submit_report_hash(
        self, report_hash: str, workspace_id: str, version: str, metadata_uri: str = ""
    ) -> ChainSubmissionResult: ...

    @abstractmethod
    async def read_service_price(self, service_id: str) -> ServicePriceResult: ...

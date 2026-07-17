import json
from pathlib import Path

from eth_account import Account
from web3 import Web3

from app.config import get_settings
from app.services.chain.provider import ChainProvider, ChainSubmissionResult, ServicePriceResult

ABI_DIR = Path(__file__).parent / "abi"


def _load_abi(contract_name: str) -> list:
    path = ABI_DIR / f"{contract_name}.json"
    if not path.exists():
        raise RuntimeError(
            f"Missing ABI for {contract_name} at {path}. "
            "Run `npm run export-abi -w @agentops/contracts` after deploying the contracts."
        )
    return json.loads(path.read_text())


class Web3ChainProvider(ChainProvider):
    """Signs and submits transactions against the AgentOps Base contracts.

    Every public method is a thin async wrapper around a synchronous
    web3.py call run in a worker thread (`asyncio.to_thread`) so the FastAPI
    event loop is never blocked waiting on an RPC round-trip.
    """

    def __init__(self):
        self._settings = get_settings()
        self._w3 = Web3(Web3.HTTPProvider(self._settings.chain_rpc_url))
        self._account = (
            Account.from_key(self._settings.chain_private_key) if self._settings.chain_private_key else None
        )

    async def submit_report_hash(
        self, report_hash: str, workspace_id: str, version: str, metadata_uri: str = ""
    ) -> ChainSubmissionResult:
        import asyncio

        return await asyncio.to_thread(self._submit_report_hash_sync, report_hash, workspace_id, version, metadata_uri)

    def _submit_report_hash_sync(
        self, report_hash: str, workspace_id: str, version: str, metadata_uri: str
    ) -> ChainSubmissionResult:
        if not self._account:
            raise RuntimeError("chain_private_key is not configured")
        contract_address = self._settings.report_registry_contract_address
        if not contract_address:
            raise RuntimeError("report_registry_contract_address is not configured")

        abi = _load_abi("EnterpriseReportRegistry")
        contract = self._w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

        report_hash_bytes = bytes.fromhex(report_hash.removeprefix("0x"))
        nonce = self._w3.eth.get_transaction_count(self._account.address)
        tx = contract.functions.registerReport(
            report_hash_bytes, workspace_id, version, metadata_uri
        ).build_transaction(
            {
                "from": self._account.address,
                "nonce": nonce,
                "chainId": self._settings.chain_id,
            }
        )
        signed = self._account.sign_transaction(tx)
        raw_tx = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = self._w3.eth.send_raw_transaction(raw_tx)
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        # HexBytes.hex() drops the "0x" prefix on some web3.py versions —
        # normalize so tx_hash always reads like a standard Ethereum hash.
        tx_hash_str = "0x" + tx_hash.hex().removeprefix("0x")

        return ChainSubmissionResult(
            tx_hash=tx_hash_str,
            contract_address=contract_address,
            block_number=receipt.blockNumber,
            chain_id=self._settings.chain_id,
            explorer_url=f"{self._settings.base_explorer_url}/tx/{tx_hash_str}",
        )

    async def read_service_price(self, service_id: str) -> ServicePriceResult:
        import asyncio

        return await asyncio.to_thread(self._read_service_price_sync, service_id)

    def _read_service_price_sync(self, service_id: str) -> ServicePriceResult:
        contract_address = self._settings.service_pricing_contract_address
        if not contract_address:
            raise RuntimeError("service_pricing_contract_address is not configured")

        abi = _load_abi("ServicePricing")
        contract = self._w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
        name, price, currency, enabled, _version = contract.functions.getService(service_id).call()

        return ServicePriceResult(service_id=service_id, name=name, price=price, currency=currency, enabled=enabled)

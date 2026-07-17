"""Anchors an Executive Report's hash on-chain after it's generated.

Mirrors app/services/scan/report_service.py's resilience contract: any
chain failure (unconfigured environment, network, RPC error, already
registered) degrades to a FAILED row rather than raising — a Health Scan
must never be blocked by the on-chain trust layer. See docs/SmartContracts.md
and docs/ContractArchitecture.md for why only a hash is ever submitted.
"""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.enums import VerificationStatus
from app.models.health_scan import HealthScan
from app.models.report_verification import ReportVerification
from app.services.activity_service import record_event

# Mirrors AgentOpsRegistry's initial registered version (see
# packages/contracts/scripts/deploy.ts INITIAL_PRODUCT_VERSION).
PRODUCT_VERSION = "phase4.0.0"


def compute_report_hash(report: dict) -> str:
    """Deterministic SHA-256 hash of a report's canonical JSON serialization.

    `sort_keys=True` guarantees the same report dict always hashes to the
    same value regardless of key insertion order, so re-hashing a
    previously fetched report (see docs/VerificationGuide.md) reproduces
    the exact value stored on-chain.
    """
    canonical = json.dumps(report, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def submit_report_for_verification(db: AsyncSession, org_id: str, scan: HealthScan) -> ReportVerification:
    """Hashes `scan.executive_report` and submits it to EnterpriseReportRegistry.

    Always returns a `ReportVerification` row, even when the chain call
    fails or the environment has no on-chain config at all — callers never
    need to special-case "no verification available".
    """
    settings = get_settings()
    report_hash = compute_report_hash(scan.executive_report)

    verification = ReportVerification(
        org_id=org_id,
        health_scan_id=scan.id,
        report_hash=report_hash,
        contract_address=settings.report_registry_contract_address,
        chain_id=settings.chain_id,
        status=VerificationStatus.PENDING,
        version=PRODUCT_VERSION,
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    if not settings.chain_private_key or not settings.report_registry_contract_address:
        verification.status = VerificationStatus.FAILED
        verification.error_message = "On-chain verification is not configured for this environment."
        await db.commit()
        return verification

    try:
        from app.services.chain.base_sepolia_provider import Web3ChainProvider

        provider = Web3ChainProvider()
        result = await provider.submit_report_hash(
            report_hash=report_hash,
            workspace_id=org_id,
            version=PRODUCT_VERSION,
        )
        verification.tx_hash = result.tx_hash
        verification.contract_address = result.contract_address
        verification.block_number = result.block_number
        verification.chain_id = result.chain_id
        verification.explorer_url = result.explorer_url
        verification.status = VerificationStatus.CONFIRMED
        await db.commit()

        await record_event(
            db,
            org_id=org_id,
            actor="system",
            event_type="report_verified_on_chain",
            description=f"Executive Report for scan {scan.id} anchored on Base (tx {result.tx_hash}).",
            event_metadata={"health_scan_id": scan.id, "report_hash": report_hash},
            tx_hash=result.tx_hash,
        )
    except Exception as exc:  # noqa: BLE001 — the chain layer must never fail a Health Scan
        verification.status = VerificationStatus.FAILED
        verification.error_message = str(exc)
        await db.commit()

    return verification


async def get_verification_for_scan(db: AsyncSession, org_id: str, health_scan_id: str) -> ReportVerification | None:
    stmt = select(ReportVerification).where(
        ReportVerification.org_id == org_id, ReportVerification.health_scan_id == health_scan_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

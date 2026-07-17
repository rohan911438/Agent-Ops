"""On-chain report verification.

Mirrors test_scan_reports.py's "no external config -> deterministic
fallback" contract: with no chain config set (see conftest.py), every
submission must degrade to a FAILED row rather than raise, so a Health Scan
is never blocked by the trust layer. A separate set of tests patches in a
fake ChainProvider to exercise the success path without any network call.
"""

from app.config import get_settings
from app.models.enums import ScanSourceType, VerificationStatus
from app.models.health_scan import HealthScan
from app.services import verification_service
from app.services.chain.provider import ChainSubmissionResult


def _scan(**overrides) -> HealthScan:
    defaults = dict(
        id="scan-1",
        org_id="org-1",
        source_type=ScanSourceType.FILE_UPLOAD,
        source_label="fixture.json",
        executive_report={"executive_summary": "b", "health_score": 90, "priority_actions": []},
    )
    defaults.update(overrides)
    return HealthScan(**defaults)


class _FakeChainProvider:
    def __init__(self):
        pass

    async def submit_report_hash(self, report_hash, workspace_id, version, metadata_uri=""):
        return ChainSubmissionResult(
            tx_hash="0xfaketxhash",
            contract_address="0xFakeReportRegistry",
            block_number=123,
            chain_id=84532,
            explorer_url="https://sepolia.basescan.org/tx/0xfaketxhash",
        )


def test_compute_report_hash_is_order_independent():
    a = verification_service.compute_report_hash({"a": 1, "b": 2})
    b = verification_service.compute_report_hash({"b": 2, "a": 1})
    assert a == b
    assert len(a) == 64  # sha256 hex digest


def test_compute_report_hash_changes_with_content():
    a = verification_service.compute_report_hash({"health_score": 90})
    b = verification_service.compute_report_hash({"health_score": 89})
    assert a != b


async def test_submit_without_chain_config_fails_gracefully(db_session):
    settings = get_settings()
    assert settings.chain_private_key == ""
    assert settings.report_registry_contract_address == ""

    scan = _scan()
    verification = await verification_service.submit_report_for_verification(db_session, "org-1", scan)

    assert verification.status == VerificationStatus.FAILED
    assert verification.tx_hash is None
    assert verification.error_message
    assert verification.report_hash == verification_service.compute_report_hash(scan.executive_report)


async def test_submit_with_configured_provider_succeeds(db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "chain_private_key", "0x" + "1" * 64)
    monkeypatch.setattr(settings, "report_registry_contract_address", "0xRealReportRegistry")
    monkeypatch.setattr(
        "app.services.chain.base_sepolia_provider.Web3ChainProvider", _FakeChainProvider
    )

    scan = _scan(id="scan-2")
    verification = await verification_service.submit_report_for_verification(db_session, "org-1", scan)

    assert verification.status == VerificationStatus.CONFIRMED
    assert verification.tx_hash == "0xfaketxhash"
    assert verification.block_number == 123
    assert verification.explorer_url.endswith("0xfaketxhash")

    fetched = await verification_service.get_verification_for_scan(db_session, "org-1", "scan-2")
    assert fetched is not None
    assert fetched.id == verification.id


async def test_get_verification_for_scan_returns_none_when_missing(db_session):
    result = await verification_service.get_verification_for_scan(db_session, "org-1", "never-submitted")
    assert result is None

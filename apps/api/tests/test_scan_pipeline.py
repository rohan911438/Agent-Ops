"""Integration coverage for the Enterprise Health Scan pipeline through the
real API (upload -> start -> poll -> COMPLETED) and the service layer
directly for finding M-1 (retry a FAILED scan) and M-3 (stale-scan sweep).
Previously nothing exercised scan_service.run_scan or the HTTP layer at
all — test_scan_reports.py only covers the report/plan fallback functions
in isolation. See docs/ASP-6262-Production-Readiness-Audit.md finding H-3.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import BackgroundTasks

from app.models.enums import ScanSourceType, ScanStatus
from app.models.health_scan import HealthScan
from app.services import scan_service

SAMPLE_AGENTS = {
    "agents": [
        {"name": "Support Bot", "framework": "langgraph", "model": "gpt-4o-mini"},
        {"name": "Ops Agent", "framework": "crewai", "monthly_cost_cents": 3000},
    ]
}


def _upload_file(payload: dict):
    return {"file": ("agents.json", json.dumps(payload), "application/json")}


async def _poll_until_terminal(client, scan_id: str, attempts: int = 20):
    for _ in range(attempts):
        resp = await client.get(f"/api/v1/scans/{scan_id}")
        data = resp.json()
        if data["status"] in ("completed", "failed"):
            return data
        await asyncio.sleep(0.05)
    raise AssertionError(f"Scan {scan_id} did not reach a terminal status in time")


# --- Through the real HTTP API ---------------------------------------


async def test_full_scan_pipeline_completes_via_upload(logged_in_client):
    upload_resp = await logged_in_client.post("/api/v1/scans/upload", files=_upload_file(SAMPLE_AGENTS))
    assert upload_resp.status_code == 201
    scan = upload_resp.json()
    assert scan["status"] == "pending"

    start_resp = await logged_in_client.post(f"/api/v1/scans/{scan['id']}/start")
    assert start_resp.status_code == 202

    final = await _poll_until_terminal(logged_in_client, scan["id"])
    assert final["status"] == "completed"
    assert final["summary"]["agent_count"] == 2
    assert set(final["executive_report"].keys()) >= {
        "executive_summary",
        "health_score",
        "priority_actions",
    }
    assert final["optimization_plan"]["summary"]

    history = await logged_in_client.get("/api/v1/scans")
    assert any(s["id"] == scan["id"] for s in history.json())


async def test_upload_rejects_missing_name_field(logged_in_client):
    bad = {"agents": [{"framework": "langgraph"}]}
    resp = await logged_in_client.post("/api/v1/scans/upload", files=_upload_file(bad))
    assert resp.status_code == 422


async def test_upload_rejects_oversized_file(logged_in_client):
    huge = "x" * (2 * 1024 * 1024 + 1)
    resp = await logged_in_client.post(
        "/api/v1/scans/upload", files={"file": ("agents.json", huge, "application/json")}
    )
    assert resp.status_code == 413


async def test_unauthenticated_request_is_rejected(client):
    resp = await client.post("/api/v1/scans/upload", files=_upload_file(SAMPLE_AGENTS))
    assert resp.status_code == 401


# --- start_scan / M-1 (retry a FAILED scan) directly at the service layer --


async def test_start_scan_allows_retry_from_failed(db_session):
    scan = HealthScan(
        org_id="org-1",
        source_type=ScanSourceType.FILE_UPLOAD,
        source_label="agents.json",
        status=ScanStatus.FAILED,
        error_message="a previous transient failure",
    )
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    restarted = await scan_service.start_scan(db_session, scan, BackgroundTasks())

    assert restarted.status == ScanStatus.PARSING
    assert restarted.error_message is None


async def test_start_scan_rejects_retry_from_completed(db_session):
    scan = HealthScan(
        org_id="org-1",
        source_type=ScanSourceType.FILE_UPLOAD,
        source_label="agents.json",
        status=ScanStatus.COMPLETED,
    )
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with pytest.raises(scan_service.ScanAlreadyStartedError):
        await scan_service.start_scan(db_session, scan, BackgroundTasks())


# --- sweep_stale_scans / M-3 --------------------------------------------


async def test_sweep_stale_scans_marks_old_inflight_scan_as_failed(db_session):
    stale = HealthScan(
        org_id="org-1",
        source_type=ScanSourceType.FILE_UPLOAD,
        source_label="agents.json",
        status=ScanStatus.ANALYZING,
    )
    fresh = HealthScan(
        org_id="org-1",
        source_type=ScanSourceType.FILE_UPLOAD,
        source_label="agents2.json",
        status=ScanStatus.ANALYZING,
    )
    db_session.add_all([stale, fresh])
    await db_session.commit()
    await db_session.refresh(stale)
    await db_session.refresh(fresh)

    stale.created_at = (
        datetime.now(timezone.utc) - scan_service.STALE_SCAN_THRESHOLD - timedelta(minutes=1)
    )
    await db_session.commit()

    swept = await scan_service.sweep_stale_scans(db_session)
    swept_ids = {s.id for s in swept}

    assert stale.id in swept_ids
    assert fresh.id not in swept_ids
    await db_session.refresh(stale)
    await db_session.refresh(fresh)
    assert stale.status == ScanStatus.FAILED
    assert fresh.status == ScanStatus.ANALYZING


async def test_sweep_stale_scans_ignores_pending(db_session):
    """PENDING is "created but not started yet", not stuck — must never be
    swept regardless of age."""
    pending = HealthScan(
        org_id="org-1",
        source_type=ScanSourceType.FILE_UPLOAD,
        source_label="agents.json",
        status=ScanStatus.PENDING,
    )
    db_session.add(pending)
    await db_session.commit()
    await db_session.refresh(pending)
    pending.created_at = (
        datetime.now(timezone.utc) - scan_service.STALE_SCAN_THRESHOLD - timedelta(hours=1)
    )
    await db_session.commit()

    swept = await scan_service.sweep_stale_scans(db_session)

    assert pending.id not in {s.id for s in swept}

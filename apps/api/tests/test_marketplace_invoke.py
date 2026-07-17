"""Tests for POST /marketplace/invoke — the internal service-invocation
dispatch built to close docs/ASP-6262-Production-Readiness-Audit.md
finding C-1 ("nothing in this repository can be invoked programmatically
at all"). Exercises all 4 registered ASP #6262 services end to end,
authenticated with an API key rather than a wallet session (the
machine/agent-caller path — see app/api/deps.py, app/services/
settings_service.py verify_api_key).
"""

SAMPLE_AGENTS = [
    {"name": "Support Bot", "framework": "langgraph", "model": "gpt-4o-mini"},
    {"name": "Ops Agent", "framework": "crewai", "monthly_cost_cents": 25000},
]


async def _issue_api_key(logged_in_client) -> str:
    resp = await logged_in_client.post("/api/v1/settings/api-keys", json={"name": "marketplace-worker"})
    assert resp.status_code == 201
    return resp.json()["key"]


async def _invoke(client, api_key: str, service: str, **kwargs):
    return await client.post(
        "/api/v1/marketplace/invoke",
        json={"service": service, "agents": SAMPLE_AGENTS, **kwargs},
        headers={"Authorization": f"Bearer {api_key}"},
    )


async def test_api_key_can_invoke_enterprise_health_scan(client, logged_in_client):
    api_key = await _issue_api_key(logged_in_client)
    resp = await _invoke(client, api_key, "enterprise_health_scan")

    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "enterprise_health_scan"
    assert body["status"] == "completed"
    assert body["result"]["agent_count"] == 2
    assert body["scan"]["summary"]["agent_count"] == 2


async def test_api_key_can_invoke_executive_ai_audit(client, logged_in_client):
    api_key = await _issue_api_key(logged_in_client)
    resp = await _invoke(client, api_key, "executive_ai_audit")

    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "executive_ai_audit"
    assert set(body["result"].keys()) >= {"executive_summary", "health_score", "priority_actions"}


async def test_api_key_can_invoke_ai_optimization_planner(client, logged_in_client):
    api_key = await _issue_api_key(logged_in_client)
    resp = await _invoke(client, api_key, "ai_optimization_planner")

    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "ai_optimization_planner"
    assert "summary" in body["result"]
    assert "total_estimated_monthly_savings" in body["result"]


async def test_api_key_can_invoke_ai_infrastructure_assessment(client, logged_in_client):
    api_key = await _issue_api_key(logged_in_client)
    resp = await _invoke(client, api_key, "ai_infrastructure_assessment")

    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "ai_infrastructure_assessment"
    assert isinstance(body["result"], list)
    # Ops Agent is $250/mo -> above HIGH_COST_CENTS_THRESHOLD ($200/mo)
    assert any(r["type"] == "reduce_cost" for r in body["result"])


async def test_invoke_without_api_key_is_rejected(client):
    resp = await client.post(
        "/api/v1/marketplace/invoke",
        json={"service": "enterprise_health_scan", "agents": SAMPLE_AGENTS},
    )
    assert resp.status_code == 401


async def test_invoke_with_bogus_api_key_is_rejected(client):
    resp = await client.post(
        "/api/v1/marketplace/invoke",
        json={"service": "enterprise_health_scan", "agents": SAMPLE_AGENTS},
        headers={"Authorization": "Bearer aoc_not-a-real-key"},
    )
    assert resp.status_code == 401


async def test_invoke_requires_exactly_one_data_source(client, logged_in_client):
    api_key = await _issue_api_key(logged_in_client)

    neither = await client.post(
        "/api/v1/marketplace/invoke",
        json={"service": "enterprise_health_scan"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert neither.status_code == 422

    both = await client.post(
        "/api/v1/marketplace/invoke",
        json={
            "service": "enterprise_health_scan",
            "agents": SAMPLE_AGENTS,
            "repo_url": "owner/repo",
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert both.status_code == 422


async def test_invoke_rejects_malformed_agents(client, logged_in_client):
    api_key = await _issue_api_key(logged_in_client)
    resp = await _invoke(client, api_key, "enterprise_health_scan", agents=[{"framework": "langgraph"}])
    assert resp.status_code == 422


async def test_two_orgs_do_not_see_each_others_scans_via_api_key(client, logged_in_client):
    """The API key resolves an org_id server-side from the key itself —
    confirms it can't be tricked into acting on a different org's data."""
    api_key = await _issue_api_key(logged_in_client)
    resp = await _invoke(client, api_key, "enterprise_health_scan")
    scan_id = resp.json()["scan_id"]

    # A second, independently-created workspace's session cookie should
    # not be able to see the first workspace's scan.
    from eth_account import Account
    from eth_account.messages import encode_defunct

    account = Account.create()
    nonce_resp = await client.post("/api/v1/auth/wallet/nonce", json={"address": account.address})
    body = nonce_resp.json()
    signed = Account.sign_message(encode_defunct(text=body["message"]), private_key=account.key)
    await client.post(
        "/api/v1/auth/wallet/verify",
        json={"address": account.address, "signature": signed.signature.hex(), "nonce": body["nonce"]},
    )

    other_orgs_view = await client.get(f"/api/v1/scans/{scan_id}")
    assert other_orgs_view.status_code == 404

"""Direct tests for the AI Infrastructure Assessment service's rule engine
(app/services/recommendation_service.py) — previously had zero test
coverage despite being an entire registered marketplace service (ASP
#6262, service #4). See docs/ASP-6262-Production-Readiness-Audit.md
finding H-3, and findings M-2/M-4, regression-tested here directly.
"""

from app.models.agent import Agent
from app.models.agent_permission import AgentPermission
from app.models.enums import AgentFramework, AgentSource, RecommendationType, RiskLevel
from app.services import recommendation_service

ORG_ID = "org-1"


def _agent(**overrides) -> Agent:
    defaults = dict(
        org_id=ORG_ID,
        name="Test Agent",
        framework=AgentFramework.CUSTOM,
        owner_user_id="u1",
        monthly_cost_cents=1000,
        source=AgentSource.MANUAL,
        agent_metadata={},
    )
    defaults.update(overrides)
    return Agent(**defaults)


async def _run(db_session, *agents) -> list:
    for agent in agents:
        db_session.add(agent)
    await db_session.commit()
    for agent in agents:
        await db_session.refresh(agent)
    return await recommendation_service.refresh_recommendations(db_session, ORG_ID)


async def test_unused_agent_flagged_with_no_activity(db_session):
    recs = await _run(db_session, _agent(name="Idle Agent"))
    assert any(r.type == RecommendationType.UNUSED_AGENT for r in recs)


async def test_high_cost_agent_flagged(db_session):
    recs = await _run(db_session, _agent(name="Pricey Agent", monthly_cost_cents=25000))
    assert any(r.type == RecommendationType.REDUCE_COST for r in recs)


async def test_orphaned_agent_flagged(db_session):
    recs = await _run(db_session, _agent(name="Orphan Agent", owner_user_id=None))
    assert any(r.type == RecommendationType.ORPHANED_AGENT for r in recs)


async def test_model_downgrade_suggested_for_expensive_model(db_session):
    recs = await _run(
        db_session,
        _agent(name="Expensive Model Agent", monthly_cost_cents=6000, agent_metadata={"model": "gpt-4o"}),
    )
    assert any(r.type == RecommendationType.MODEL_DOWNGRADE for r in recs)


async def test_permission_risk_flagged_for_high_risk_scope(db_session):
    agent = _agent(name="Risky Agent")
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    db_session.add(
        AgentPermission(agent_id=agent.id, scope="admin:*", resource="org", risk_level=RiskLevel.HIGH)
    )
    await db_session.commit()

    recs = await recommendation_service.refresh_recommendations(db_session, ORG_ID)
    assert any(r.type == RecommendationType.PERMISSION_RISK for r in recs)


async def test_duplicate_agents_grouped_on_strong_name_overlap(db_session):
    a = _agent(name="Support Triage Bot", framework=AgentFramework.LANGGRAPH)
    b = _agent(name="Support Triage Assistant", framework=AgentFramework.LANGGRAPH)
    recs = await _run(db_session, a, b)

    dup = [r for r in recs if r.type == RecommendationType.MERGE_DUPLICATE]
    assert len(dup) == 1
    assert "Support Triage Bot" in dup[0].description
    assert "Support Triage Assistant" in dup[0].description


async def test_duplicate_agents_no_false_positive_on_single_generic_word(db_session):
    """Regression for finding M-4: the old first-word-only match flagged
    "Support Bot" and "Support Triage Assistant" as duplicates just
    because they both start with "Support". They now share only 1 token
    out of 4 total — below the overlap threshold — so no MERGE_DUPLICATE
    should fire."""
    a = _agent(name="Support Bot", framework=AgentFramework.LANGGRAPH)
    b = _agent(name="Support Triage Assistant", framework=AgentFramework.LANGGRAPH)
    recs = await _run(db_session, a, b)

    assert not any(r.type == RecommendationType.MERGE_DUPLICATE for r in recs)


async def test_overlapping_workflows_flagged_across_frameworks(db_session):
    """Regression for finding M-2: cross-framework overlap must now be a
    real, queryable Recommendation (WORKFLOW_OPTIMIZATION), not just
    narrative text buried in the Executive Report."""
    a = _agent(name="Invoice Processor Agent", framework=AgentFramework.LANGGRAPH)
    b = _agent(name="Invoice Processor Bot", framework=AgentFramework.CREWAI)
    recs = await _run(db_session, a, b)

    assert any(r.type == RecommendationType.WORKFLOW_OPTIMIZATION for r in recs)


async def test_overlapping_workflows_ignores_same_framework_pairs(db_session):
    """Same-framework overlap is _rule_duplicate_agents' job — the two
    rules shouldn't both fire for the same pair."""
    a = _agent(name="Invoice Processor Agent", framework=AgentFramework.LANGGRAPH)
    b = _agent(name="Invoice Processor Bot", framework=AgentFramework.LANGGRAPH)
    recs = await _run(db_session, a, b)

    assert not any(r.type == RecommendationType.WORKFLOW_OPTIMIZATION for r in recs)
    assert any(r.type == RecommendationType.MERGE_DUPLICATE for r in recs)


async def test_refresh_recommendations_does_not_duplicate_open_findings(db_session):
    agent = _agent(name="Idle Agent Two")
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    first = await recommendation_service.refresh_recommendations(db_session, ORG_ID)
    second = await recommendation_service.refresh_recommendations(db_session, ORG_ID)

    assert len(first) >= 1
    assert second == []

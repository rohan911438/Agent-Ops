"""Executive Report + Optimization Plan fallback shape.

No OPENAI_API_KEY is set in this test environment (see conftest.py), so
every call below exercises the deterministic fallback path — the one that
must always produce the full, fixed shape with zero external config.
"""

from app.models.agent import Agent
from app.models.enums import (
    AgentFramework,
    AgentSource,
    AgentStatus,
    RecommendationStatus,
    RecommendationType,
    RiskLevel,
)
from app.models.recommendation import Recommendation
from app.services.scan import optimization_plan_service, report_service


def _agent(**overrides) -> Agent:
    defaults = dict(
        id="agent-1",
        org_id="org-1",
        name="Test Agent",
        framework=AgentFramework.CUSTOM,
        owner_user_id=None,
        status=AgentStatus.ACTIVE,
        monthly_cost_cents=5000,
        health_score=80,
        risk_level=RiskLevel.LOW,
        source=AgentSource.MANUAL,
        agent_metadata={},
    )
    defaults.update(overrides)
    return Agent(**defaults)


def _recommendation(**overrides) -> Recommendation:
    defaults = dict(
        id="rec-1",
        org_id="org-1",
        agent_id="agent-1",
        type=RecommendationType.UNUSED_AGENT,
        title="Test finding",
        description="Test description",
        impact_estimate="$50/mo reclaimable",
        status=RecommendationStatus.OPEN,
    )
    defaults.update(overrides)
    return Recommendation(**defaults)


async def test_report_fallback_has_all_sections_with_zero_data():
    summary = {"agent_count": 0, "frameworks": {}, "monthly_cost_cents": 0}
    report = await report_service.generate_executive_report([], [], summary)

    assert set(report.keys()) == set(report_service.REPORT_SECTIONS)
    assert len(report["priority_actions"]) == 5
    assert 0 <= report["health_score"] <= 100


async def test_report_fallback_reflects_findings():
    agents = [_agent()]
    recommendations = [
        _recommendation(type=RecommendationType.PERMISSION_RISK, impact_estimate="1 high-risk scope(s)"),
        _recommendation(id="rec-2", agent_id="agent-1", type=RecommendationType.ORPHANED_AGENT),
    ]
    summary = {
        "agent_count": 1,
        "frameworks": {"custom": 1},
        "monthly_cost_cents": 5000,
        "duplicate_count": 0,
        "orphaned_count": 1,
        "high_risk_count": 1,
        "unused_count": 0,
        "model_downgrade_count": 0,
    }

    report = await report_service.generate_executive_report(agents, recommendations, summary)

    assert report["health_score"] == 100 - 8 - 5  # permission_risk + orphaned_agent penalties
    assert report["security_risks"]["high_risk_agents"]
    assert report["operational_risks"]["orphaned_agents"]


_BUCKET_KEYS = (
    "immediate_wins",
    "thirty_day_plan",
    "ninety_day_improvements",
    "long_term_architecture",
)


def _all_items(plan: dict) -> list[dict]:
    return [item for key in _BUCKET_KEYS for item in plan[key]]


async def test_optimization_plan_matches_recommendation_count():
    recommendations = [
        _recommendation(),
        _recommendation(id="rec-2", type=RecommendationType.MODEL_DOWNGRADE),
    ]

    plan = await optimization_plan_service.generate_optimization_plan(
        recommendations, {"executive_summary": "test"}
    )

    assert set(plan.keys()) == {"summary", "total_estimated_monthly_savings", *_BUCKET_KEYS}
    items = _all_items(plan)
    assert len(items) == 2
    assert {item["title"] for item in items} == {r.title for r in recommendations}
    for item in items:
        assert set(optimization_plan_service.PLAN_ITEM_FIELDS) == set(item.keys())
        assert 0 <= item["confidence_score"] <= 100
        assert item["priority"] in {"low", "medium", "high"}
        assert item["risk_level"] in {"low", "medium", "high"}
        assert isinstance(item["dependencies"], list)


async def test_optimization_plan_empty_when_no_recommendations():
    plan = await optimization_plan_service.generate_optimization_plan([], {})
    assert _all_items(plan) == []
    assert plan["total_estimated_monthly_savings"] == "$0/mo"

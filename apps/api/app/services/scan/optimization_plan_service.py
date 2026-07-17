"""AI Optimization Planner — turns Recommendation Engine findings into a
phased, executive-facing implementation roadmap.

Architectural boundary (see docs/Architecture.md): the Recommendation
Engine (app/services/recommendation_service.py) finds problems — it has no
knowledge of this module and never imports from it. This module solves
them — it takes a list of already-persisted Recommendation rows as input
and never writes to the recommendations table. Swapping either module's
internals never requires touching the other; the only contract between
them is the Recommendation ORM model itself.

For every recommendation this generates a full implementation-plan item —
priority, business value, estimated cost savings, estimated engineering
effort, risk level, dependencies, confidence, rollback strategy, expected
KPI improvement, and timeline — then buckets each item into one of four
horizons (Immediate Wins / 30-Day Plan / 90-Day Improvements / Long-Term
Architecture) via a fixed, documented (priority, effort) lookup table, the
same explicit-rule-table philosophy as _TYPE_PROFILES below and
report_service._HEALTH_SCORE_PENALTIES. Nothing here is a black box.

The plan is never a restatement of individual findings: _build_fallback_summary
reasons across the whole portfolio — governance gaps, consolidation
patterns, unit-economics patterns, and a recommended execution sequence —
the way a consulting deliverable would frame it for an executive sponsor,
not a bulleted restatement of what recommendation_service already said.

Same zero-config-safe pattern as report_service.py throughout: an LLM can
enrich the narrative fields and portfolio summary when OPENAI_API_KEY is
set, but every structured field (priority/effort/risk/confidence/...) and
every fallback narrative always comes from the deterministic profiles
below — never invented, never missing, never blocking on an external
service.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass

from app.config import get_settings
from app.models.enums import RecommendationType
from app.models.recommendation import Recommendation

# --- Item shape -------------------------------------------------------

PLAN_ITEM_FIELDS = (
    "id",
    "type",
    "title",
    "business_problem",
    "business_value",
    "technical_reason",
    "recommended_action",
    "priority",
    "estimated_cost_savings",
    "estimated_engineering_effort",
    "risk_level",
    "dependencies",
    "confidence_score",
    "rollback_strategy",
    "expected_kpi_improvement",
    "timeline",
    "expected_roi",
)

# Narrative fields an LLM may rewrite; everything else in an item is
# always rule-derived — see module docstring.
_NARRATIVE_FIELDS = (
    "business_problem",
    "business_value",
    "technical_reason",
    "recommended_action",
    "expected_kpi_improvement",
    "expected_roi",
)

_IMPACT_DOLLAR_RE = re.compile(r"\$?([\d,]+(?:\.\d+)?)")


def _dollar_value(text: str) -> float:
    match = _IMPACT_DOLLAR_RE.search(text or "")
    if not match:
        return 0.0
    return float(match.group(1).replace(",", ""))


# --- Deterministic per-type profile ------------------------------------


@dataclass(frozen=True)
class _TypeProfile:
    business_problem: str
    business_value: str
    recommended_action: str
    expected_kpi_improvement: str
    rollback_strategy: str
    dependencies: tuple[str, ...]
    priority: str  # high | medium | low
    effort: str  # low | medium | high — drives both the effort label and the bucket
    effort_label: str
    risk_level: str  # low | medium | high — risk of *executing* this change
    confidence: int


_TYPE_PROFILES: dict[RecommendationType, _TypeProfile] = {
    RecommendationType.MERGE_DUPLICATE: _TypeProfile(
        business_problem="Duplicate agents increase maintenance cost and let configuration drift apart "
        "without adding capability.",
        business_value="Consolidating into one implementation cuts ongoing maintenance cost and removes "
        "the risk of the two versions silently diverging in behavior.",
        recommended_action="Consolidate the duplicate agents into a single canonical implementation and "
        "retire the rest.",
        expected_kpi_improvement="Agent count for this capability drops to 1 with no regression in output "
        "quality.",
        rollback_strategy="Retain the retired agent's full configuration for 30 days; restore it "
        "immediately if the consolidated agent underperforms.",
        dependencies=(
            "Confirm no downstream workflow references the agent(s) being retired",
            "Sign-off from each duplicate agent's owner",
        ),
        priority="high",
        effort="medium",
        effort_label="Medium — roughly 3-5 engineer-days to consolidate, test, and cut over.",
        risk_level="medium",
        confidence=75,
    ),
    RecommendationType.REDUCE_COST: _TypeProfile(
        business_problem="This agent represents a disproportionate share of total AI spend relative to "
        "the value it delivers.",
        business_value="Directly reduces monthly AI spend without a rebuild — the fastest lever available "
        "for cost control.",
        recommended_action="Audit model choice, prompt size, and caching opportunities before considering "
        "a rebuild.",
        expected_kpi_improvement="Monthly cost for this agent drops by the estimated savings within one "
        "billing cycle.",
        rollback_strategy="Revert the prompt/model change immediately; no data or state is affected.",
        dependencies=("Baseline current output quality before making changes",),
        priority="high",
        effort="low",
        effort_label="Low — roughly 1-2 engineer-days for a prompt/model audit.",
        risk_level="low",
        confidence=70,
    ),
    RecommendationType.UNUSED_AGENT: _TypeProfile(
        business_problem="Idle infrastructure continues to accrue cost and attack surface with no "
        "business activity to justify it.",
        business_value="Recovers idle spend immediately and shrinks unmonitored attack surface at "
        "minimal effort.",
        recommended_action="Archive or decommission the agent; retain its configuration for 30 days in "
        "case it's needed again.",
        expected_kpi_improvement="Zero cost attributed to this agent 30 days after decommission, with no "
        "incident tied to its removal.",
        rollback_strategy="Restore from the 30-day retained configuration snapshot if the agent turns out "
        "to still be needed.",
        dependencies=("Confirm with the agent's owner (if any) before decommissioning",),
        priority="medium",
        effort="low",
        effort_label="Low — under a day to archive and confirm no dependents.",
        risk_level="low",
        confidence=85,
    ),
    RecommendationType.PERMISSION_RISK: _TypeProfile(
        business_problem="Excess permissions increase the blast radius if this agent is compromised or "
        "misconfigured.",
        business_value="Materially reduces the blast radius of a compromised or misconfigured agent — the "
        "highest-leverage security fix in this scan.",
        recommended_action="Scope permissions down to least privilege required by the agent's actual "
        "observed activity.",
        expected_kpi_improvement="Agent's permission scopes match the least-privilege set required by its "
        "activity.",
        rollback_strategy="Revert to the prior permission set immediately if legitimate activity breaks "
        "after scoping down.",
        dependencies=(
            "Map required scopes from recent activity logs before scoping down",
            "Security team review for high-risk scope changes",
        ),
        priority="high",
        effort="medium",
        effort_label="Medium — roughly 2-4 engineer-days to map real usage before scoping down.",
        risk_level="medium",
        confidence=80,
    ),
    RecommendationType.ORPHANED_AGENT: _TypeProfile(
        business_problem="No one is accountable for this agent's behavior, cost, or access — an audit and "
        "incident-response gap.",
        business_value="Restores accountability for cost, behavior, and incident response — closes an "
        "audit gap at near-zero engineering cost.",
        recommended_action="Assign an accountable owner from the team that operates or depends on this "
        "agent.",
        expected_kpi_improvement="Agent has a named, accountable owner in the system of record.",
        rollback_strategy="N/A — assigning an owner carries no technical rollback risk.",
        dependencies=("Identify the team most likely responsible based on the agent's purpose and "
        "framework",),
        priority="medium",
        effort="low",
        effort_label="Low — an ownership assignment, no code change.",
        risk_level="low",
        confidence=90,
    ),
    RecommendationType.MODEL_DOWNGRADE: _TypeProfile(
        business_problem="This agent runs on a premium model where a cheaper model would likely deliver "
        "comparable output quality.",
        business_value="Cuts unit cost per agent run while preserving output quality for most workloads — "
        "compounds across every future invocation.",
        recommended_action="Run an A/B comparison against the suggested cheaper model before switching "
        "production traffic.",
        expected_kpi_improvement="Output quality holds steady on spot-check after the model switch, at "
        "the lower cost.",
        rollback_strategy="Switch back to the original model immediately — a config flag, no "
        "infrastructure change.",
        dependencies=("A/B test against a production traffic sample before full cutover",),
        priority="medium",
        effort="low",
        effort_label="Low — a config change plus an A/B comparison, roughly 1-2 engineer-days.",
        risk_level="medium",
        confidence=65,
    ),
    RecommendationType.WORKFLOW_OPTIMIZATION: _TypeProfile(
        business_problem="The same capability appears to have been rebuilt in a different framework, "
        "splitting ownership and maintenance across two implementations of the same thing.",
        business_value="Consolidating cross-framework overlap reduces duplicate maintenance burden and "
        "gives the capability a single, unambiguous owner.",
        recommended_action="Confirm with both agents' owners whether the overlap is intentional; if not, "
        "standardize on one framework and retire the other implementation.",
        expected_kpi_improvement="The capability has exactly one active implementation across all "
        "frameworks.",
        rollback_strategy="Retain the retired agent's full configuration for 30 days; restore it "
        "immediately if the surviving agent doesn't cover the same use cases.",
        dependencies=(
            "Confirm both agents actually serve the same purpose before consolidating",
            "Sign-off from each agent's owner",
        ),
        priority="medium",
        effort="medium",
        effort_label="Medium — roughly 2-4 engineer-days to confirm overlap and migrate to one framework.",
        risk_level="medium",
        confidence=60,
    ),
}

_DEFAULT_PROFILE = _TypeProfile(
    business_problem="Flagged by the fleet health scan as an optimization opportunity.",
    business_value="Resolving this finding removes a known gap from the fleet's cost, risk, or ownership "
    "posture.",
    recommended_action="Review the finding and decide whether to apply, defer, or dismiss it.",
    expected_kpi_improvement="Finding is resolved or explicitly dismissed with a documented reason.",
    rollback_strategy="Revert the specific change made; no other side effects expected.",
    dependencies=("Review the finding and confirm scope before implementation",),
    priority="medium",
    effort="medium",
    effort_label="Medium — scope not yet characterized by the rule engine.",
    risk_level="medium",
    confidence=50,
)

# --- Horizon bucketing ---------------------------------------------------

_BUCKET_INFO: dict[str, dict[str, str]] = {
    "immediate_wins": {"label": "Immediate Wins", "timeline": "This week"},
    "thirty_day_plan": {"label": "30-Day Plan", "timeline": "Within 30 days"},
    "ninety_day_improvements": {
        "label": "90-Day Improvements",
        "timeline": "Within this quarter (90 days)",
    },
    "long_term_architecture": {
        "label": "Long-Term Architecture",
        "timeline": "6+ months — multi-quarter roadmap item",
    },
}

# (priority, effort) -> bucket key. Explicit and exhaustive rather than
# branching logic, so "why is this a 30-day item and not immediate" is
# always answerable by reading one table.
_BUCKET_MATRIX: dict[tuple[str, str], str] = {
    ("high", "low"): "immediate_wins",
    ("medium", "low"): "immediate_wins",
    ("low", "low"): "thirty_day_plan",
    ("high", "medium"): "thirty_day_plan",
    ("medium", "medium"): "thirty_day_plan",
    ("low", "medium"): "ninety_day_improvements",
    ("high", "high"): "ninety_day_improvements",
    ("medium", "high"): "long_term_architecture",
    ("low", "high"): "long_term_architecture",
}


def _bucket_for(priority: str, effort: str) -> str:
    return _BUCKET_MATRIX.get((priority, effort), "ninety_day_improvements")


# --- Item construction ---------------------------------------------------


def _fallback_item(rec: Recommendation) -> dict:
    profile = _TYPE_PROFILES.get(rec.type, _DEFAULT_PROFILE)
    bucket = _bucket_for(profile.priority, profile.effort)
    return {
        "id": rec.id,
        "type": rec.type.value,
        "title": rec.title,
        "business_problem": profile.business_problem,
        "business_value": profile.business_value,
        "technical_reason": rec.description,
        "recommended_action": profile.recommended_action,
        "priority": profile.priority,
        "estimated_cost_savings": rec.impact_estimate,
        "estimated_engineering_effort": profile.effort_label,
        "risk_level": profile.risk_level,
        "dependencies": list(profile.dependencies),
        "confidence_score": profile.confidence,
        "rollback_strategy": profile.rollback_strategy,
        "expected_kpi_improvement": profile.expected_kpi_improvement,
        "timeline": _BUCKET_INFO[bucket]["timeline"],
        "expected_roi": f"{rec.impact_estimate} for {profile.effort} implementation effort.",
        "_bucket": bucket,  # stripped before returning, see generate_optimization_plan
    }


def _group_by_bucket(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {key: [] for key in _BUCKET_INFO}
    for item in items:
        grouped[item["_bucket"]].append({k: v for k, v in item.items() if k != "_bucket"})
    return grouped


# --- Portfolio-level reasoning (never a restatement of individual items) --


def _build_fallback_summary(recommendations: list[Recommendation], grouped: dict[str, list[dict]]) -> str:
    total = len(recommendations)
    if total == 0:
        return (
            "No findings were surfaced in this scan, so there is no optimization plan to sequence yet — "
            "run another scan once agents are ingested."
        )

    type_counts = Counter(r.type for r in recommendations)
    immediate = len(grouped["immediate_wins"])
    thirty = len(grouped["thirty_day_plan"])
    ninety = len(grouped["ninety_day_improvements"])
    long_term = len(grouped["long_term_architecture"])
    total_savings = sum(
        _dollar_value(item["estimated_cost_savings"]) for bucket in grouped.values() for item in bucket
    )

    sentences = [
        f"This plan sequences {total} finding(s) from the assessment into a phased roadmap: "
        f"{immediate} immediate win(s), {thirty} item(s) for the 30-day plan, {ninety} for 90-day "
        f"improvements, and {long_term} structural item(s) reserved for long-term architecture."
    ]

    if total_savings > 0:
        sentences.append(
            f"Executed in full, these actions are projected to recover roughly ${total_savings:,.0f}/mo "
            "in AI spend."
        )

    governance_count = type_counts.get(RecommendationType.ORPHANED_AGENT, 0) + type_counts.get(
        RecommendationType.PERMISSION_RISK, 0
    )
    if governance_count >= 2:
        sentences.append(
            f"{governance_count} findings point to a governance gap rather than isolated incidents — "
            "ownership and permission hygiene should be run as a single initiative, not one-off tickets."
        )

    consolidation_count = type_counts.get(RecommendationType.MERGE_DUPLICATE, 0)
    if consolidation_count >= 1:
        sentences.append(
            f"{consolidation_count} consolidation opportunit{'y' if consolidation_count == 1 else 'ies'} "
            "suggest the fleet is growing faster than platform standards are being enforced — worth a "
            "lightweight agent-creation review process going forward."
        )

    unit_economics_count = type_counts.get(RecommendationType.MODEL_DOWNGRADE, 0) + type_counts.get(
        RecommendationType.REDUCE_COST, 0
    )
    if unit_economics_count >= 2:
        sentences.append(
            f"{unit_economics_count} findings are cost-driven, indicating model selection isn't yet "
            "governed by a cost/quality policy — a lightweight model-tiering guideline would prevent this "
            "class of finding from recurring."
        )

    if immediate > 0:
        sentences.append(
            f"Recommend starting with the {immediate} immediate win(s) to build momentum before "
            "committing engineering time to the larger 90-day and long-term items."
        )
    elif long_term > 0 and thirty == 0 and ninety == 0:
        sentences.append(
            "Every finding here is structural — expect this quarter's roadmap discussion, not a quick "
            "cleanup sprint."
        )

    return " ".join(sentences)


# --- LLM enrichment (optional, narrative-only, strict fallback) ----------


def _build_prompt(recommendations: list[Recommendation], report: dict, fallback_summary: str) -> str:
    rec_lines = "\n".join(
        f"- id={r.id} | [{r.type.value}] {r.title}: {r.description} (impact: {r.impact_estimate})"
        for r in recommendations
    )
    return f"""You are a senior Enterprise AI Infrastructure Architect turning a set of rule-engine
findings into a phased implementation roadmap for an executive sponsor, in the style of a
McKinsey / Deloitte / AWS Well-Architected review. Executive-friendly language — plain
business English, not engineering jargon. Never simply restate a finding; reason about
what the *portfolio* of findings implies about the organization.

EXECUTIVE SUMMARY CONTEXT: {report.get("executive_summary", "")}

DETERMINISTIC PORTFOLIO SUMMARY (you may improve the prose, but must preserve every fact
and number in it): {fallback_summary}

FINDINGS:
{rec_lines or "(none)"}

Respond with ONLY a JSON object with exactly these keys:
- "portfolio_summary": string, 3-6 sentences, cross-cutting reasoning about the whole set of
  findings (themes, sequencing rationale, organizational implications) — not a per-item list
- "items": array, one entry per finding above, same order, each with exactly these keys:
  - "business_problem": string, 1-2 sentences, framed for a business stakeholder
  - "business_value": string, 1-2 sentences, the upside of fixing it
  - "technical_reason": string, 1-2 sentences, the concrete technical rationale
  - "recommended_action": string, one imperative sentence
  - "expected_kpi_improvement": string, one sentence, the metric that should move
  - "expected_roi": string, one short phrase
Do not include priority, estimated_cost_savings, estimated_engineering_effort, risk_level,
dependencies, confidence_score, rollback_strategy, or timeline — those are supplied
separately by a deterministic rule table and must not be overridden.
"""


async def generate_optimization_plan(recommendations: list[Recommendation], report: dict) -> dict:
    """Returns the phased plan: {"summary", "total_estimated_monthly_savings",
    "immediate_wins", "thirty_day_plan", "ninety_day_improvements",
    "long_term_architecture"}. Deterministic every time in structure and
    ratings; only narrative prose is ever LLM-enriched, and only when it
    preserves the exact item count/order — otherwise the rule-derived text
    is used untouched. Works with zero external configuration."""
    fallback_items = [_fallback_item(rec) for rec in recommendations]
    fallback_grouped = _group_by_bucket(fallback_items)
    fallback_summary = _build_fallback_summary(recommendations, fallback_grouped)
    total_savings = sum(
        _dollar_value(item["estimated_cost_savings"])
        for bucket in fallback_grouped.values()
        for item in bucket
    )
    fallback_plan = {
        "summary": fallback_summary,
        "total_estimated_monthly_savings": f"${total_savings:,.0f}/mo",
        **fallback_grouped,
    }

    settings = get_settings()
    if not settings.openai_api_key or not recommendations:
        return fallback_plan

    try:
        from app.services.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        response = await provider.complete(
            _build_prompt(recommendations, report, fallback_summary),
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.text)
        items = parsed.get("items")
        if not isinstance(items, list) or len(items) != len(recommendations):
            return fallback_plan

        merged_items = []
        for rec, narrative in zip(recommendations, items):
            item = _fallback_item(rec)
            if isinstance(narrative, dict):
                for key in _NARRATIVE_FIELDS:
                    value = narrative.get(key)
                    if isinstance(value, str) and value.strip():
                        item[key] = value.strip()
            merged_items.append(item)

        summary = parsed.get("portfolio_summary")
        final_summary = summary.strip() if isinstance(summary, str) and summary.strip() else fallback_summary

        return {
            "summary": final_summary,
            "total_estimated_monthly_savings": fallback_plan["total_estimated_monthly_savings"],
            **_group_by_bucket(merged_items),
        }
    except Exception:
        # Any failure (network, auth, malformed JSON, unexpected shape) —
        # degrade to the deterministic plan rather than fail the scan.
        return fallback_plan

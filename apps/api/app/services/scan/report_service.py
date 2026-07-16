"""Executive Report generation for a completed Health Scan.

Turns the scan's agents + the recommendations the rule engine produced into
a nine-section report written for a senior, non-technical executive
audience — the kind of assessment a consulting AI infrastructure team would
hand back after an engagement: an executive summary, an organization
overview, cost/security/operational risk analysis, optimization
opportunities, business impact, priority actions, and an overall health
score.

Works with zero external configuration: if no OpenAI key is set, or the LLM
call/response fails for any reason, this falls back to a deterministic
template built directly from the same data the LLM would have seen (health
score included — see _health_score, an explicit rule-based formula, not a
model). The report always has all nine sections either way — callers should
never have to special-case "the AI was unavailable".
"""

import json
import re

from app.config import get_settings
from app.models.agent import Agent
from app.models.enums import RecommendationType
from app.models.recommendation import Recommendation

REPORT_SECTIONS = (
    "executive_summary",
    "organization_overview",
    "cost_analysis",
    "security_risks",
    "operational_risks",
    "optimization_opportunities",
    "business_impact",
    "priority_actions",
    "health_score",
)

_IMPACT_DOLLAR_RE = re.compile(r"\$?([\d,]+(?:\.\d+)?)")

# Explicit, documented weights — mirrors the recommendation engine's
# philosophy of staying rule-based and explainable rather than a black box.
_HEALTH_SCORE_PENALTIES: dict[str, int] = {
    "permission_risk": 8,
    "orphaned_agent": 5,
    "unused_agent": 4,
    "merge_duplicate": 3,
    "model_downgrade": 2,
}


def _dollar_value(text: str) -> float:
    match = _IMPACT_DOLLAR_RE.search(text or "")
    if not match:
        return 0.0
    return float(match.group(1).replace(",", ""))


def _group_by_type(recommendations: list[Recommendation]) -> dict[RecommendationType, list[Recommendation]]:
    grouped: dict[RecommendationType, list[Recommendation]] = {}
    for rec in recommendations:
        grouped.setdefault(rec.type, []).append(rec)
    return grouped


def _detect_redundant_workflows(agents: list[Agent]) -> list[str]:
    """Cross-framework name-similarity heuristic — separate from
    MERGE_DUPLICATE, which only catches same-framework near-duplicates."""
    findings: list[str] = []
    seen_pairs: set[frozenset[str]] = set()
    for i, a in enumerate(agents):
        a_tokens = set(re.findall(r"[a-z]+", a.name.lower()))
        if not a_tokens:
            continue
        for b in agents[i + 1 :]:
            if a.framework == b.framework:
                continue  # same-framework overlap is MERGE_DUPLICATE's job
            b_tokens = set(re.findall(r"[a-z]+", b.name.lower()))
            if not b_tokens:
                continue
            overlap = a_tokens & b_tokens
            if len(overlap) >= 2 or (len(overlap) == 1 and len(a_tokens | b_tokens) <= 3):
                pair = frozenset((a.id, b.id))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                findings.append(
                    f'"{a.name}" ({a.framework.value}) and "{b.name}" ({b.framework.value}) '
                    "appear to overlap in purpose despite using different frameworks — worth "
                    "reviewing whether both are needed."
                )
    return findings[:5]


def _health_score(summary: dict) -> int:
    """0-100 composite: starts at 100, subtracts a fixed, documented penalty
    per open finding type. Rule-derived, not a learned model — see
    _HEALTH_SCORE_PENALTIES above."""
    score = 100
    score -= summary.get("high_risk_count", 0) * _HEALTH_SCORE_PENALTIES["permission_risk"]
    score -= summary.get("orphaned_count", 0) * _HEALTH_SCORE_PENALTIES["orphaned_agent"]
    score -= summary.get("unused_count", 0) * _HEALTH_SCORE_PENALTIES["unused_agent"]
    score -= summary.get("duplicate_count", 0) * _HEALTH_SCORE_PENALTIES["merge_duplicate"]
    score -= summary.get("model_downgrade_count", 0) * _HEALTH_SCORE_PENALTIES["model_downgrade"]
    return max(0, min(100, score))


def _fallback_report(
    agents: list[Agent], recommendations: list[Recommendation], summary: dict
) -> dict:
    grouped = _group_by_type(recommendations)
    agent_count = summary.get("agent_count", 0)
    monthly_cost = summary.get("monthly_cost_cents", 0) / 100

    reduce_cost = grouped.get(RecommendationType.REDUCE_COST, [])
    unused = grouped.get(RecommendationType.UNUSED_AGENT, [])
    model_downgrades = grouped.get(RecommendationType.MODEL_DOWNGRADE, [])
    high_risk = grouped.get(RecommendationType.PERMISSION_RISK, [])
    orphaned = grouped.get(RecommendationType.ORPHANED_AGENT, [])
    duplicates = grouped.get(RecommendationType.MERGE_DUPLICATE, [])
    redundant_workflows = _detect_redundant_workflows(agents)

    health_score = _health_score(summary)
    total_findings = len(recommendations)

    executive_summary = (
        f"This assessment covers {agent_count} AI agent(s) across {len(summary.get('frameworks', {}))} "
        f"framework(s), running at approximately ${monthly_cost:,.0f}/mo. The engine surfaced "
        f"{total_findings} actionable finding(s) across cost, security, and operational risk. "
        f"Overall fleet health scores {health_score}/100 — "
        + (
            "a strong baseline with only incremental cleanup remaining."
            if health_score >= 80
            else "solid, but with meaningful risk and cost concentration worth prioritizing this quarter."
            if health_score >= 50
            else "below where an enterprise fleet this size should sit; the priority actions below "
            "address the highest-leverage items first."
        )
    )

    owned = sum(1 for a in agents if a.owner_user_id)
    organization_overview = (
        f"{agent_count} agent(s) are currently tracked, spanning "
        f"{', '.join(sorted(summary.get('frameworks', {}).keys())) or 'no frameworks yet'}. "
        f"{owned} of {agent_count} have an assigned owner"
        + (f" ({agent_count - owned} do not)." if agent_count - owned > 0 else ".")
    )

    reclaimable = sum(_dollar_value(r.impact_estimate) for r in unused)
    cost_summary = (
        f"${monthly_cost:,.0f}/mo across the fleet. {len(unused)} unused agent(s) could reclaim "
        f"roughly ${reclaimable:,.0f}/mo, and {len(reduce_cost)} agent(s) are flagged as top cost "
        "drivers worth a model or prompt review."
        if (unused or reduce_cost)
        else f"${monthly_cost:,.0f}/mo across the fleet — no major waste detected by the rule engine."
    )
    cost_analysis = {
        "summary": cost_summary,
        "model_downgrade_suggestions": [r.description for r in model_downgrades],
    }

    security_summary = (
        f"{len(high_risk)} agent(s) hold high-risk permissions beyond what their activity requires — "
        "the highest-leverage security reduction available right now."
        if high_risk
        else "No high-risk permissions detected in this scan."
    )
    security_risks = {
        "summary": security_summary,
        "high_risk_agents": [r.title for r in high_risk],
    }

    operational_summary = (
        f"{len(orphaned)} agent(s) have no assigned owner, and {len(redundant_workflows)} pair(s) of "
        "agents appear to duplicate effort across frameworks."
        if (orphaned or redundant_workflows)
        else "No ownerless agents or cross-framework redundancy detected."
    )
    operational_risks = {
        "summary": operational_summary,
        "orphaned_agents": [r.title for r in orphaned],
        "redundant_workflows": redundant_workflows,
    }

    optimization_opportunities = {
        "summary": (
            f"{len(duplicates)} merge opportunity(ies) and {len(model_downgrades)} model downgrade(s) "
            "identified."
            if (duplicates or model_downgrades)
            else "No merge or model-downgrade opportunities identified in this scan."
        ),
        "merge_candidates": [r.title for r in duplicates],
    }

    business_impact = (
        f"Acting on the findings above could reclaim roughly ${reclaimable:,.0f}/mo in idle spend, "
        f"reduce the fleet's highest-risk permission exposure ({len(high_risk)} agent(s)), and remove "
        f"{len(orphaned)} governance gap(s) — without pausing any agent currently in active use."
    )

    ranked = sorted(recommendations, key=lambda r: _dollar_value(r.impact_estimate), reverse=True)
    priority_actions = [
        {
            "title": r.title,
            "rationale": r.description,
            "estimated_impact": r.impact_estimate,
        }
        for r in ranked
    ]

    return {
        "executive_summary": executive_summary,
        "organization_overview": organization_overview,
        "cost_analysis": cost_analysis,
        "security_risks": security_risks,
        "operational_risks": operational_risks,
        "optimization_opportunities": optimization_opportunities,
        "business_impact": business_impact,
        "priority_actions": priority_actions,
        "health_score": health_score,
    }


def _normalize_dict_section(value, list_keys: tuple[str, ...]) -> dict:
    if not isinstance(value, dict):
        value = {}
    normalized = {"summary": str(value.get("summary") or "No data available.")}
    for key in list_keys:
        items = value.get(key)
        normalized[key] = items if isinstance(items, list) else []
    return normalized


def _normalize_report(report: dict, fallback: dict) -> dict:
    """Guarantees the fixed shape regardless of which path produced it —
    callers should never need to check for missing keys or a wrong-length
    priority_actions list."""
    normalized = {section: report.get(section) for section in REPORT_SECTIONS}

    normalized["executive_summary"] = str(
        normalized["executive_summary"] or fallback["executive_summary"]
    )
    normalized["organization_overview"] = str(
        normalized["organization_overview"] or fallback["organization_overview"]
    )
    normalized["business_impact"] = str(normalized["business_impact"] or fallback["business_impact"])

    normalized["cost_analysis"] = _normalize_dict_section(
        normalized["cost_analysis"], ("model_downgrade_suggestions",)
    )
    normalized["security_risks"] = _normalize_dict_section(
        normalized["security_risks"], ("high_risk_agents",)
    )
    normalized["operational_risks"] = _normalize_dict_section(
        normalized["operational_risks"], ("orphaned_agents", "redundant_workflows")
    )
    normalized["optimization_opportunities"] = _normalize_dict_section(
        normalized["optimization_opportunities"], ("merge_candidates",)
    )

    actions = normalized["priority_actions"]
    if not isinstance(actions, list):
        actions = []
    actions = actions[:5]
    while len(actions) < 5:
        actions.append(
            {
                "title": "No further action identified",
                "rationale": "The scan didn't surface additional high-impact opportunities.",
                "estimated_impact": "—",
            }
        )
    normalized["priority_actions"] = actions

    try:
        health_score = int(normalized["health_score"])
    except (TypeError, ValueError):
        health_score = fallback["health_score"]
    normalized["health_score"] = max(0, min(100, health_score))

    return normalized


def _build_prompt(agents: list[Agent], recommendations: list[Recommendation], summary: dict) -> str:
    agent_lines = "\n".join(
        f"- {a.name} | framework={a.framework.value} | model={a.agent_metadata.get('model', 'unknown')} "
        f"| ${a.monthly_cost_cents / 100:.0f}/mo | owner={'none' if not a.owner_user_id else 'assigned'} "
        f"| risk={a.risk_level.value}"
        for a in agents
    )
    rec_lines = "\n".join(
        f"- [{r.type.value}] {r.title}: {r.description} (impact: {r.impact_estimate})"
        for r in recommendations
    )
    return f"""You are a senior Enterprise AI Infrastructure Architect delivering the findings of an
AI agent fleet assessment to a company's executive team. Write like an experienced
consultant, not a generic AI assistant: concrete, quantified wherever the data supports
it, no hedging filler, no invented numbers not implied by the data below.

SCAN SUMMARY: {json.dumps(summary)}

AGENTS:
{agent_lines or "(none)"}

RULE-ENGINE FINDINGS:
{rec_lines or "(none)"}

Respond with ONLY a JSON object with exactly these keys:
- "executive_summary": string, 3-5 sentences, the top-line takeaway for a non-technical exec
- "organization_overview": string, 2-3 sentences on fleet composition and ownership coverage
- "cost_analysis": object {{"summary": string, "model_downgrade_suggestions": array of strings}}
- "security_risks": object {{"summary": string, "high_risk_agents": array of strings}}
- "operational_risks": object {{"summary": string, "orphaned_agents": array of strings, "redundant_workflows": array of strings}}
- "optimization_opportunities": object {{"summary": string, "merge_candidates": array of strings}}
- "business_impact": string, 2-4 sentences translating the findings into business terms (cost, risk, time)
- "priority_actions": array of exactly 5 objects, each {{"title": string, "rationale": string, "estimated_impact": string}},
  ranked by ROI, highest first
- "health_score": integer 0-100, overall fleet health
"""


async def generate_executive_report(
    agents: list[Agent], recommendations: list[Recommendation], summary: dict
) -> dict:
    settings = get_settings()
    fallback = _fallback_report(agents, recommendations, summary)
    if not settings.openai_api_key:
        return _normalize_report(fallback, fallback)

    try:
        from app.services.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        response = await provider.complete(
            _build_prompt(agents, recommendations, summary),
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.text)
        return _normalize_report(parsed, fallback)
    except Exception:
        # Any failure (network, auth, malformed JSON, unexpected shape) —
        # degrade to the deterministic report rather than fail the scan.
        return _normalize_report(fallback, fallback)

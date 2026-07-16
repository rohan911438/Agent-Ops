"""Executive Report generation for a completed Health Scan.

Turns the scan's agents + the recommendations the rule engine produced
into a narrative aimed at a non-technical exec: where money is wasted,
where risk is highest, what to merge, what to downgrade, what looks
redundant, and the top 5 highest-ROI actions.

Works with zero external configuration: if no OpenAI key is set, or the
LLM call/response fails for any reason, this falls back to a deterministic
template built directly from the same data the LLM would have seen. The
report always has all six sections and exactly five top actions either
way — callers should never have to special-case "the AI was unavailable".
"""

import json
import re

from app.config import get_settings
from app.models.agent import Agent
from app.models.enums import RecommendationType
from app.models.recommendation import Recommendation

REPORT_SECTIONS = (
    "money_wasted",
    "risk_summary",
    "merge_candidates",
    "model_downgrades",
    "redundant_workflows",
    "top_actions",
)

_IMPACT_DOLLAR_RE = re.compile(r"\$?([\d,]+(?:\.\d+)?)")


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


def _fallback_report(
    agents: list[Agent], recommendations: list[Recommendation], summary: dict
) -> dict:
    grouped = _group_by_type(recommendations)

    reduce_cost = grouped.get(RecommendationType.REDUCE_COST, [])
    unused = grouped.get(RecommendationType.UNUSED_AGENT, [])
    reclaimable = sum(_dollar_value(r.impact_estimate) for r in unused)
    money_wasted = (
        f"${summary.get('monthly_cost_cents', 0) / 100:,.0f}/mo across "
        f"{summary.get('agent_count', 0)} agents. "
        f"{len(unused)} unused agent(s) could reclaim roughly ${reclaimable:,.0f}/mo, and "
        f"{len(reduce_cost)} agent(s) are flagged as top cost drivers worth a model or "
        "prompt review."
        if (unused or reduce_cost)
        else f"${summary.get('monthly_cost_cents', 0) / 100:,.0f}/mo across "
        f"{summary.get('agent_count', 0)} agents — no major waste detected by the rule engine."
    )

    high_risk = grouped.get(RecommendationType.PERMISSION_RISK, [])
    orphaned = grouped.get(RecommendationType.ORPHANED_AGENT, [])
    risk_summary = (
        f"{len(high_risk)} agent(s) hold high-risk permissions beyond what their activity "
        f"requires, and {len(orphaned)} agent(s) have no assigned owner — both are the "
        "highest-leverage risk reductions available right now."
        if (high_risk or orphaned)
        else "No high-risk permissions or ownerless agents detected in this scan."
    )

    merge_candidates = [r.title for r in grouped.get(RecommendationType.MERGE_DUPLICATE, [])]
    model_downgrades = [r.description for r in grouped.get(RecommendationType.MODEL_DOWNGRADE, [])]
    redundant_workflows = _detect_redundant_workflows(agents)

    ranked = sorted(recommendations, key=lambda r: _dollar_value(r.impact_estimate), reverse=True)
    top_actions = [
        {
            "title": r.title,
            "rationale": r.description,
            "estimated_impact": r.impact_estimate,
        }
        for r in ranked
    ]

    return {
        "money_wasted": money_wasted,
        "risk_summary": risk_summary,
        "merge_candidates": merge_candidates,
        "model_downgrades": model_downgrades,
        "redundant_workflows": redundant_workflows,
        "top_actions": top_actions,
    }


def _normalize_report(report: dict) -> dict:
    """Guarantees the fixed shape regardless of which path produced it —
    callers should never need to check for missing keys or a wrong-length
    top_actions list."""
    normalized = {section: report.get(section) for section in REPORT_SECTIONS}
    for list_field in ("merge_candidates", "model_downgrades", "redundant_workflows"):
        if not isinstance(normalized[list_field], list):
            normalized[list_field] = []
    normalized["money_wasted"] = str(normalized["money_wasted"] or "No cost data available.")
    normalized["risk_summary"] = str(normalized["risk_summary"] or "No risk data available.")

    actions = normalized["top_actions"]
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
    normalized["top_actions"] = actions
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
    return f"""You are writing an Executive Health Report for a company's AI agent fleet, for a
non-technical executive audience. Be concrete and quantify impact wherever the data
supports it. Do not invent numbers not implied by the data below.

SCAN SUMMARY: {json.dumps(summary)}

AGENTS:
{agent_lines or "(none)"}

RULE-ENGINE FINDINGS:
{rec_lines or "(none)"}

Respond with ONLY a JSON object with exactly these keys:
- "money_wasted": string, 2-4 sentences on where money is being wasted and how much
- "risk_summary": string, 2-4 sentences on where operational risk is highest
- "merge_candidates": array of strings, agents/groups that should be merged
- "model_downgrades": array of strings, specific model downgrade suggestions
- "redundant_workflows": array of strings, workflows that appear redundant
- "top_actions": array of exactly 5 objects, each {{"title": string, "rationale": string, "estimated_impact": string}},
  ranked by ROI, highest first
"""


async def generate_executive_report(
    agents: list[Agent], recommendations: list[Recommendation], summary: dict
) -> dict:
    settings = get_settings()
    if not settings.openai_api_key:
        return _normalize_report(_fallback_report(agents, recommendations, summary))

    try:
        from app.services.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        response = await provider.complete(
            _build_prompt(agents, recommendations, summary),
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.text)
        return _normalize_report(parsed)
    except Exception:
        # Any failure (network, auth, malformed JSON, unexpected shape) —
        # degrade to the deterministic report rather than fail the scan.
        return _normalize_report(_fallback_report(agents, recommendations, summary))

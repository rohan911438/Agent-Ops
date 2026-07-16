"""Parses uploaded agent-definition files (JSON/YAML) into the raw dict
shape scan_service.py ingests through the normal agent_service layer.

Deliberately lenient: a scan is a discovery tool, not a strict schema
validator. A single malformed agent entry (bad framework name, missing
optional field) should never fail the whole upload — only a missing
`name` or an unparseable file does.
"""

import json

import yaml

from app.models.enums import AgentFramework


class ScanParseError(Exception):
    """Raised when the uploaded content can't be parsed into agent
    definitions at all — caught by the API layer and returned as a 422."""


def _coerce_framework(value: str | None) -> AgentFramework:
    if not value:
        return AgentFramework.CUSTOM
    try:
        return AgentFramework(str(value).strip().lower())
    except ValueError:
        return AgentFramework.CUSTOM


def parse_agent_definitions(content: str, filename: str) -> list[dict]:
    """Returns a list of raw agent dicts: name, framework, model,
    monthly_cost_cents, owner_email, permissions (all but name optional)."""
    lower_name = filename.lower()

    if lower_name.endswith((".yaml", ".yml")):
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ScanParseError(f"Could not parse {filename} as YAML: {exc}") from exc
    elif lower_name.endswith(".json"):
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ScanParseError(f"Could not parse {filename} as JSON: {exc}") from exc
    else:
        raise ScanParseError(
            f"Unsupported file type for {filename} — expected .json, .yaml, or .yml"
        )

    if isinstance(data, dict) and "agents" in data:
        data = data["agents"]
    if not isinstance(data, list):
        raise ScanParseError(
            "Expected a list of agents (or an object with an \"agents\" list) at the top level"
        )
    if not data:
        raise ScanParseError("No agents found in the uploaded file")

    agents: list[dict] = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ScanParseError(f"Agent at index {i} is missing a required \"name\" field")
        agents.append(
            {
                "name": str(raw["name"]),
                "framework": _coerce_framework(raw.get("framework")),
                "model": raw.get("model"),
                "monthly_cost_cents": raw.get("monthly_cost_cents"),
                "owner_email": raw.get("owner_email"),
                "permissions": raw.get("permissions") or [],
            }
        )
    return agents

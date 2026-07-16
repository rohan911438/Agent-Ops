"""Real GitHub connector: genuinely registered in ADAPTER_REGISTRY, with an
explicitly-labeled placeholder for the actual "what agents live in this
repo" inference.

test_connection does a real, cheap GitHub API call to confirm the repo
exists and is reachable. sync_agents does a real (not faked) static scan
of root-level dependency manifests for known agent-framework package
markers — it does not execute or deeply parse the repo's code. Every
agent it produces is tagged agent_metadata.needs_review=True so the UI
and the rest of the product never treat a GitHub-detected agent as
equivalent in confidence to a manually entered or uploaded one.
"""

import base64
import re

import httpx

from app.models.enums import AgentFramework, ConnectorType
from app.services.connector_service import ConnectorAdapter

GITHUB_API = "https://api.github.com"

# Root-level manifest files worth inspecting, capped to keep the total
# number of API calls small (well under the 60/hr unauthenticated limit).
_MANIFEST_FILES = ("requirements.txt", "pyproject.toml", "package.json")

# package-name marker -> framework it implies. Checked as a substring
# against lowercased manifest content.
_FRAMEWORK_MARKERS: list[tuple[str, AgentFramework]] = [
    ("langgraph", AgentFramework.LANGGRAPH),
    ("crewai", AgentFramework.CREWAI),
    ("openai-agents", AgentFramework.OPENAI_AGENTS),
    ("pyautogen", AgentFramework.AUTOGEN),
    ("autogen-agentchat", AgentFramework.AUTOGEN),
]

_REPO_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$"
)
_SHORTHAND_RE = re.compile(r"^([^/\s]+)/([^/\s]+)$")


class GitHubRepoError(Exception):
    """Repo URL couldn't be parsed, or the repo isn't reachable."""


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    repo_url = (repo_url or "").strip()
    match = _REPO_URL_RE.match(repo_url) or _SHORTHAND_RE.match(repo_url)
    if not match:
        raise GitHubRepoError(
            f'Could not parse "{repo_url}" as a GitHub repo — expected a URL like '
            "https://github.com/owner/repo or the shorthand owner/repo"
        )
    return match.group(1), match.group(2)


def _headers(token: str | None) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


class GitHubConnectorAdapter(ConnectorAdapter):
    type = ConnectorType.GITHUB

    async def test_connection(self, config: dict) -> bool:
        owner, repo = parse_repo_url(config.get("repo_url", ""))
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}", headers=_headers(config.get("github_token"))
            )
        return resp.status_code == 200

    async def sync_agents(self, config: dict) -> list[dict]:
        owner, repo = parse_repo_url(config.get("repo_url", ""))
        token = config.get("github_token")
        headers = _headers(token)

        agents: list[dict] = []
        detected_frameworks: set[AgentFramework] = set()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for filename in _MANIFEST_FILES:
                resp = await client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/contents/{filename}", headers=headers
                )
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                if payload.get("encoding") != "base64":
                    continue
                try:
                    content = base64.b64decode(payload["content"]).decode("utf-8", errors="ignore")
                except (ValueError, KeyError):
                    continue

                lowered = content.lower()
                for marker, framework in _FRAMEWORK_MARKERS:
                    if marker in lowered and framework not in detected_frameworks:
                        detected_frameworks.add(framework)
                        agents.append(
                            {
                                "name": f"{repo} ({framework.value})",
                                "framework": framework,
                                "model": None,
                                "monthly_cost_cents": None,
                                "owner_email": None,
                                "permissions": [],
                                "detected_via": "github_static_scan",
                                "needs_review": True,
                                "source_file": filename,
                            }
                        )

        return agents

import enum


class AgentFramework(str, enum.Enum):
    OPENAI_AGENTS = "openai_agents"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    N8N = "n8n"
    CUSTOM = "custom"
    MCP = "mcp"
    INTERNAL = "internal"


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    ARCHIVED = "archived"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentSource(str, enum.Enum):
    MANUAL = "manual"
    CONNECTOR = "connector"


class RecommendationType(str, enum.Enum):
    MERGE_DUPLICATE = "merge_duplicate"
    REDUCE_COST = "reduce_cost"
    UNUSED_AGENT = "unused_agent"
    PERMISSION_RISK = "permission_risk"
    MEMORY_OPTIMIZATION = "memory_optimization"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"


class RecommendationStatus(str, enum.Enum):
    OPEN = "open"
    DISMISSED = "dismissed"
    APPLIED = "applied"


class ConnectorType(str, enum.Enum):
    GITHUB = "github"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    OPENAI_AGENTS_SDK = "openai_agents_sdk"
    MCP = "mcp"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class ConnectorStatus(str, enum.Enum):
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"
    ERROR = "error"


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class WalletChain(str, enum.Enum):
    BASE = "base"

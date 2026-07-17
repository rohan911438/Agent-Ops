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
    ORPHANED_AGENT = "orphaned_agent"
    MODEL_DOWNGRADE = "model_downgrade"


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


class ScanSourceType(str, enum.Enum):
    FILE_UPLOAD = "file_upload"
    GITHUB = "github"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    OPENAI_AGENTS_SDK = "openai_agents_sdk"


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class WalletChain(str, enum.Enum):
    BASE = "base"


class VerificationStatus(str, enum.Enum):
    """Status of an Executive Report's on-chain proof submission — see
    app/services/verification_service.py. A chain failure never fails the
    Health Scan itself; it just leaves the row at FAILED."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class AuthProviderType(str, enum.Enum):
    """Identity provider that authenticated a user. WALLET (OKX) is the only
    one implemented today — see app/auth/providers/. The rest are reserved
    extension points: adding one means a new provider module + route, no
    changes to app/auth/session.py, app/auth/deps.py, or any existing
    router (see docs/Architecture.md)."""

    WALLET = "wallet"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    OKTA = "okta"
    SAML = "saml"

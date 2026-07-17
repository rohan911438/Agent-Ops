from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The literal value session_secret_key defaults to below AND the hardcoded
# fallback in apps/web/middleware.ts — kept as one named constant here so
# the "is this still the insecure default" check has a single source of
# truth instead of a magic string repeated at each call site.
INSECURE_DEFAULT_SESSION_SECRET = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    """Central app configuration, loaded from environment / .env.

    Kept deliberately small for the MVP — see docs/TechnicalDecisions.md
    for why SQLite + no queue broker is the right call at this stage.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite+aiosqlite:///./data/agentops.db"

    # Session JWT — signs/verifies the cookie issued after a successful
    # wallet login (see app/auth/session.py). Shared with apps/web's
    # SESSION_JWT_SECRET so Next.js middleware can verify the same token
    # at the edge without a round-trip to the API.
    session_secret_key: str = INSECURE_DEFAULT_SESSION_SECRET
    session_ttl_seconds: int = 60 * 60 * 24 * 7

    # Wallet auth needs no third-party config (unlike Clerk), so there's no
    # natural "unconfigured -> skip" state anymore. AUTH_DISABLED is the
    # explicit opt-out that preserves zero-config local dev: true resolves
    # every request to a fixed seeded dev-org/dev-user, exactly like today's
    # "Clerk env vars unset" behavior did.
    auth_disabled: bool = True

    openai_api_key: str = ""

    # On-chain trust layer (Base Sepolia today, Base Mainnet later — same
    # code, different values). Never required: every chain call degrades
    # gracefully when unconfigured, exactly like OpenAIProvider's fallback.
    # See app/services/chain/ and docs/SmartContracts.md.
    chain_rpc_url: str = "https://sepolia.base.org"
    chain_id: int = 84532
    # Backend signer key used to submit report hashes / read pricing.
    # Never the same trust boundary as end-user wallets — this key only
    # ever touches the three AgentOps contracts below.
    chain_private_key: str = ""
    report_registry_contract_address: str = ""
    service_pricing_contract_address: str = ""
    agentops_registry_contract_address: str = ""
    base_explorer_url: str = "https://sepolia.basescan.org"

    cors_origins: str = "http://localhost:3000"

    # See app/middleware.py RateLimitMiddleware. Configurable so a growing
    # integration-test suite (many requests in a tight loop against one
    # shared in-process app instance — see tests/conftest.py) doesn't trip
    # the same limit meant to catch production abuse.
    rate_limit_max_requests: int = 120
    rate_limit_window_seconds: float = 60.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _reject_insecure_production_config(self) -> "Settings":
        """Dev-friendly zero-config defaults (open auth, a public signing
        secret) must never silently reach a non-development environment —
        see docs/ASP-6262-Production-Readiness-Audit.md finding C-2. Chain
        settings are deliberately exempt: they're designed to degrade, not
        required (see the on-chain trust layer comment above)."""
        if self.environment == "development":
            return self
        problems = []
        if self.auth_disabled:
            problems.append("AUTH_DISABLED must be false outside development")
        if self.session_secret_key == INSECURE_DEFAULT_SESSION_SECRET:
            problems.append("SESSION_SECRET_KEY must be set to a real secret outside development")
        if problems:
            raise ValueError(
                f"Insecure configuration for environment={self.environment!r}: " + "; ".join(problems)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    session_secret_key: str = "dev-insecure-secret-change-me"
    session_ttl_seconds: int = 60 * 60 * 24 * 7

    # Wallet auth needs no third-party config (unlike Clerk), so there's no
    # natural "unconfigured -> skip" state anymore. AUTH_DISABLED is the
    # explicit opt-out that preserves zero-config local dev: true resolves
    # every request to a fixed seeded dev-org/dev-user, exactly like today's
    # "Clerk env vars unset" behavior did.
    auth_disabled: bool = True

    openai_api_key: str = ""

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

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

    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_webhook_secret: str = ""

    openai_api_key: str = ""

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def auth_enabled(self) -> bool:
        """Clerk verification is skipped when unconfigured, so local dev
        never needs a live Clerk project just to hit the API."""
        return bool(self.clerk_jwks_url and self.clerk_issuer)


@lru_cache
def get_settings() -> Settings:
    return Settings()

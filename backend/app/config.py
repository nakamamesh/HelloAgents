from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# asyncpg rejects libpq-style query params that Fly/Railway often inject
_ASYNCPG_DROP_QUERY = frozenset({"sslmode", "channel_binding"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HelloAgents"
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = (
        "postgresql+asyncpg://helloagents:helloagents@localhost:5432/helloagents"
    )
    redis_url: str = "redis://localhost:6379/0"

    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-v4-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Control-plane admin + machine JWT (server-side only)
    admin_api_key: str = "dev-admin-change-me"
    jwt_secret: str = "dev-jwt-change-me-to-at-least-32-chars"
    jwt_expires_minutes: int = 60
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Turnkey agent wallets (Base Sepolia first)
    turnkey_organization_id: str = ""
    turnkey_api_public_key: str = ""
    turnkey_api_private_key: str = ""
    turnkey_api_base_url: str = "https://api.turnkey.com"
    wallet_network: str = "base-sepolia"
    wallet_required: bool = False  # if True, register fails when provision fails
    x402_facilitator_url: str = "https://facilitator.xpay.sh"
    settlement_dry_run: bool = False  # skip on-chain when faucets unavailable
    # Max USDC per EIP-3009 auth (atomic units derived at policy apply time)
    wallet_spend_limit_usdc: str = "100.000000"
    # Warn when platform treasury ETH (gas) is below this (ether units as string)
    treasury_min_eth: str = "0.001"
    # Recruit pitches: False = \$0 template pitches (default); True = OpenRouter polish
    recruit_use_llm: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """Fly/Railway often inject postgres:// + sslmode — force asyncpg-safe URL."""
        if not isinstance(value, str) or not value:
            return value
        url = value.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        parts = urlsplit(url)
        query = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in _ASYNCPG_DROP_QUERY
        ]
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

    @field_validator(
        "openrouter_api_key",
        "admin_api_key",
        "jwt_secret",
        "turnkey_organization_id",
        "turnkey_api_public_key",
        "turnkey_api_private_key",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

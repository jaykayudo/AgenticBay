from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Agentic Bay"
    APP_ENV: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    JWT_SECRET: str
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            import json

            result: list[str] = json.loads(v)
            return result
        return list(v)

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OAuth sign-in
    GOOGLE_AUTH_URL: str | None = None
    FACEBOOK_AUTH_URL: str | None = None

    # Email OTP auth
    EMAIL_OTP_EXPIRE_SECONDS: int = 60 * 10
    EMAIL_OTP_MAX_ATTEMPTS: int = 5
    EMAIL_OTP_RATE_LIMIT_WINDOW_SECONDS: int = 60 * 15
    EMAIL_OTP_RATE_LIMIT_MAX_REQUESTS: int = 3

    # Orchestrator
    ORCHESTRATOR_WS_URL: str = "ws://localhost:8000"

    # Web3
    RPC_URL: str = ""
    INVOICE_CONTRACT_ADDRESS: str = ""
    INVOICE_CONTRACT_ABI: str = ""
    ORCHESTRATOR_PRIVATE_KEY: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

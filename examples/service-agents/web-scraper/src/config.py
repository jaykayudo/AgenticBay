from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Orchestrator
    ORCHESTRATOR_API_KEY: str

    # Agent identity
    AGENT_WALLET_ADDRESS: str
    AGENT_ID: str = ""

    # Service
    PORT: int = 5000
    LOG_LEVEL: str = "INFO"
    SCRAPER_TIMEOUT_SECONDS: float = 15.0
    SCRAPER_MAX_RESPONSE_BYTES: int = 2_000_000

    model_config = {"env_file": ".env"}


settings = Settings()

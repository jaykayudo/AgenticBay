from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Orchestrator
    ORCHESTRATOR_API_KEY: str

    # Agent identity
    AGENT_WALLET_ADDRESS: str
    AGENT_ID: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str

    # Service
    PORT: int = 5000
    LOG_LEVEL: str = "INFO"
    RESEARCH_TIMEOUT_SECONDS: float = 15.0

    model_config = {"env_file": ".env"}


settings = Settings()

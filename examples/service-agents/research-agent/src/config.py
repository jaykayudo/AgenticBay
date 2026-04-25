from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ORCHESTRATOR_API_KEY: str
    AGENT_WALLET_ADDRESS: str
    AGENT_ID: str = ""
    ANTHROPIC_API_KEY: str
    PORT: int = 5001
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()

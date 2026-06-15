from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Research Copilot"
    debug: bool = False
    database_url: str = "sqlite:///./research.db"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    model_config = {"env_prefix": "RESEARCH_COPILOT_", "env_file": ".env"}


settings = Settings()

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    secret_key: str = "change-me-to-a-random-string"
    debug: bool = False

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8085/auth/callback"

    # LLM
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "gemma3:4b"

    # Redis
    redis_url: str = "redis://stardiscover-redis:6379/0"

    # Scheduler
    weekly_refresh_day: str = "sunday"
    weekly_refresh_hour: int = 3

    # Rate limiting
    github_requests_per_hour: int = 5000
    max_stargazers_sample: int = 100
    max_similar_users: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Singleton for easy access
settings = get_settings()

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Required environment variables:
    - SEVDESK_API_KEY: Your SevDesk API key (required)
    """

    # SevDesk API Configuration
    sevdesk_api_key: str
    sevdesk_base_url: str = "https://my.sevdesk.de/api/v1"

    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./sevdesk.db"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # CORS Configuration
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

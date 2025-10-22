from typing import List, Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Core Home Assistant settings
    HA_URL: str
    HA_TOKEN: str

    # API authentication
    API_KEYS: List[str]

    # SSL Configuration (optional)
    SSL_CERT: Optional[str] = None
    SSL_KEY: Optional[str] = None

    # Feature flags
    CACHE_TTL: int = 300
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    METRICS_ENABLED: bool = True
    WEBSOCKET_ENABLED: bool = True

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

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
    STATES_CACHE_TTL: int = 60  # States change frequently
    SERVICES_CACHE_TTL: int = 1800  # Services change rarely
    CONFIG_CACHE_TTL: int = 3600  # Config changes very rarely
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    METRICS_ENABLED: bool = True
    WEBSOCKET_ENABLED: bool = True

    # WebSocket Configuration
    WEBSOCKET_RECONNECT_MAX_ATTEMPTS: int = 0  # 0 = infinite retries
    WEBSOCKET_RECONNECT_MAX_DELAY: int = 60  # Max backoff delay in seconds

    # Event Filtering (Performance optimization for Raspberry Pi)
    WEBSOCKET_FILTER_ENABLED: bool = True
    WEBSOCKET_ENTITY_FILTERS: List[str] = []  # e.g., ["light.", "switch."]
    WEBSOCKET_EXCLUDE_DOMAINS: List[str] = ["media_player", "camera"]

    # Cache Update Strategy
    WEBSOCKET_UPDATE_CACHE: bool = (
        True  # Update cache with WebSocket data vs invalidate
    )

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def STATES_CACHE_ENABLED(self) -> bool:
        """Dynamic cache setting for states API"""
        try:
            from .ui_config import ui_config

            return ui_config.get_cache_setting("states")
        except ImportError:
            # Fallback if UI config not available
            return True

    @property
    def SERVICES_CACHE_ENABLED(self) -> bool:
        """Dynamic cache setting for services API"""
        try:
            from .ui_config import ui_config

            return ui_config.get_cache_setting("services")
        except ImportError:
            # Fallback if UI config not available
            return True

    @property
    def CONFIG_CACHE_ENABLED(self) -> bool:
        """Dynamic cache setting for config API"""
        try:
            from .ui_config import ui_config

            return ui_config.get_cache_setting("config")
        except ImportError:
            # Fallback if UI config not available
            return True

    @property
    def STATES_INDIVIDUAL_CACHE_ENABLED(self) -> bool:
        """Dynamic cache setting for individual state lookups"""
        try:
            from .ui_config import ui_config

            return ui_config.get_cache_setting("states_individual")
        except ImportError:
            # Fallback if UI config not available (disabled by default)
            return False

    @property
    def SERVICES_INDIVIDUAL_CACHE_ENABLED(self) -> bool:
        """Dynamic cache setting for individual service lookups"""
        try:
            from .ui_config import ui_config

            return ui_config.get_cache_setting("services_individual")
        except ImportError:
            # Fallback if UI config not available (disabled by default)
            return False


# Global settings instance
settings = Settings()

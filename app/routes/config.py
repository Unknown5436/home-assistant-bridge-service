import time
from fastapi import APIRouter, HTTPException, status
import structlog

from app.clients.ha_client import HomeAssistantClient
from app.models.schemas import ConfigResponse
from app.cache.manager import cache_manager, cached
from app.monitoring.metrics import metrics_collector

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/", response_model=ConfigResponse)
@cached("config", ttl=600)  # Cache for 10 minutes
async def get_config():
    """Get Home Assistant configuration."""
    try:
        client = HomeAssistantClient()
        config = await client.get_config()
        logger.info("Retrieved configuration")
        return config
    except Exception as e:
        logger.error("Failed to get config", error=str(e))
        metrics_collector.record_error("get_config_error", "/api/v1/config/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}",
        )


@router.get("/health")
async def get_health():
    """Get Home Assistant connection health."""
    try:
        client = HomeAssistantClient()
        is_connected = await client.check_connection()

        health_status = {
            "ha_connected": is_connected,
            "timestamp": time.time(),
            "status": "healthy" if is_connected else "unhealthy",
        }

        logger.info("Health check completed", connected=is_connected)
        return health_status

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        metrics_collector.record_error("health_check_error", "/api/v1/config/health")
        return {
            "ha_connected": False,
            "timestamp": time.time(),
            "status": "unhealthy",
            "error": str(e),
        }

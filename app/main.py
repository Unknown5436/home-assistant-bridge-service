import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config.settings import settings
from app.auth.middleware import auth_middleware
from app.monitoring.metrics import (
    metrics_middleware,
    get_metrics_response,
    metrics_collector,
)
from app.routes import states, services, config
from app.clients.websocket import HomeAssistantWebSocketClient

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global WebSocket client
websocket_client: HomeAssistantWebSocketClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global websocket_client

    # Startup
    logger.info("Starting Home Assistant Bridge Service")

    # Initialize WebSocket client if enabled
    if settings.WEBSOCKET_ENABLED:
        websocket_client = HomeAssistantWebSocketClient()
        connected = await websocket_client.connect()
        if connected:
            logger.info("WebSocket client connected")
            metrics_collector.set_websocket_connection_status(True)
        else:
            logger.warning("Failed to connect WebSocket client")
            metrics_collector.set_websocket_connection_status(False)

    # Set initial HA connection status
    try:
        from app.clients.ha_client import HomeAssistantClient

        async with HomeAssistantClient() as client:
            ha_connected = await client.check_connection()
            metrics_collector.set_ha_connection_status(ha_connected)
            logger.info("Home Assistant connection status", connected=ha_connected)
    except Exception as e:
        logger.error("Failed to check HA connection", error=str(e))
        metrics_collector.set_ha_connection_status(False)

    yield

    # Shutdown
    logger.info("Shutting down Home Assistant Bridge Service")

    if websocket_client:
        await websocket_client.disconnect()
        logger.info("WebSocket client disconnected")


# Create FastAPI application
app = FastAPI(
    title="Home Assistant Bridge Service",
    description="A secure FastAPI-based intermediary service for Home Assistant integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(auth_middleware)
app.middleware("http")(metrics_middleware)

# Include routers
app.include_router(states.router)
app.include_router(services.router)
app.include_router(config.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global websocket_client

    ha_connected = False
    websocket_connected = False

    try:
        from app.clients.ha_client import HomeAssistantClient

        async with HomeAssistantClient() as client:
            ha_connected = await client.check_connection()
    except Exception as e:
        logger.error("Health check HA connection failed", error=str(e))

    if websocket_client:
        websocket_connected = websocket_client.is_connected()

    return {
        "status": "healthy" if ha_connected else "degraded",
        "timestamp": time.time(),
        "version": "1.0.0",
        "ha_connected": ha_connected,
        "websocket_connected": websocket_connected,
        "metrics_enabled": settings.METRICS_ENABLED,
        "websocket_enabled": settings.WEBSOCKET_ENABLED,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.METRICS_ENABLED:
        return JSONResponse(status_code=404, content={"error": "Metrics disabled"})

    return get_metrics_response()


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    global websocket_client

    status_info = {
        "service": "Home Assistant Bridge",
        "version": "1.0.0",
        "timestamp": time.time(),
        "settings": {
            "ha_url": settings.HA_URL,
            "cache_ttl": settings.CACHE_TTL,
            "rate_limit_requests": settings.RATE_LIMIT_REQUESTS,
            "rate_limit_window": settings.RATE_LIMIT_WINDOW,
            "metrics_enabled": settings.METRICS_ENABLED,
            "websocket_enabled": settings.WEBSOCKET_ENABLED,
        },
        "connections": {"ha_connected": False, "websocket_connected": False},
    }

    # Check HA connection
    try:
        from app.clients.ha_client import HomeAssistantClient

        async with HomeAssistantClient() as client:
            status_info["connections"]["ha_connected"] = await client.check_connection()
    except Exception as e:
        logger.error("Status check HA connection failed", error=str(e))

    # Check WebSocket connection
    if websocket_client:
        status_info["connections"][
            "websocket_connected"
        ] = websocket_client.is_connected()

    return status_info


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "timestamp": time.time(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )

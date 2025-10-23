import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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


async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    )

    # Strict Transport Security (only for HTTPS)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global websocket_client

    # Startup
    logger.info("Starting Home Assistant Bridge Service")

    # Initialize WebSocket client if enabled
    if settings.WEBSOCKET_ENABLED:
        logger.info(
            "WebSocket client initialization starting",
            ws_url=settings.HA_URL.replace("http://", "ws://").replace(
                "https://", "wss://"
            )
            + "/api/websocket",
        )
        websocket_client = HomeAssistantWebSocketClient()
        connected = await websocket_client.connect()
        if connected:
            logger.info("WebSocket client connected successfully")
            metrics_collector.set_websocket_connection_status(True)
        else:
            logger.warning(
                "Initial WebSocket connection failed - will retry in background",
                reconnect_attempts=websocket_client.reconnect_attempts,
            )
            metrics_collector.set_websocket_connection_status(False)
            # Start background reconnection task
            asyncio.create_task(websocket_client._attempt_reconnect())

    # Set initial HA connection status
    try:
        from app.clients.ha_client import HomeAssistantClient

        client = HomeAssistantClient()
        ha_connected = await client.check_connection()
        metrics_collector.set_ha_connection_status(ha_connected)
        logger.info("Home Assistant connection status", connected=ha_connected)

        # Warm up caches if HA is connected
        if ha_connected:
            from app.cache.manager import cache_manager

            await cache_manager.warm_cache()

    except Exception as e:
        logger.error("Failed to check HA connection", error=str(e))
        metrics_collector.set_ha_connection_status(False)

    yield

    # Shutdown
    logger.info("Shutting down Home Assistant Bridge Service")

    if websocket_client:
        websocket_client.should_reconnect = False  # Stop reconnection attempts
        await websocket_client.disconnect()
        logger.info("WebSocket client disconnected")


# Create FastAPI application
app = FastAPI(
    title="Home Assistant Bridge Service",
    description="A secure FastAPI-based intermediary service for Home Assistant integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"]
)  # Configure appropriately for production
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
app.middleware("http")(security_headers_middleware)

# Include routers - order matters for route matching
app.include_router(states.router)
app.include_router(config.router)
app.include_router(services.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global websocket_client

    ha_connected = False
    websocket_info = None

    try:
        from app.clients.ha_client import HomeAssistantClient

        client = HomeAssistantClient()
        ha_connected = await client.check_connection()
    except Exception as e:
        logger.error("Health check HA connection failed", error=str(e))

    if websocket_client:
        websocket_info = {
            "connected": websocket_client.is_connected(),
            "reconnect_attempts": websocket_client.reconnect_attempts,
            "subscriptions": len(websocket_client.active_subscriptions),
        }

    return {
        "status": "healthy" if ha_connected else "degraded",
        "timestamp": time.time(),
        "version": "1.0.0",
        "ha_connected": ha_connected,
        "websocket": websocket_info,
        "metrics_enabled": settings.METRICS_ENABLED,
        "websocket_enabled": settings.WEBSOCKET_ENABLED,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.METRICS_ENABLED:
        return JSONResponse(status_code=404, content={"error": "Metrics disabled"})

    return get_metrics_response()


@app.get("/queue/status")
async def queue_status():
    """Priority queue status endpoint."""
    from app.queue.priority_queue import priority_queue

    stats = priority_queue.get_stats()
    return {"queue_status": "active", "stats": stats, "timestamp": time.time()}


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

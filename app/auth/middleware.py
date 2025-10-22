import time
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

# Rate limiting storage (in production, use Redis or similar)
rate_limit_storage: Dict[str, Dict[str, float]] = {}


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = None, window_seconds: int = None):
        self.max_requests = max_requests or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limit."""
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Clean old entries
        if key in rate_limit_storage:
            rate_limit_storage[key] = {
                timestamp: count
                for timestamp, count in rate_limit_storage[key].items()
                if float(timestamp) > window_start
            }
        else:
            rate_limit_storage[key] = {}

        # Count requests in current window
        current_requests = sum(rate_limit_storage[key].values())

        if current_requests >= self.max_requests:
            return False

        # Add current request
        timestamp_str = str(current_time)
        rate_limit_storage[key][timestamp_str] = (
            rate_limit_storage[key].get(timestamp_str, 0) + 1
        )

        return True


class APIKeyAuth(HTTPBearer):
    """API Key authentication scheme."""

    def __init__(self):
        super().__init__(auto_error=False)
        self.valid_keys = set(settings.API_KEYS)

    async def __call__(
        self, request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        """Validate API key from request."""
        credentials = await super().__call__(request)

        if not credentials:
            return None

        if credentials.credentials not in self.valid_keys:
            return None

        return credentials


# Global instances
api_key_auth = APIKeyAuth()
rate_limiter = RateLimiter()


async def authenticate_request(request: Request) -> str:
    """Authenticate request and return API key."""
    credentials = await api_key_auth(request)

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


async def check_rate_limit(request: Request, api_key: str):
    """Check rate limit for the request."""
    # Use API key + IP for rate limiting
    client_ip = request.client.host
    rate_limit_key = f"{api_key}:{client_ip}"

    if not rate_limiter.is_allowed(rate_limit_key):
        logger.warning("Rate limit exceeded", api_key=api_key, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(rate_limiter.window_seconds)},
        )


async def auth_middleware(request: Request, call_next):
    """Authentication and rate limiting middleware."""
    try:
        # Skip auth for health, metrics, docs, and test endpoints
        if request.url.path in [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/api/v1/services/test",
            "/status",
        ]:
            return await call_next(request)

        # Authenticate request
        api_key = await authenticate_request(request)

        # Check rate limit
        await check_rate_limit(request, api_key)

        # Add API key to request state for use in routes
        request.state.api_key = api_key

        response = await call_next(request)
        return response

    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.detail, "timestamp": time.time()},
        )
    except Exception as e:
        logger.error("Auth middleware error", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "timestamp": time.time()},
        )

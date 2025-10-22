import time
from typing import Dict, Any
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Request, Response
import structlog

logger = structlog.get_logger()


class MetricsCollector:
    """Prometheus metrics collector for the bridge service."""

    def __init__(self):
        # Request metrics
        self.request_count = Counter(
            "ha_bridge_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status_code"],
        )

        self.request_duration = Histogram(
            "ha_bridge_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
        )

        # Home Assistant connection metrics
        self.ha_connection_status = Gauge(
            "ha_bridge_ha_connection_status",
            "Home Assistant connection status (1=connected, 0=disconnected)",
        )

        self.websocket_connection_status = Gauge(
            "ha_bridge_websocket_connection_status",
            "WebSocket connection status (1=connected, 0=disconnected)",
        )

        # Cache metrics
        self.cache_hits = Counter(
            "ha_bridge_cache_hits_total", "Total cache hits", ["cache_name"]
        )

        self.cache_misses = Counter(
            "ha_bridge_cache_misses_total", "Total cache misses", ["cache_name"]
        )

        # Rate limiting metrics
        self.rate_limit_hits = Counter(
            "ha_bridge_rate_limit_hits_total", "Total rate limit hits", ["api_key"]
        )

        # Error metrics
        self.error_count = Counter(
            "ha_bridge_errors_total",
            "Total number of errors",
            ["error_type", "endpoint"],
        )

    def record_request(self, request: Request, status_code: int, duration: float):
        """Record request metrics."""
        method = request.method
        endpoint = request.url.path

        self.request_count.labels(
            method=method, endpoint=endpoint, status_code=str(status_code)
        ).inc()

        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def record_cache_hit(self, cache_name: str):
        """Record cache hit."""
        self.cache_hits.labels(cache_name=cache_name).inc()

    def record_cache_miss(self, cache_name: str):
        """Record cache miss."""
        self.cache_misses.labels(cache_name=cache_name).inc()

    def record_rate_limit_hit(self, api_key: str):
        """Record rate limit hit."""
        self.rate_limit_hits.labels(api_key=api_key).inc()

    def record_error(self, error_type: str, endpoint: str):
        """Record error."""
        self.error_count.labels(error_type=error_type, endpoint=endpoint).inc()

    def set_ha_connection_status(self, connected: bool):
        """Set Home Assistant connection status."""
        self.ha_connection_status.set(1 if connected else 0)

    def set_websocket_connection_status(self, connected: bool):
        """Set WebSocket connection status."""
        self.websocket_connection_status.set(1 if connected else 0)

    def get_metrics(self) -> bytes:
        """Get Prometheus metrics in text format."""
        return generate_latest()


# Global metrics collector instance
metrics_collector = MetricsCollector()


async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()

    try:
        response = await call_next(request)

        # Record metrics
        duration = time.time() - start_time
        metrics_collector.record_request(request, response.status_code, duration)

        return response

    except Exception as e:
        # Record error metrics
        duration = time.time() - start_time
        metrics_collector.record_request(request, 500, duration)
        metrics_collector.record_error(type(e).__name__, request.url.path)

        raise


def get_metrics_response() -> Response:
    """Get metrics response for /metrics endpoint."""
    metrics_data = metrics_collector.get_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

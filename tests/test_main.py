import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.clients.ha_client import HomeAssistantClient
from app.models.schemas import StateResponse, ServiceResponse

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint(self):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_endpoint(self):
        """Test metrics endpoint returns metrics."""
        response = client.get("/metrics")
        # Should return 200 or 404 depending on METRICS_ENABLED setting
        assert response.status_code in [200, 404]


class TestStatusEndpoint:
    """Test status endpoint."""

    def test_status_endpoint(self):
        """Test status endpoint returns detailed status."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "settings" in data
        assert "connections" in data


class TestAuthentication:
    """Test authentication middleware."""

    def test_protected_endpoint_without_auth(self):
        """Test that protected endpoints require authentication."""
        response = client.get("/api/v1/states/")
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_auth(self):
        """Test that invalid API key is rejected."""
        headers = {"Authorization": "Bearer invalid-key"}
        response = client.get("/api/v1/states/", headers=headers)
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_auth(self):
        """Test that valid API key is accepted."""
        headers = {"Authorization": "Bearer key1"}
        with patch.object(HomeAssistantClient, "get_states") as mock_get_states:
            mock_states = [
                {
                    "entity_id": "test.entity",
                    "state": "on",
                    "attributes": {},
                    "last_changed": "2023-01-01T00:00:00Z",
                    "last_updated": "2023-01-01T00:00:00Z",
                }
            ]
            mock_get_states.return_value = [
                StateResponse(**state) for state in mock_states
            ]

            response = client.get("/api/v1/states/", headers=headers)
            # Should not be 401, might be 500 due to HA connection issues
            assert response.status_code != 401


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiting(self):
        """Test that rate limiting works."""
        headers = {"Authorization": "Bearer key1"}

        # Make requests up to the limit
        for i in range(101):  # Assuming limit is 100
            response = client.get("/api/v1/states/", headers=headers)
            if response.status_code == 429:
                break

        # Should eventually hit rate limit
        assert response.status_code == 429


class TestHomeAssistantClient:
    """Test Home Assistant client."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client context manager."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = []
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            async with HomeAssistantClient() as client:
                states = await client.get_states()
                assert isinstance(states, list)

    @pytest.mark.asyncio
    async def test_get_states_error_handling(self):
        """Test error handling in get_states."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                Exception("Connection error")
            )

            async with HomeAssistantClient() as client:
                with pytest.raises(Exception, match="Failed to retrieve states"):
                    await client.get_states()


if __name__ == "__main__":
    pytest.main([__file__])

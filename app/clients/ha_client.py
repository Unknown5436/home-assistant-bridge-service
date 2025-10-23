import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from app.config.settings import settings
from app.models.schemas import StateResponse, ServiceResponse, ConfigResponse
from app.queue.priority_queue import priority_queue, Priority

logger = structlog.get_logger()

# Global client instance for connection reuse
_global_client: Optional[httpx.AsyncClient] = None


class HomeAssistantClient:
    """Home Assistant API client for REST operations."""

    def __init__(self):
        self.base_url = settings.HA_URL.rstrip("/")
        self.token = settings.HA_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.client: Optional[httpx.AsyncClient] = None

        # Connection limits for better performance
        self.limits = httpx.Limits(
            max_connections=20, max_keepalive_connections=10, keepalive_expiry=30.0
        )

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=self.limits,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a client instance."""
        global _global_client

        if self.client:
            return self.client

        if _global_client is None:
            _global_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=httpx.Timeout(30.0, connect=5.0),
                limits=self.limits,
            )

        return _global_client

    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant."""
        try:
            client = await self._get_client()
            response = await client.get("/api/states")
            response.raise_for_status()

            states = response.json()  # Return raw JSON
            logger.info("Retrieved all states", count=len(states))
            return states

        except httpx.HTTPError as e:
            logger.error("Failed to get states", error=str(e))
            raise Exception(f"Failed to retrieve states: {e}")

    async def get_state(self, entity_id: str) -> StateResponse:
        """Get specific entity state from Home Assistant."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/states/{entity_id}")
            response.raise_for_status()

            state_data = response.json()
            logger.info("Retrieved state", entity_id=entity_id)
            return StateResponse(**state_data)

        except httpx.HTTPError as e:
            logger.error("Failed to get state", entity_id=entity_id, error=str(e))
            raise Exception(f"Failed to retrieve state for {entity_id}: {e}")

    async def set_state(
        self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None
    ) -> StateResponse:
        """Set entity state in Home Assistant."""
        try:
            payload = {"state": state}
            if attributes:
                payload["attributes"] = attributes

            client = await self._get_client()
            response = await client.post(f"/api/states/{entity_id}", json=payload)
            response.raise_for_status()

            state_data = response.json()
            logger.info("Set state", entity_id=entity_id, state=state)
            return StateResponse(**state_data)

        except httpx.HTTPError as e:
            logger.error("Failed to set state", entity_id=entity_id, error=str(e))
            raise Exception(f"Failed to set state for {entity_id}: {e}")

    async def call_service(
        self, domain: str, service: str, service_data: Optional[Dict[str, Any]] = None
    ) -> ServiceResponse:
        """Call a Home Assistant service."""
        try:
            payload = {}
            if service_data:
                payload = service_data

            client = await self._get_client()
            response = await client.post(
                f"/api/services/{domain}/{service}", json=payload
            )
            response.raise_for_status()

            logger.info("Called service", domain=domain, service=service)
            logger.debug("Response status", status_code=response.status_code)
            logger.debug("Response content", content=response.text)

            # Handle empty response content
            response_data = None
            if response.content:
                try:
                    response_data = response.json()
                    logger.debug("Parsed JSON response", data=response_data)
                except Exception as e:
                    logger.debug(
                        "Failed to parse JSON", error=str(e), raw_content=response.text
                    )
                    response_data = {"raw_response": response.text}
            else:
                # Handle empty response - Home Assistant often returns empty arrays for service calls
                response_data = []
                logger.debug("Empty response, setting data to empty array")

            return ServiceResponse(
                success=True,
                message=f"Service {domain}.{service} called successfully",
                data=response_data,
            )

        except httpx.HTTPError as e:
            logger.error(
                "Failed to call service", domain=domain, service=service, error=str(e)
            )
            return ServiceResponse(
                success=False, message=f"Failed to call service {domain}.{service}: {e}"
            )

    async def get_services(self) -> Dict[str, Any]:
        """Get available services from Home Assistant."""
        try:
            logger.info(
                "Attempting to retrieve services from HA", base_url=self.base_url
            )

            client = await self._get_client()
            logger.info("Making GET request to /api/services")
            response = await client.get("/api/services")
            logger.info("Received response", status_code=response.status_code)

            response.raise_for_status()

            services = response.json()
            logger.info(
                "Successfully parsed services JSON",
                count=len(services),
                service_type=type(services).__name__,
            )

            # Handle both list and dict responses from HA API
            if isinstance(services, list):
                logger.info("Services returned as list - converting to dict format")
                # Convert list to dict format for consistency
                services_dict = {}
                for service in services:
                    if isinstance(service, dict) and "domain" in service:
                        domain = service["domain"]
                        if domain not in services_dict:
                            services_dict[domain] = {}
                        if "services" in service:
                            services_dict[domain].update(service["services"])
                services = services_dict
                logger.info(
                    "Converted services to dict format", domains=list(services.keys())
                )

            return services

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error getting services",
                status_code=e.response.status_code,
                error=str(e),
                response_text=e.response.text[:200],
            )
            raise Exception(
                f"Failed to retrieve services (HTTP {e.response.status_code}): {e}"
            )
        except httpx.HTTPError as e:
            logger.error(
                "Connection error getting services",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise Exception(f"Failed to retrieve services: {e}")
        except Exception as e:
            logger.error(
                "Unexpected error getting services",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise Exception(f"Failed to retrieve services: {e}")

    async def get_config(self) -> ConfigResponse:
        """Get Home Assistant configuration."""
        try:
            client = await self._get_client()
            response = await client.get("/api/config")
            response.raise_for_status()

            config_data = response.json()
            logger.info("Retrieved configuration")
            return ConfigResponse(**config_data)

        except httpx.HTTPError as e:
            logger.error("Failed to get config", error=str(e))
            raise Exception(f"Failed to retrieve configuration: {e}")

    async def get_state_priority(
        self, entity_id: str, priority: Priority = Priority.NORMAL
    ) -> StateResponse:
        """Get specific entity state with priority processing."""
        return await priority_queue.add_request(
            func=self.get_state, args=(entity_id,), priority=priority, timeout=10.0
        )

    async def get_states_priority(
        self, priority: Priority = Priority.NORMAL
    ) -> List[Dict[str, Any]]:
        """Get all entity states with priority processing."""
        return await priority_queue.add_request(
            func=self.get_states, priority=priority, timeout=30.0
        )

    async def call_service_priority(
        self,
        domain: str,
        service: str,
        service_data: Optional[Dict[str, Any]] = None,
        priority: Priority = Priority.HIGH,
    ) -> ServiceResponse:
        """Call a Home Assistant service with priority processing."""
        return await priority_queue.add_request(
            func=self.call_service,
            args=(domain, service, service_data),
            priority=priority,
            timeout=15.0,
        )

    async def check_connection(self) -> bool:
        """Check if Home Assistant is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/api/")
            return response.status_code == 200
        except Exception as e:
            logger.warning("HA connection check failed", error=str(e))
            return False

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from app.config.settings import settings
from app.models.schemas import StateResponse, ServiceResponse, ConfigResponse

logger = structlog.get_logger()


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

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, timeout=30.0
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant."""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url, headers=self.headers, timeout=30.0
                )

            response = await self.client.get("/api/states")
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
            if not self.client:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url, headers=self.headers, timeout=30.0
                )

            response = await self.client.get(f"/api/states/{entity_id}")
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

            if not self.client:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url, headers=self.headers, timeout=30.0
                )

            response = await self.client.post(f"/api/states/{entity_id}", json=payload)
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

            if not self.client:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url, headers=self.headers, timeout=30.0
                )

            response = await self.client.post(
                f"/api/services/{domain}/{service}", json=payload
            )
            response.raise_for_status()

            logger.info("Called service", domain=domain, service=service)
            return ServiceResponse(
                success=True,
                message=f"Service {domain}.{service} called successfully",
                data=response.json() if response.content else None,
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

            if not self.client:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url, headers=self.headers, timeout=30.0
                )
                logger.info("Created new httpx client for services request")

            # Try the services endpoint
            logger.info("Making GET request to /api/services")
            response = await self.client.get("/api/services")
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
            if not self.client:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url, headers=self.headers, timeout=30.0
                )

            response = await self.client.get("/api/config")
            response.raise_for_status()

            config_data = response.json()
            logger.info("Retrieved configuration")
            return ConfigResponse(**config_data)

        except httpx.HTTPError as e:
            logger.error("Failed to get config", error=str(e))
            raise Exception(f"Failed to retrieve configuration: {e}")

    async def check_connection(self) -> bool:
        """Check if Home Assistant is reachable."""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url, headers=self.headers, timeout=30.0
                )

            response = await self.client.get("/api/")
            return response.status_code == 200
        except Exception as e:
            logger.error("Connection check failed", error=str(e))
            return False

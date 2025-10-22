from typing import Dict, Any, Optional
from pydantic import BaseModel


class StateResponse(BaseModel):
    """Home Assistant state response model."""

    entity_id: str
    state: str
    attributes: Dict[str, Any]
    last_changed: str
    last_updated: str
    context: Optional[Dict[str, Any]] = None


class ServiceCallRequest(BaseModel):
    """Service call request model."""

    entity_id: Optional[str] = None
    service_data: Optional[Dict[str, Any]] = None


class ServiceResponse(BaseModel):
    """Service call response model."""

    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ConfigResponse(BaseModel):
    """Home Assistant configuration response model."""

    latitude: float
    longitude: float
    elevation: int
    unit_system: Dict[str, str]
    location_name: str
    time_zone: str
    components: list
    config_dir: str
    whitelist_external_dirs: list
    version: str
    safe_mode: bool
    state: str


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    version: str
    ha_connected: bool
    websocket_connected: bool


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None
    timestamp: str

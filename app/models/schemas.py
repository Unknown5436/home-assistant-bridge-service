from typing import Dict, Any, Optional
from pydantic import BaseModel


class StateResponse(BaseModel):
    """Home Assistant state response model."""

    entity_id: str
    state: str
    attributes: Dict[str, Any] = {}
    last_changed: str
    last_updated: str
    last_reported: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"  # Allow extra fields from HA


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

    # Core fields that should always exist
    version: str

    # Common but potentially optional fields
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[int] = None
    unit_system: Optional[Dict[str, str]] = None
    location_name: Optional[str] = None
    time_zone: Optional[str] = None
    components: Optional[list] = None
    config_dir: Optional[str] = None

    # Additional fields from actual HA response
    allowlist_external_dirs: Optional[list] = None
    allowlist_external_urls: Optional[list] = None
    config_source: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    debug: Optional[bool] = None
    external_url: Optional[str] = None
    internal_url: Optional[str] = None
    language: Optional[str] = None
    radius: Optional[int] = None
    recovery_mode: Optional[bool] = None
    safe_mode: Optional[bool] = None
    state: Optional[str] = None
    whitelist_external_dirs: Optional[list] = None

    class Config:
        extra = "allow"  # Allow extra fields from HA


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

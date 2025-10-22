from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
import structlog

from app.clients.ha_client import HomeAssistantClient
from app.models.schemas import ServiceCallRequest, ServiceResponse
from app.cache.manager import cache_manager, cached
from app.monitoring.metrics import metrics_collector

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/services", tags=["services"])


@router.get("/", response_model=Dict[str, Any])
@cached("services", ttl=300)  # Cache for 5 minutes
async def get_services():
    """Get available services from Home Assistant."""
    try:
        async with HomeAssistantClient() as client:
            services = await client.get_services()
            logger.info("Retrieved services", count=len(services))
            return services
    except Exception as e:
        logger.error("Failed to get services", error=str(e))
        metrics_collector.record_error("get_services_error", "/api/v1/services/")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve services: {str(e)}",
        )


@router.post("/{domain}/{service}", response_model=ServiceResponse)
async def call_service(
    domain: str, service: str, service_data: ServiceCallRequest = None
):
    """Call a Home Assistant service."""
    try:
        data = service_data.service_data if service_data else None

        async with HomeAssistantClient() as client:
            result = await client.call_service(domain, service, data)

            # Invalidate relevant caches
            cache_manager.invalidate_pattern("states", domain)

            logger.info("Called service", domain=domain, service=service)
            return result

    except Exception as e:
        logger.error(
            "Failed to call service", domain=domain, service=service, error=str(e)
        )
        metrics_collector.record_error(
            "call_service_error", f"/api/v1/services/{domain}/{service}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to call service {domain}.{service}: {str(e)}",
        )


@router.post("/batch")
async def batch_call_services(service_calls: List[Dict[str, Any]]):
    """Batch call multiple services."""
    try:
        results = []
        errors = []

        async with HomeAssistantClient() as client:
            for call in service_calls:
                domain = call.get("domain")
                service = call.get("service")
                service_data = call.get("service_data")

                if not domain or not service:
                    errors.append(f"Invalid service call: {call}")
                    continue

                try:
                    result = await client.call_service(domain, service, service_data)
                    results.append(
                        {
                            "domain": domain,
                            "service": service,
                            "success": result.success,
                            "result": result,
                        }
                    )

                    # Invalidate relevant caches
                    cache_manager.invalidate_pattern("states", domain)

                except Exception as e:
                    errors.append(f"Failed to call {domain}.{service}: {str(e)}")
                    results.append(
                        {
                            "domain": domain,
                            "service": service,
                            "success": False,
                            "error": str(e),
                        }
                    )

        logger.info(
            "Batch service calls completed", success=len(results), errors=len(errors)
        )

        return {
            "results": results,
            "errors": errors,
            "success_count": len([r for r in results if r["success"]]),
            "error_count": len(errors),
        }

    except Exception as e:
        logger.error("Failed to batch call services", error=str(e))
        metrics_collector.record_error(
            "batch_call_services_error", "/api/v1/services/batch"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch call services: {str(e)}",
        )


@router.get("/{domain}", response_model=Dict[str, Any])
@cached("services", ttl=300)
async def get_domain_services(domain: str):
    """Get services for a specific domain."""
    try:
        async with HomeAssistantClient() as client:
            all_services = await client.get_services()
            domain_services = all_services.get(domain, {})

            logger.info(
                "Retrieved domain services", domain=domain, count=len(domain_services)
            )
            return domain_services

    except Exception as e:
        logger.error("Failed to get domain services", domain=domain, error=str(e))
        metrics_collector.record_error(
            "get_domain_services_error", f"/api/v1/services/{domain}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve services for domain {domain}: {str(e)}",
        )

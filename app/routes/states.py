from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
import structlog
import asyncio

from app.clients.ha_client import HomeAssistantClient
from app.models.schemas import (
    StateResponse,
    ServiceCallRequest,
    ServiceResponse,
    BatchStatesRequest,
)
from app.cache.manager import cache_manager, cached
from app.monitoring.metrics import metrics_collector
from app.config.settings import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/states", tags=["states"])


@router.get("/simple")
async def simple_test():
    """Simple test endpoint without any decorators."""
    return {"message": "Simple test endpoint works", "status": "success"}


def get_all_states_impl():
    """Implementation of get_all_states without decorator"""

    async def _get_all_states():
        """Get all entity states from Home Assistant."""
        try:
            client = HomeAssistantClient()
            states = await client.get_states()
            logger.info("Retrieved all states", count=len(states))
            return states
        except Exception as e:
            logger.error(
                "Failed to get states", error=str(e), error_type=type(e).__name__
            )
            metrics_collector.record_error("get_states_error", "/api/v1/states/")
            # Return detailed error information
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "message": f"Failed to retrieve states: {str(e)}",
                },
            )

    return _get_all_states


# Apply conditional caching based on UI settings
if settings.STATES_CACHE_ENABLED:

    @router.get("/all")
    @cached("states", ttl=settings.STATES_CACHE_TTL)
    async def get_all_states():
        return await get_all_states_impl()()

else:

    @router.get("/all")
    async def get_all_states():
        return await get_all_states_impl()()


def get_state_impl():
    """Implementation of get_state without decorator"""

    async def _get_state(entity_id: str):
        """Get specific entity state from Home Assistant."""
        # Validate entity ID format (should be domain.entity_name)
        if "." not in entity_id or entity_id.count(".") != 1:
            logger.warning("Invalid entity ID format", entity_id=entity_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invalid entity ID format: {entity_id}. Expected format: domain.entity_name",
            )

        try:
            client = HomeAssistantClient()
            state = await client.get_state(entity_id)
            logger.info("Retrieved state", entity_id=entity_id)
            return state
        except Exception as e:
            logger.error("Failed to get state", entity_id=entity_id, error=str(e))
            metrics_collector.record_error(
                "get_state_error", f"/api/v1/states/{entity_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve state for {entity_id}: {str(e)}",
            )

    return _get_state


# Apply conditional caching based on UI settings
if settings.STATES_INDIVIDUAL_CACHE_ENABLED:

    @router.get("/{entity_id}", response_model=StateResponse)
    @cached("state", ttl=settings.STATES_CACHE_TTL)
    async def get_state(entity_id: str):
        return await get_state_impl()(entity_id)

else:

    @router.get("/{entity_id}", response_model=StateResponse)
    async def get_state(entity_id: str):
        return await get_state_impl()(entity_id)


@router.post("/batch")
async def get_batch_states(request: BatchStatesRequest):
    """Get multiple entity states in a single request."""
    try:
        entity_ids = request.entity_ids

        if not entity_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No entity IDs provided"
            )

        client = HomeAssistantClient()
        results = {}
        errors = {}

        # Use asyncio.gather for concurrent requests
        tasks = []
        for entity_id in entity_ids:
            # Validate entity ID format
            if "." not in entity_id or entity_id.count(".") != 1:
                errors[entity_id] = f"Invalid entity ID format: {entity_id}"
                continue

            task = client.get_state(entity_id)
            tasks.append((entity_id, task))

        # Execute all requests concurrently
        if tasks:
            entity_ids_list, task_list = zip(*tasks)
            responses = await asyncio.gather(*task_list, return_exceptions=True)

            for entity_id, response in zip(entity_ids_list, responses):
                if isinstance(response, Exception):
                    errors[entity_id] = str(response)
                else:
                    # Convert StateResponse object to dictionary for JSON serialization
                    results[entity_id] = response.model_dump()

        logger.info(
            "Batch states request completed",
            requested=len(entity_ids),
            successful=len(results),
            errors=len(errors),
        )

        return {
            "results": results,
            "errors": errors,
            "success_count": len(results),
            "error_count": len(errors),
            "total_requested": len(entity_ids),
        }

    except Exception as e:
        logger.error(
            "Failed to get batch states", error=str(e), error_type=type(e).__name__
        )
        metrics_collector.record_error("get_batch_states_error", "/api/v1/states/batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batch states: {str(e)}",
        )


@router.post("/{entity_id}", response_model=StateResponse)
async def set_state(entity_id: str, state_data: Dict[str, Any]):
    """Set entity state in Home Assistant."""
    try:
        state = state_data.get("state")
        attributes = state_data.get("attributes")

        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State value is required",
            )

        client = HomeAssistantClient()
        result = await client.set_state(entity_id, state, attributes)

        # Invalidate cache for this entity
        cache_manager.invalidate_pattern("states", entity_id)

        logger.info("Set state", entity_id=entity_id, state=state)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to set state", entity_id=entity_id, error=str(e))
        metrics_collector.record_error("set_state_error", f"/api/v1/states/{entity_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set state for {entity_id}: {str(e)}",
        )


@router.get("/group/{group_id}")
@cached("states", ttl=30)  # Cache for 30 seconds
async def get_group_states(group_id: str):
    """Get states for all entities in a group."""
    try:
        client = HomeAssistantClient()
        # Get all states and filter by group
        all_states = await client.get_states()
        # Filter by entity_id containing group_id
        group_states = [
            state for state in all_states if group_id in state.get("entity_id", "")
        ]

        logger.info(
            "Retrieved group states", group_id=group_id, count=len(group_states)
        )
        return group_states

    except Exception as e:
        logger.error("Failed to get group states", group_id=group_id, error=str(e))
        metrics_collector.record_error(
            "get_group_states_error", f"/api/v1/states/group/{group_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve states for group {group_id}: {str(e)}",
        )

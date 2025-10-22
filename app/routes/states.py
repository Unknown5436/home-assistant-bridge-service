from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
import structlog

from app.clients.ha_client import HomeAssistantClient
from app.models.schemas import StateResponse, ServiceCallRequest, ServiceResponse
from app.cache.manager import cache_manager, cached
from app.monitoring.metrics import metrics_collector

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/states", tags=["states"])


@router.get("/simple")
async def simple_test():
    """Simple test endpoint without any decorators."""
    return {"message": "Simple test endpoint works", "status": "success"}


@router.get("/all")
async def get_all_states():
    """Get all entity states from Home Assistant."""
    try:
        client = HomeAssistantClient()
        states = await client.get_states()
        logger.info("Retrieved all states", count=len(states))
        return states
    except Exception as e:
        logger.error("Failed to get states", error=str(e), error_type=type(e).__name__)
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


@router.get("/{entity_id}", response_model=StateResponse)
async def get_state(entity_id: str):
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
        metrics_collector.record_error("get_state_error", f"/api/v1/states/{entity_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve state for {entity_id}: {str(e)}",
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


@router.post("/group/{group_id}/batch")
async def batch_update_group_states(group_id: str, updates: List[Dict[str, Any]]):
    """Batch update states for entities in a group."""
    try:
        results = []
        errors = []

        client = HomeAssistantClient()
        for update in updates:
            entity_id = update.get("entity_id")
            state = update.get("state")
            attributes = update.get("attributes")

            if not entity_id or not state:
                errors.append(f"Invalid update data: {update}")
                continue

            try:
                result = await client.set_state(entity_id, state, attributes)
                results.append(
                    {"entity_id": entity_id, "success": True, "state": result}
                )

                # Invalidate cache for this entity
                cache_manager.invalidate_pattern("states", entity_id)

            except Exception as e:
                errors.append(f"Failed to update {entity_id}: {str(e)}")
                results.append(
                    {"entity_id": entity_id, "success": False, "error": str(e)}
                )

        logger.info(
            "Batch update completed",
            group_id=group_id,
            success=len(results),
            errors=len(errors),
        )

        return {
            "group_id": group_id,
            "results": results,
            "errors": errors,
            "success_count": len([r for r in results if r["success"]]),
            "error_count": len(errors),
        }

    except Exception as e:
        logger.error(
            "Failed to batch update group states", group_id=group_id, error=str(e)
        )
        metrics_collector.record_error(
            "batch_update_error", f"/api/v1/states/group/{group_id}/batch"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch update states for group {group_id}: {str(e)}",
        )

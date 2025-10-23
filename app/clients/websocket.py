import asyncio
import json
import random
import websockets
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class HomeAssistantWebSocketClient:
    """WebSocket client for real-time Home Assistant updates."""

    def __init__(self):
        self.ws_url = (
            settings.HA_URL.replace("http://", "ws://").replace("https://", "wss://")
            + "/api/websocket"
        )
        self.token = settings.HA_TOKEN
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.message_id = 1
        self.subscriptions: Dict[int, Callable] = {}
        self.active_subscriptions: Dict[str, int] = {}  # Track all subscriptions by event_type
        self.reconnect_attempts = 0
        self.should_reconnect = True

    async def connect(self) -> bool:
        """Connect to Home Assistant WebSocket."""
        try:
            logger.info("Attempting WebSocket connection", ws_url=self.ws_url)
            
            # Connect without Authorization header (HA WebSocket doesn't use it)
            self.websocket = await websockets.connect(
                self.ws_url, ping_interval=20, ping_timeout=10
            )
            logger.debug("WebSocket connection established, waiting for auth_required")

            # Wait for auth_required message
            auth_required = await self.websocket.recv()
            auth_data = json.loads(auth_required)
            logger.debug("Received auth message", message_type=auth_data.get("type"))

            if auth_data.get("type") == "auth_required":
                # Send auth message with token
                logger.debug("Sending authentication token")
                await self.websocket.send(
                    json.dumps({"type": "auth", "access_token": self.token})
                )

                # Wait for auth result
                auth_result = await self.websocket.recv()
                result_data = json.loads(auth_result)
                logger.debug("Received auth result", result_type=result_data.get("type"))

                if result_data.get("type") == "auth_ok":
                    self.connected = True
                    self.reconnect_attempts = 0
                    logger.info("WebSocket connected and authenticated successfully")

                    # Update metrics
                    try:
                        from app.monitoring.metrics import metrics_collector

                        metrics_collector.set_websocket_connection_status(True)
                    except ImportError:
                        pass

                    # Start message handler
                    asyncio.create_task(self._message_handler())

                    # Subscribe to events (no callbacks to avoid recursion)
                    await self.subscribe_events("state_changed")
                    await self.subscribe_events("service_registered")
                    await self.subscribe_events("service_removed")

                    return True
                else:
                    logger.error("WebSocket authentication failed", result=result_data)
                    return False
            else:
                logger.error("Expected auth_required message", received=auth_data)
                return False

        except Exception as e:
            logger.error(
                "WebSocket connection failed", 
                error=str(e), 
                error_type=type(e).__name__,
                ws_url=self.ws_url,
                has_token=bool(self.token)
            )
            return False

    async def disconnect(self):
        """Disconnect from Home Assistant WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("WebSocket disconnected")

    async def subscribe_events(
        self, event_type: str = "state_changed", callback: Optional[Callable] = None
    ) -> int:
        """Subscribe to Home Assistant events."""
        if not self.connected:
            raise Exception("WebSocket not connected")

        message_id = self.message_id
        self.message_id += 1

        subscribe_message = {
            "id": message_id,
            "type": "subscribe_events",
            "event_type": event_type,
        }

        await self.websocket.send(json.dumps(subscribe_message))

        if callback:
            self.subscriptions[message_id] = callback
        
        # Track all subscriptions (not just ones with callbacks)
        self.active_subscriptions[event_type] = message_id

        logger.info(
            "Subscribed to events", 
            event_type=event_type, 
            message_id=message_id,
            total_subscriptions=len(self.active_subscriptions)
        )
        return message_id

    async def subscribe_states(self, callback: Optional[Callable] = None) -> int:
        """Subscribe to state changes."""
        return await self.subscribe_events("state_changed", callback)

    async def get_states(self) -> Dict[str, Any]:
        """Get current states via WebSocket."""
        if not self.connected:
            raise Exception("WebSocket not connected")

        message_id = self.message_id
        self.message_id += 1

        get_states_message = {"id": message_id, "type": "get_states"}

        await self.websocket.send(json.dumps(get_states_message))

        # Wait for response
        response = await self._wait_for_response(message_id)
        return response.get("result", [])

    async def call_service(
        self, domain: str, service: str, service_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call service via WebSocket."""
        if not self.connected:
            raise Exception("WebSocket not connected")

        message_id = self.message_id
        self.message_id += 1

        call_service_message = {
            "id": message_id,
            "type": "call_service",
            "domain": domain,
            "service": service,
        }

        if service_data:
            call_service_message["service_data"] = service_data

        await self.websocket.send(json.dumps(call_service_message))

        # Wait for response
        response = await self._wait_for_response(message_id)
        return response

    async def _wait_for_response(
        self, message_id: int, timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Wait for a specific response message."""
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                data = json.loads(message)

                if data.get("id") == message_id:
                    return data
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Error waiting for response", error=str(e))
                break

        raise Exception(f"Timeout waiting for response to message {message_id}")

    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        logger.info("WebSocket message handler started")
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")

                    logger.debug("Received WebSocket message", message_type=message_type)

                    if message_type == "event":
                        await self._handle_event(data)
                    elif message_type == "result":
                        # Handle direct responses (already handled by _wait_for_response)
                        logger.debug("Received result message", message_id=data.get("id"), success=data.get("success"))
                    elif message_type == "pong":
                        # Handle pong responses
                        pass
                    else:
                        logger.debug(
                            "Unhandled message type", type=message_type, data=data
                        )

                except json.JSONDecodeError as e:
                    logger.error("Failed to parse WebSocket message", error=str(e))
                except Exception as e:
                    logger.error("Error handling WebSocket message", error=str(e))

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False

            # Update metrics
            try:
                from app.monitoring.metrics import metrics_collector

                metrics_collector.set_websocket_connection_status(False)
            except ImportError:
                pass

            # Attempt reconnection if enabled
            if self.should_reconnect:
                await self._attempt_reconnect()
        except Exception as e:
            logger.error("WebSocket message handler error", error=str(e))
            self.connected = False

            # Update metrics
            try:
                from app.monitoring.metrics import metrics_collector

                metrics_collector.set_websocket_connection_status(False)
            except ImportError:
                pass

    async def _handle_event(self, event_data: Dict[str, Any]):
        """Handle incoming events."""
        event_type = event_data.get("event", {}).get("event_type")

        if event_type == "state_changed":
            await self._handle_state_changed(event_data)
        else:
            logger.debug("Unhandled event type", event_type=event_type)

    async def _handle_state_changed(self, event_data: Dict[str, Any]):
        """Handle state change events with smart cache update or invalidation."""
        event = event_data.get("event", {})
        entity_id = event.get("data", {}).get("entity_id")
        new_state = event.get("data", {}).get("new_state")
        old_state = event.get("data", {}).get("old_state")

        if not entity_id or not new_state:
            return

        # Apply entity filters if enabled
        if settings.WEBSOCKET_FILTER_ENABLED:
            if not self._should_process_entity(entity_id):
                logger.debug("Entity filtered out", entity_id=entity_id)
                return

        from app.cache.manager import cache_manager

        if settings.WEBSOCKET_UPDATE_CACHE:
            # Update cache with new state data (faster, reduces HA load)
            try:
                # Update specific entity cache with WebSocket state data
                # Format matches what REST API returns (StateResponse)
                cache_key = f"get_state:{entity_id}"
                cache_manager.set("states", cache_key, new_state)

                logger.info(
                    "Cache updated from WebSocket",
                    entity_id=entity_id,
                    old_state=old_state.get("state") if old_state else None,
                    new_state=new_state.get("state"),
                    action="update",
                )
            except Exception as e:
                # Fall back to invalidation if update fails
                logger.warning(
                    "Failed to update cache, falling back to invalidation",
                    entity_id=entity_id,
                    error=str(e),
                )
                cache_manager.delete("states", f"get_state:{entity_id}")
        else:
            # Traditional invalidation - forces next API call to fetch fresh data
            cache_manager.delete("states", f"get_state:{entity_id}")

            logger.info(
                "Cache invalidated for state change",
                entity_id=entity_id,
                old_state=old_state.get("state") if old_state else None,
                new_state=new_state.get("state"),
                action="invalidate",
            )

        # Always invalidate all states cache (too complex to update incrementally)
        cache_manager.delete("states", "get_all_states")

        # Invalidate group caches that might contain this entity
        domain = entity_id.split(".")[0]
        cache_manager.invalidate_pattern("states", f"group:{domain}")

    async def _handle_service_event(self, event_data: Dict[str, Any]):
        """Handle service_registered and service_removed events."""
        from app.cache.manager import cache_manager

        event_type = event_data.get("event", {}).get("event_type")
        domain = event_data.get("event", {}).get("data", {}).get("domain")
        service = event_data.get("event", {}).get("data", {}).get("service")

        # Invalidate entire services cache (services change rarely)
        cache_manager.clear("services")

        logger.info(
            "Service cache invalidated",
            event_type=event_type,
            domain=domain,
            service=service,
        )

    def _should_process_entity(self, entity_id: str) -> bool:
        """Check if entity should be processed based on filters."""
        domain = entity_id.split(".")[0]

        # Check exclude list first
        if domain in settings.WEBSOCKET_EXCLUDE_DOMAINS:
            return False

        # If entity filters specified, check if entity matches
        if settings.WEBSOCKET_ENTITY_FILTERS:
            return any(
                entity_id.startswith(f) for f in settings.WEBSOCKET_ENTITY_FILTERS
            )

        # No filters = process all (except excluded domains)
        return True

    async def _attempt_reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        max_attempts = settings.WEBSOCKET_RECONNECT_MAX_ATTEMPTS

        # Check if we should stop reconnecting
        if max_attempts > 0 and self.reconnect_attempts >= max_attempts:
            logger.error(
                "Max reconnection attempts reached", attempts=self.reconnect_attempts
            )
            return

        self.reconnect_attempts += 1

        # Exponential backoff with jitter
        base_delay = min(
            2**self.reconnect_attempts, settings.WEBSOCKET_RECONNECT_MAX_DELAY
        )
        jitter = random.uniform(0, 0.1 * base_delay)
        wait_time = base_delay + jitter

        logger.warning(
            "Attempting to reconnect",
            attempt=self.reconnect_attempts,
            wait_time=round(wait_time, 2),
            note="Cache will continue via TTL during reconnection",
        )

        await asyncio.sleep(wait_time)

        success = await self.connect()
        if not success and self.should_reconnect:
            await self._attempt_reconnect()
        elif success:
            logger.info(
                "Reconnected successfully", after_attempts=self.reconnect_attempts
            )

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.connected and self.websocket is not None

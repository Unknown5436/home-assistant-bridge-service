import asyncio
import json
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
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def connect(self) -> bool:
        """Connect to Home Assistant WebSocket."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.websocket = await websockets.connect(
                self.ws_url, extra_headers=headers, ping_interval=20, ping_timeout=10
            )

            # Wait for auth result
            auth_result = await self.websocket.recv()
            auth_data = json.loads(auth_result)

            if auth_data.get("type") == "auth_ok":
                self.connected = True
                self.reconnect_attempts = 0
                logger.info("WebSocket connected successfully")

                # Start message handler
                asyncio.create_task(self._message_handler())
                return True
            else:
                logger.error("WebSocket authentication failed", result=auth_data)
                return False

        except Exception as e:
            logger.error("WebSocket connection failed", error=str(e))
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

        logger.info(
            "Subscribed to events", event_type=event_type, message_id=message_id
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
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")

                    if message_type == "event":
                        await self._handle_event(data)
                    elif message_type == "result":
                        # Handle direct responses (already handled by _wait_for_response)
                        pass
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
            await self._attempt_reconnect()
        except Exception as e:
            logger.error("WebSocket message handler error", error=str(e))
            self.connected = False

    async def _handle_event(self, event_data: Dict[str, Any]):
        """Handle incoming events."""
        event_type = event_data.get("event", {}).get("event_type")

        if event_type == "state_changed":
            await self._handle_state_changed(event_data)
        else:
            logger.debug("Unhandled event type", event_type=event_type)

    async def _handle_state_changed(self, event_data: Dict[str, Any]):
        """Handle state change events."""
        event = event_data.get("event", {})
        entity_id = event.get("data", {}).get("entity_id")
        new_state = event.get("data", {}).get("new_state")

        if entity_id and new_state:
            logger.info(
                "State changed", entity_id=entity_id, state=new_state.get("state")
            )

            # Notify subscribers
            for callback in self.subscriptions.values():
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_data)
                    else:
                        callback(event_data)
                except Exception as e:
                    logger.error("Error in state change callback", error=str(e))

    async def _attempt_reconnect(self):
        """Attempt to reconnect to WebSocket."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return

        self.reconnect_attempts += 1
        wait_time = min(2**self.reconnect_attempts, 30)  # Exponential backoff, max 30s

        logger.info(
            "Attempting to reconnect",
            attempt=self.reconnect_attempts,
            wait_time=wait_time,
        )
        await asyncio.sleep(wait_time)

        success = await self.connect()
        if not success:
            await self._attempt_reconnect()

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.connected and self.websocket is not None

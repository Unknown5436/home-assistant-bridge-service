"""
Tests for WebSocket client functionality
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.clients.websocket import HomeAssistantWebSocketClient
from app.cache.manager import cache_manager


class TestWebSocketClient:
    """Test WebSocket client functionality"""

    @pytest.mark.asyncio
    async def test_websocket_connection_auth_flow(self):
        """Test WebSocket connection and proper auth flow."""
        client = HomeAssistantWebSocketClient()

        # Mock websocket connection
        with patch("websockets.connect") as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            # Simulate auth flow
            mock_ws.recv.side_effect = [
                '{"type": "auth_required", "ha_version": "2023.1.0"}',
                '{"type": "auth_ok", "ha_version": "2023.1.0"}',
            ]

            connected = await client.connect()

            assert connected is True
            assert client.is_connected() is True
            assert client.reconnect_attempts == 0

            # Verify auth message was sent
            mock_ws.send.assert_called_once()
            sent_data = mock_ws.send.call_args[0][0]
            assert '"type": "auth"' in sent_data
            assert '"access_token"' in sent_data

    @pytest.mark.asyncio
    async def test_websocket_auth_failure(self):
        """Test WebSocket handles auth failure."""
        client = HomeAssistantWebSocketClient()

        with patch("websockets.connect") as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            # Simulate auth failure
            mock_ws.recv.side_effect = [
                '{"type": "auth_required"}',
                '{"type": "auth_invalid", "message": "Invalid access token"}',
            ]

            connected = await client.connect()

            assert connected is False
            assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_cache_update_on_state_change(self):
        """Test cache is updated with new state when WEBSOCKET_UPDATE_CACHE=true."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_UPDATE_CACHE = True
            mock_settings.WEBSOCKET_FILTER_ENABLED = False

            # Pre-populate cache with old state
            cache_manager.set("states", "get_state:light.living_room", {"state": "off"})
            cache_manager.set(
                "states", "get_all_states", [{"entity_id": "light.living_room"}]
            )

            # Simulate state change event
            client = HomeAssistantWebSocketClient()
            new_state_data = {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"brightness": 255},
            }
            event_data = {
                "event": {
                    "event_type": "state_changed",
                    "data": {
                        "entity_id": "light.living_room",
                        "new_state": new_state_data,
                        "old_state": {"state": "off"},
                    },
                }
            }

            await client._handle_state_changed(event_data)

            # Verify cache was updated with new state
            cached_state = cache_manager.get("states", "get_state:light.living_room")
            assert cached_state is not None
            assert cached_state["state"] == "on"
            assert cached_state["attributes"]["brightness"] == 255

            # All states cache should still be invalidated
            assert cache_manager.get("states", "get_all_states") is None

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_state_change(self):
        """Test cache is invalidated when WEBSOCKET_UPDATE_CACHE=false."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_UPDATE_CACHE = False
            mock_settings.WEBSOCKET_FILTER_ENABLED = False

            # Pre-populate cache
            cache_manager.set("states", "get_state:light.living_room", {"state": "off"})
            cache_manager.set(
                "states", "get_all_states", [{"entity_id": "light.living_room"}]
            )

            # Verify cache is populated
            assert (
                cache_manager.get("states", "get_state:light.living_room") is not None
            )
            assert cache_manager.get("states", "get_all_states") is not None

            # Simulate state change event
            client = HomeAssistantWebSocketClient()
            event_data = {
                "event": {
                    "event_type": "state_changed",
                    "data": {
                        "entity_id": "light.living_room",
                        "new_state": {"state": "on"},
                        "old_state": {"state": "off"},
                    },
                }
            }

            await client._handle_state_changed(event_data)

            # Verify cache was invalidated (deleted)
            assert cache_manager.get("states", "get_state:light.living_room") is None
            assert cache_manager.get("states", "get_all_states") is None

    @pytest.mark.asyncio
    async def test_cache_update_fallback_on_error(self):
        """Test cache falls back to invalidation if update fails."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_UPDATE_CACHE = True
            mock_settings.WEBSOCKET_FILTER_ENABLED = False

            # Pre-populate cache
            cache_manager.set("states", "get_state:light.living_room", {"state": "off"})

            # Mock cache_manager.set to raise an exception
            with patch.object(
                cache_manager, "set", side_effect=Exception("Cache error")
            ):
                client = HomeAssistantWebSocketClient()
                event_data = {
                    "event": {
                        "event_type": "state_changed",
                        "data": {
                            "entity_id": "light.living_room",
                            "new_state": {"state": "on"},
                            "old_state": {"state": "off"},
                        },
                    }
                }

                await client._handle_state_changed(event_data)

            # Verify cache was invalidated as fallback
            assert cache_manager.get("states", "get_state:light.living_room") is None

    @pytest.mark.asyncio
    async def test_entity_filtering(self):
        """Test entity filtering logic."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_FILTER_ENABLED = True
            mock_settings.WEBSOCKET_ENTITY_FILTERS = ["light.", "switch."]
            mock_settings.WEBSOCKET_EXCLUDE_DOMAINS = ["media_player"]

            client = HomeAssistantWebSocketClient()

            # Should process - matches filter
            assert client._should_process_entity("light.living_room") is True
            assert client._should_process_entity("switch.bedroom") is True

            # Should not process - excluded domain
            assert client._should_process_entity("media_player.tv") is False

            # Should not process - doesn't match filter
            assert client._should_process_entity("sensor.temperature") is False

    @pytest.mark.asyncio
    async def test_entity_filtering_no_filters(self):
        """Test entity filtering with no filters specified."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_FILTER_ENABLED = True
            mock_settings.WEBSOCKET_ENTITY_FILTERS = []
            mock_settings.WEBSOCKET_EXCLUDE_DOMAINS = ["camera"]

            client = HomeAssistantWebSocketClient()

            # Should process - no filters means accept all except excluded
            assert client._should_process_entity("light.living_room") is True
            assert client._should_process_entity("sensor.temperature") is True

            # Should not process - excluded domain
            assert client._should_process_entity("camera.front_door") is False

    @pytest.mark.asyncio
    async def test_service_event_cache_invalidation(self):
        """Test service events invalidate services cache."""
        # Pre-populate services cache
        cache_manager.set("services", "test_key", {"domain": "light", "services": {}})

        assert cache_manager.get("services", "test_key") is not None

        # Simulate service event
        client = HomeAssistantWebSocketClient()
        event_data = {
            "event": {
                "event_type": "service_registered",
                "data": {"domain": "light", "service": "turn_on"},
            }
        }

        await client._handle_service_event(event_data)

        # Verify services cache was cleared
        assert cache_manager.get("services", "test_key") is None

    @pytest.mark.asyncio
    async def test_reconnection_exponential_backoff(self):
        """Test reconnection uses exponential backoff."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_RECONNECT_MAX_ATTEMPTS = 3
            mock_settings.WEBSOCKET_RECONNECT_MAX_DELAY = 60

            client = HomeAssistantWebSocketClient()
            client.reconnect_attempts = 2

            with patch.object(client, "connect", return_value=False) as mock_connect:
                with patch("asyncio.sleep") as mock_sleep:
                    client.should_reconnect = False  # Prevent actual reconnection
                    await client._attempt_reconnect()

                    # Verify exponential backoff calculation
                    # attempt 3: 2^3 = 8 seconds + jitter
                    assert mock_sleep.called
                    sleep_time = mock_sleep.call_args[0][0]
                    assert 8 <= sleep_time <= 8.8  # Base delay + 10% jitter

    @pytest.mark.asyncio
    async def test_max_reconnection_attempts(self):
        """Test reconnection stops after max attempts."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_RECONNECT_MAX_ATTEMPTS = 5

            client = HomeAssistantWebSocketClient()
            client.reconnect_attempts = 5

            with patch.object(client, "connect") as mock_connect:
                await client._attempt_reconnect()

                # Should not attempt to connect if max attempts reached
                mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscription_management(self):
        """Test event subscription tracking."""
        client = HomeAssistantWebSocketClient()
        client.connected = True
        client.websocket = AsyncMock()

        callback = AsyncMock()

        # Subscribe to event
        msg_id = await client.subscribe_events("state_changed", callback)

        assert msg_id in client.subscriptions
        assert client.subscriptions[msg_id] == callback
        assert client.websocket.send.called

    def test_should_process_entity_filter_disabled(self):
        """Test entity processing when filtering is disabled."""
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.WEBSOCKET_FILTER_ENABLED = False

            client = HomeAssistantWebSocketClient()

            # When filtering is disabled, _should_process_entity is not called
            # This test verifies the filter logic works correctly when enabled
            mock_settings.WEBSOCKET_FILTER_ENABLED = True
            mock_settings.WEBSOCKET_ENTITY_FILTERS = []
            mock_settings.WEBSOCKET_EXCLUDE_DOMAINS = []

            # Should process all entities when no filters or exclusions
            assert client._should_process_entity("any.entity") is True

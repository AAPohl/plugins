"""WebSocket client for MyStiebel integration."""

import asyncio
from collections.abc import Callable
import json
import logging
from typing import Any

import aiohttp

from .const import (
    APP_NAME,
    APP_VERSION_ANDROID,
    USER_AGENT,
    WEBSOCKET_HEARTBEAT,
    WEBSOCKET_RECONNECT_INITIAL,
    WEBSOCKET_RECONNECT_MAX,
    WS_URL,
)

from .message_generator import MessageGenerator
from .mystiebel_auth import MyStiebelAuth

_LOGGER = logging.getLogger(__name__)

class WebSocketClient:
    """WebSocket client for MyStiebel integration."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: MyStiebelAuth,
        installation_id: str,
        client_id: str,
        fields_to_monitor: list[int],
        on_update: Callable[[int, Any], None],

    ) -> None:
        """Initialize the WebSocket client."""
        self.session = session
        self.auth = auth
        self.fields_to_monitor = fields_to_monitor
        self.on_update = on_update
        self.reconnect_delay = WEBSOCKET_RECONNECT_INITIAL
        self._running = True
        self._task = None
        self._current_ws = None
        self.message_generator = MessageGenerator(installation_id, client_id)

    def start(self) -> None:
        """Start the WebSocket client as a background task."""
        self._task = asyncio.create_task(
            self._run()
        )

    async def stop(self) -> None:
        """Stop the WebSocket client."""
        _LOGGER.debug("Stopping WebSocket client")
        self._running = False

        # Close any active WebSocket connection first
        if self._current_ws and not self._current_ws.closed:
            try:
                await self._current_ws.close()
                _LOGGER.debug("Closed active WebSocket connection")
            except Exception as e:
                _LOGGER.warning("Error closing WebSocket: %s", e)

        # Cancel the background task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                # Wait for task to complete with a timeout
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.CancelledError:
                _LOGGER.debug("WebSocket task cancelled")
            except asyncio.TimeoutError:
                _LOGGER.warning("WebSocket task did not stop within timeout")
            except Exception as e:
                _LOGGER.warning("Error stopping WebSocket task: %s", e)

        _LOGGER.info("WebSocket client stopped completely")

    async def _run(self) -> None:
        """Main run loop with automatic reconnection."""
        while self._running:
            try:
                if await self._connect_and_listen():
                    # Successful connection, reset delay
                    self.reconnect_delay = WEBSOCKET_RECONNECT_INITIAL
                else:
                    # Connection failed, apply backoff
                    await self._wait_reconnect()
            except asyncio.CancelledError:
                # Task was cancelled, stop immediately
                _LOGGER.debug("WebSocket task cancelled, stopping")
                break
            except Exception as e:
                _LOGGER.error("Unexpected error in WebSocket loop: %s", e, exc_info=True)
                if self._running:  # Only reconnect if we're still supposed to be running
                    await self._wait_reconnect()

    async def request_values(self) -> None:
        if self._current_ws:
            await self._request_values(self._current_ws)
        else:
            _LOGGER.warning("Cannot request values; WebSocket not connected")

    async def set_value(self, register_index: int, value: Any) -> None:
        if self._current_ws:
            await self._set_value(register_index, value, self._current_ws)
        else:
            _LOGGER.warning("Cannot set value; WebSocket not connected")

#region connection
    async def _connect_and_listen(self) -> bool:
        """Establish connection and listen for messages.

        Returns:
            True if connection was successful and closed cleanly.
            False if an error occurred.
        """
        try:
            # Authenticate first
            await self.auth.ensure_valid_token()

            # Create WebSocket connection
            async with await self._create_connection() as ws:
                _LOGGER.debug("WebSocket connected successfully")
                self._current_ws = ws

                # Login to WebSocket
                login_msg = self.message_generator.create_login(self.auth.token)
                await ws.send_json(login_msg)
                _LOGGER.debug("WebSocket login message sent")

                # Listen for messages
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._handle_text_message(ws, msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        _LOGGER.error("WebSocket error: %s", ws.exception())
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        _LOGGER.info("WebSocket connection closed")
                        break

            return True

        except asyncio.CancelledError:
            # Re-raise cancellation to propagate it
            _LOGGER.debug("Connection cancelled")
            raise
        except aiohttp.ClientError as e:
            _LOGGER.error("WebSocket connection error: %s", e)
            return False
        except Exception as e:
            _LOGGER.error("Unexpected error during WebSocket connection: %s", e)
            return False
        finally:
            self._current_ws = None

    async def _create_connection(self) -> aiohttp.ClientWebSocketResponse:
        """Create WebSocket connection with proper headers."""
        headers = {
            "Authorization": f"Bearer {self.auth.token}",
            "X-SC-ClientApp-Name": APP_NAME,
            "X-SC-ClientApp-Version": APP_VERSION_ANDROID,
            "User-Agent": USER_AGENT,
        }

        return await self.session.ws_connect(WS_URL, headers=headers, heartbeat=WEBSOCKET_HEARTBEAT)

    async def _wait_reconnect(self) -> None:
        """Handle reconnection with exponential backoff."""
        if not self._running:
            return  # Don't reconnect if we're stopping

        _LOGGER.info("Reconnecting in %d seconds", self.reconnect_delay)

        # Use interruptible sleep so we can cancel quickly
        await asyncio.sleep(self.reconnect_delay)

        # Exponential backoff
        self.reconnect_delay = min(self.reconnect_delay * 2, WEBSOCKET_RECONNECT_MAX)

#endregion

#region message handling
    async def _handle_text_message(self, ws: aiohttp.ClientWebSocketResponse, text: str) -> None:
        """Parse and route text messages to appropriate handlers."""
        try:
            data = json.loads(text)
            _LOGGER.debug("[websocket] Received: %s", data)

            # Route to appropriate handler based on message type
            if self._is_login_response(data):
                await self._request_values(ws)
            elif self._is_data(data):
                await self._handle_data(ws, data)

        except json.JSONDecodeError as e:
            _LOGGER.warning("Error parsing WebSocket message: %s", e)

    def _is_login_response(self, data: dict[str, Any]) -> bool:
        """Check if message is a login response."""
        return data.get("id") == 1 and data.get("result") is True

    def _is_data(self, data: dict[str, Any]) -> bool:
        """Check if message contains data."""
        result = data.get("result", {})
        return (
            data.get("id") is not None
            and isinstance(result, dict)
            and "fields" in result
        )

    async def _request_values(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """Request values."""
        msg = self.message_generator.create_get_values(self.fields_to_monitor)
        await ws.send_json(msg)
        _LOGGER.debug("Requested values")

    async def _handle_data(self, ws: aiohttp.ClientWebSocketResponse, data: dict[str, Any]) -> None:
        """Handle initial data response."""
        fields = data["result"]["fields"]
        _LOGGER.debug("Initial data received with %d values", len(fields))

        for field in fields:
            register = field.get("registerIndex")
            value = field.get("displayValue")
            if register is not None:
                self.on_update(register, value)

    async def _set_value(self, register_index: int, value: Any, ws: aiohttp.ClientWebSocketResponse) -> None:
        """Set a value via WebSocket."""
        msg = self.message_generator.create_set_values(register_index, value)
        _LOGGER.debug("Sending setValues message for register %d", register_index)
        await ws.send_json(msg)
        # Optimistically update the local data
        self.on_update(register_index, value)

#endregion

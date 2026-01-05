"""WebSocket client for Ujin Smart Home real-time updates."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

import aiohttp

_LOGGER = logging.getLogger(__name__)


class UjinWebSocketClient:
    """WebSocket client for receiving real-time device updates."""

    def __init__(
        self,
        url: str,
        on_message: Callable[[dict[str, Any]], None],
    ) -> None:
        """Initialize WebSocket client.

        Args:
            url: WebSocket URL to connect to
            on_message: Callback function for incoming messages
        """
        self._url = url
        self._on_message = on_message
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._listen_task: asyncio.Task | None = None
        self._should_reconnect = True
        self._reconnect_delay = 5  # seconds

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        if not self._session:
            self._session = aiohttp.ClientSession()

        try:
            _LOGGER.info("Connecting to WebSocket: %s", self._url)
            self._ws = await self._session.ws_connect(
                self._url,
                heartbeat=30,
                ssl=True,
            )
            _LOGGER.info("WebSocket connected successfully")

            # Start listening for messages
            if self._listen_task is None or self._listen_task.done():
                self._listen_task = asyncio.create_task(self._listen())

        except Exception as err:
            _LOGGER.error("Failed to connect to WebSocket: %s", err)
            await self._schedule_reconnect()

    async def _listen(self) -> None:
        """Listen for incoming WebSocket messages."""
        if not self._ws:
            return

        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        _LOGGER.debug("WebSocket message received: %s", data)
                        # Call callback with parsed message
                        if self._on_message:
                            self._on_message(data)
                    except json.JSONDecodeError as err:
                        _LOGGER.error("Failed to parse WebSocket message: %s", err)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", self._ws.exception())
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.warning("WebSocket connection closed")
                    break

        except Exception as err:
            _LOGGER.error("Error in WebSocket listen loop: %s", err)
        finally:
            if self._should_reconnect:
                await self._schedule_reconnect()

    async def _schedule_reconnect(self) -> None:
        """Schedule reconnection after delay."""
        if not self._should_reconnect:
            return

        _LOGGER.info("Scheduling WebSocket reconnect in %d seconds", self._reconnect_delay)
        await asyncio.sleep(self._reconnect_delay)

        if self._should_reconnect:
            await self.connect()

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self._should_reconnect = False

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()
            _LOGGER.info("WebSocket disconnected")

        if self._session and not self._session.closed:
            await self._session.close()

        self._ws = None
        self._session = None
        self._listen_task = None

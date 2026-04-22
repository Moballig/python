"""TCP and WebSocket communication manager for post-provisioning alerts."""

import asyncio
import json
import logging
from typing import Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TransportMode(Enum):
    """Supported transport protocols."""
    TCP = "tcp"
    WEBSOCKET = "websocket"


class CommsManager:
    """Manages TCP/WebSocket communication with the ESP32."""

    def __init__(self, mode: TransportMode = TransportMode.TCP):
        """
        Initialize the communication manager.
        
        Args:
            mode: Transport protocol (TCP or WebSocket).
        """
        self.mode = mode
        self.host: Optional[str] = None
        self.port: int = 8080
        self.is_connected = False
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.reconnect_interval_ms = 5000

        # Callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_message_received: Optional[Callable] = None
        
        # Reconnection task
        self._reconnect_task: Optional[asyncio.Task] = None
        self._read_task: Optional[asyncio.Task] = None
        self._intentional_disconnect = False

    async def connect_to_device(self, host: str, port: int = 8080) -> bool:
        """
        Connect to the ESP32 over TCP or WebSocket.
        
        Args:
            host: Host IP or hostname.
            port: Port number.
            
        Returns:
            True if connection successful, False otherwise.
        """
        self.host = host
        self.port = port
        self._intentional_disconnect = False

        logger.info(f"[CommsManager] Connecting to {host}:{port} via {self.mode.value.upper()}")

        try:
            if self.mode == TransportMode.TCP:
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=10.0
                )
            else:
                # WebSocket would require websockets library
                logger.warning("[CommsManager] WebSocket not fully implemented in CLI version")
                return False

            self.is_connected = True
            logger.info("[CommsManager] Connected.")
            
            if self.on_connected:
                await self._call_async(self.on_connected)

            # Start reading from the socket
            self._read_task = asyncio.create_task(self._read_loop())
            return True

        except Exception as e:
            logger.error(f"[CommsManager] Connection failed: {e}")
            self.is_connected = False
            if self.on_error:
                await self._call_async(self.on_error, str(e))
            return False

    async def disconnect_from_device(self) -> None:
        """Disconnect from the ESP32."""
        self._intentional_disconnect = True
        
        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            self._read_task = None

        # Cancel reconnect task
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"[CommsManager] Disconnect error: {e}")

        self.is_connected = False
        logger.info("[CommsManager] Disconnected.")
        
        if self.on_disconnected:
            await self._call_async(self.on_disconnected)

    async def send_json(self, data: dict) -> bool:
        """
        Send a JSON message.
        
        Args:
            data: Dictionary to serialize as JSON.
            
        Returns:
            True if send successful, False otherwise.
        """
        try:
            json_str = json.dumps(data, separators=(',', ':'))
            return await self.send_raw(json_str + "\n")
        except Exception as e:
            logger.error(f"[CommsManager] JSON serialization failed: {e}")
            return False

    async def send_raw(self, payload: str) -> bool:
        """
        Send a raw string.
        
        Args:
            payload: String to send.
            
        Returns:
            True if send successful, False otherwise.
        """
        if not self.is_connected or not self.writer:
            logger.warning("[CommsManager] send_raw() called but not connected.")
            return False

        try:
            self.writer.write(payload.encode("utf-8"))
            await self.writer.drain()
            logger.debug(f"[CommsManager] Sent: {payload.strip()}")
            return True
        except Exception as e:
            logger.error(f"[CommsManager] Send error: {e}")
            self.is_connected = False
            if not self._intentional_disconnect:
                await self._start_reconnect_timer()
            return False

    async def _read_loop(self) -> None:
        """Continuously read from the socket."""
        if not self.reader:
            return

        try:
            while self.is_connected and self.reader:
                line = await self.reader.readuntil(b'\n')
                if not line:
                    break
                
                message = line.decode("utf-8").strip()
                logger.debug(f"[CommsManager] Received: {message}")
                
                if self.on_message_received:
                    await self._call_async(self.on_message_received, message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"[CommsManager] Read error: {e}")
            self.is_connected = False
            
            if not self._intentional_disconnect and self.on_error:
                await self._call_async(self.on_error, str(e))
                await self._start_reconnect_timer()

    async def _start_reconnect_timer(self) -> None:
        """Schedule a reconnection attempt."""
        if self._reconnect_task:
            return

        logger.info(f"[CommsManager] Reconnecting in {self.reconnect_interval_ms}ms")
        
        async def reconnect_after_delay():
            await asyncio.sleep(self.reconnect_interval_ms / 1000.0)
            if self.host and not self.is_connected and not self._intentional_disconnect:
                await self.connect_to_device(self.host, self.port)

        self._reconnect_task = asyncio.create_task(reconnect_after_delay())

    @staticmethod
    async def _call_async(callback: Callable, *args, **kwargs):
        """Helper to safely call async or sync callbacks."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Callback error: {e}")

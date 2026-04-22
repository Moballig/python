"""NekoBot ESP32 TCP client manager."""

import asyncio
import json
import logging
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)


class NekoBotManager:
    """Manages TCP JSON communication with NekoBot ESP32."""

    def __init__(self):
        """Initialize the NekoBot manager."""
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False
        self.host: Optional[str] = None
        self.port: int = 9090
        self.buffer = ""
        self._read_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_pong_received: Optional[Callable] = None
        self.on_status_received: Optional[Callable] = None
        self.on_gas_level_received: Optional[Callable] = None
        self.on_expression_set: Optional[Callable] = None
        self.on_animation_mode_set: Optional[Callable] = None
        self.on_buzzer_state_set: Optional[Callable] = None

    async def connect_to_nekobot(self, host: str, port: int = 9090) -> bool:
        """
        Connect to NekoBot TCP server.
        
        Args:
            host: Host IP or hostname.
            port: Port number (default 9090).
            
        Returns:
            True if connection successful, False otherwise.
        """
        self.host = host
        self.port = port

        logger.info(f"[NekoBot] Connecting to {host}:{port}")

        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=10.0
            )
            self.is_connected = True
            logger.info("[NekoBot] Connected to ESP32")

            if self.on_connected:
                await self._call_async(self.on_connected)

            # Start reading and heartbeat
            self._read_task = asyncio.create_task(self._read_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            return True

        except Exception as e:
            logger.error(f"[NekoBot] Connection error: {e}")
            self.is_connected = False
            if self.on_error:
                await self._call_async(self.on_error, str(e))
            return False

    async def disconnect(self) -> None:
        """Disconnect from NekoBot."""
        # Cancel tasks
        if self._read_task:
            self._read_task.cancel()
            self._read_task = None

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        # Close socket
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"[NekoBot] Disconnect error: {e}")

        self.is_connected = False
        logger.info("[NekoBot] Disconnected")

        if self.on_disconnected:
            await self._call_async(self.on_disconnected)

    async def send_ping(self) -> None:
        """Send a ping command."""
        await self._send_command({"cmd": "ping"})

    async def set_expression(self, expr_id: int) -> None:
        """
        Set the expression (0-4).
        
        Args:
            expr_id: Expression ID (0=Normal, 1=Happy, 2=Talking, 3=Sleeping, 4=Worried).
        """
        if expr_id < 0 or expr_id > 4:
            logger.error("[NekoBot] Invalid expression ID (0-4)")
            if self.on_error:
                await self._call_async(self.on_error, "Invalid expression ID (0-4)")
            return
        await self._send_command({"cmd": "expr", "id": expr_id})

    async def set_animation_mode(self, mode: int) -> None:
        """
        Set animation mode.
        
        Args:
            mode: Animation mode (0=Idle, 1=Alert, 2=Pause, 3=Custom).
        """
        if mode < 0 or mode > 3:
            logger.error("[NekoBot] Invalid animation mode (0-3)")
            if self.on_error:
                await self._call_async(self.on_error, "Invalid animation mode (0-3)")
            return
        await self._send_command({"cmd": "anim", "mode": mode})

    async def request_status(self) -> None:
        """Request full status from NekoBot."""
        await self._send_command({"cmd": "status"})

    async def request_gas_level(self) -> None:
        """Request gas sensor level."""
        await self._send_command({"cmd": "gas"})

    async def set_buzzer(self, state: bool) -> None:
        """
        Set buzzer state.
        
        Args:
            state: True to turn buzzer on, False to turn off.
        """
        await self._send_command({"cmd": "buzzer", "state": 1 if state else 0})

    async def reset(self) -> None:
        """Reset NekoBot."""
        await self._send_command({"cmd": "reset"})

    async def _send_command(self, command: Dict[str, Any]) -> None:
        """
        Send a JSON command to NekoBot.
        
        Args:
            command: Command dictionary.
        """
        if not self.is_connected or not self.writer:
            logger.error("[NekoBot] Not connected to NekoBot")
            if self.on_error:
                await self._call_async(self.on_error, "Not connected to NekoBot")
            return

        try:
            json_str = json.dumps(command, separators=(',', ':'))
            self.writer.write((json_str + "\n").encode("utf-8"))
            await self.writer.drain()
            logger.debug(f"[NekoBot TX] {json_str}")
        except Exception as e:
            logger.error(f"[NekoBot] Send error: {e}")
            if self.on_error:
                await self._call_async(self.on_error, str(e))

    async def _read_loop(self) -> None:
        """Continuously read and process responses from NekoBot."""
        if not self.reader:
            return

        try:
            while self.is_connected and self.reader:
                line = await self.reader.readuntil(b'\n')
                if not line:
                    break

                self.buffer += line.decode("utf-8")

                # Process complete JSON objects
                while '\n' in self.buffer:
                    json_line, self.buffer = self.buffer.split('\n', 1)
                    json_line = json_line.strip()

                    if not json_line:
                        continue

                    try:
                        doc = json.loads(json_line)
                        await self._process_response(doc)
                    except json.JSONDecodeError as e:
                        logger.warning(f"[NekoBot] Invalid JSON: {json_line} ({e})")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[NekoBot] Read error: {e}")
            self.is_connected = False
            if self.on_error:
                await self._call_async(self.on_error, str(e))

    async def _heartbeat_loop(self) -> None:
        """Send periodic pings."""
        try:
            while self.is_connected:
                await asyncio.sleep(5.0)
                await self.send_ping()
        except asyncio.CancelledError:
            pass

    async def _process_response(self, response: Dict[str, Any]) -> None:
        """Process a response from NekoBot."""
        msg_type = response.get("type", "")
        logger.debug(f"[NekoBot RX] {msg_type}")

        if msg_type == "pong":
            if self.on_pong_received:
                await self._call_async(self.on_pong_received)

        elif msg_type == "status":
            expr = response.get("expr", 0)
            anim = response.get("anim", 0)
            gas_level = response.get("gas_level", 0)
            buzzer = response.get("buzzer", 0) != 0
            if self.on_status_received:
                await self._call_async(self.on_status_received, expr, anim, gas_level, buzzer)

        elif msg_type == "gas":
            gas_level = response.get("value", 0)
            if self.on_gas_level_received:
                await self._call_async(self.on_gas_level_received, gas_level)

        elif msg_type == "expr_set":
            if self.on_expression_set:
                await self._call_async(self.on_expression_set)

        elif msg_type == "anim_set":
            if self.on_animation_mode_set:
                await self._call_async(self.on_animation_mode_set)

        elif msg_type == "buzzer_set":
            if self.on_buzzer_state_set:
                await self._call_async(self.on_buzzer_state_set)

        elif msg_type == "error":
            error_msg = response.get("error", "Unknown error")
            if self.on_error:
                await self._call_async(self.on_error, f"NekoBot: {error_msg}")

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

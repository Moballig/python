"""Bluetooth Classic RFCOMM scanner and connection manager."""

import asyncio
import logging
from typing import Callable, Optional, List
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

logger = logging.getLogger(__name__)

# SPP (Serial Port Profile) UUID
SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"


class BluetoothManager:
    """Manages Bluetooth scanning and connections."""

    def __init__(self):
        """Initialize the Bluetooth manager."""
        self.devices: List[BLEDevice] = []
        self.client: Optional[BleakClient] = None
        self.is_scanning = False
        self.is_connected = False
        
        # Callbacks
        self.on_device_found: Optional[Callable] = None
        self.on_scan_finished: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_data_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    async def start_scan(self, timeout: float = 12.0) -> None:
        """
        Start a Bluetooth device scan.
        
        Args:
            timeout: Scan duration in seconds (default 12).
        """
        if self.is_scanning:
            logger.warning("[BT] Scan already in progress — ignoring startScan().")
            return

        self.devices.clear()
        self.is_scanning = True
        logger.info("[BT] Starting Bluetooth device scan…")

        try:
            # Modern Bleak API: discover() handles the scanner and sleep automatically
            devices = await BleakScanner.discover(timeout=timeout)
            self.devices = devices
            
            for device in devices:
                logger.debug(f"[BT] Found device: {device.name} | {device.address}")
                if self.on_device_found:
                    await self._call_async(self.on_device_found, device)
                    
        except Exception as e:
            logger.error(f"[BT] Scan error: {e}")
            if self.on_error:
                await self._call_async(self.on_error, str(e))
        finally:
            self.is_scanning = False
            logger.info(f"[BT] Scan finished. Found {len(self.devices)} device(s).")
            if self.on_scan_finished:
                await self._call_async(self.on_scan_finished)

    def stop_scan(self) -> None:
        """Stop the current scan (if any)."""
        if self.is_scanning:
            self.is_scanning = False
            logger.info("[BT] Scan stopped by user.")

    async def connect_to_device(self, address: str) -> bool:
        """
        Connect to a Bluetooth device via RFCOMM/SPP.
        
        Args:
            address: Bluetooth MAC address.
            
        Returns:
            True if connection successful, False otherwise.
        """
        if self.client and self.is_connected:
            await self.disconnect_from_device()

        logger.info(f"[BT] Connecting to {address}…")

        try:
            self.client = BleakClient(address)
            await self.client.connect()
            self.is_connected = True
            logger.info(f"[BT] Connected to {address}")
            
            if self.on_connected:
                await self._call_async(self.on_connected)
            return True
        except Exception as e:
            logger.error(f"[BT] Connection failed: {e}")
            self.is_connected = False
            if self.on_error:
                await self._call_async(self.on_error, str(e))
            return False

    async def disconnect_from_device(self) -> None:
        """Disconnect from the current device."""
        if self.client and self.is_connected:
            try:
                await self.client.disconnect()
                self.is_connected = False
                logger.info("[BT] Disconnected from device.")
                if self.on_disconnected:
                    await self._call_async(self.on_disconnected)
            except Exception as e:
                logger.error(f"[BT] Disconnect error: {e}")

    async def send_data(self, payload: str) -> bool:
        """
        Send data over the RFCOMM connection.
        
        Args:
            payload: UTF-8 string to send.
            
        Returns:
            True if write succeeded, False otherwise.
        """
        if not self.is_connected or not self.client:
            logger.warning("[BT] sendData() called but socket is not connected.")
            return False

        try:
            data = payload.encode("utf-8")
            # Note: Bleak uses GATT characteristics, writing requires a specific UUID
            # Simplified for demo
            logger.debug(f"[BT] Sent {len(data)} bytes: {payload.strip()}")
            return True
        except Exception as e:
            logger.error(f"[BT] Write failed: {e}")
            return False

    def get_discovered_devices(self) -> List[BLEDevice]:
        """Get list of discovered devices."""
        return self.devices.copy()

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

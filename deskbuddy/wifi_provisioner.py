"""WiFi credential provisioning over Bluetooth."""

import asyncio
import json
import logging
from typing import Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ProvisioningState(Enum):
    """Provisioning handshake states."""
    IDLE = "idle"
    SENDING = "sending"
    WAITING_FOR_ACK = "waiting_for_ack"
    SUCCESS = "success"
    FAILED = "failed"


class WiFiProvisioner:
    """Handles WiFi credential provisioning over Bluetooth."""

    def __init__(self, bluetooth_manager):
        """
        Initialize the WiFi provisioner.
        
        Args:
            bluetooth_manager: BluetoothManager instance to use for communication.
        """
        self.bt = bluetooth_manager
        self.state = ProvisioningState.IDLE
        self.ack_timeout_ms = 15000
        self.ack_timer_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_provisioning_succeeded: Optional[Callable] = None
        self.on_provisioning_failed: Optional[Callable] = None
        self.on_state_changed: Optional[Callable] = None

        # Wire up Bluetooth data reception
        if self.bt.on_data_received is None:
            self.bt.on_data_received = self._on_data_received

    async def send_credentials(self, ssid: str, password: str) -> None:
        """
        Send WiFi credentials to the ESP32.
        
        Args:
            ssid: WiFi network name.
            password: WiFi network password.
        """
        # Guard: must be Idle
        if self.state != ProvisioningState.IDLE:
            logger.warning(f"[WiFiProvisioner] Cannot send — current state: {self.state.value}")
            return

        # Guard: SSID cannot be empty
        if not ssid or not ssid.strip():
            logger.warning("[WiFiProvisioner] SSID is empty.")
            if self.on_provisioning_failed:
                await self._call_async(self.on_provisioning_failed, "SSID cannot be empty.")
            return

        # Guard: BT must be connected
        if not self.bt.is_connected:
            logger.warning("[WiFiProvisioner] Bluetooth not connected.")
            if self.on_provisioning_failed:
                await self._call_async(
                    self.on_provisioning_failed,
                    "Bluetooth is not connected to the ESP32."
                )
            return

        logger.info(f"[WiFiProvisioner] Sending credentials for SSID: {ssid}")
        await self._set_state(ProvisioningState.SENDING)

        # Build and send the JSON packet
        packet = self._build_credential_packet(ssid, password)
        payload = json.dumps(packet, separators=(',', ':')) + "\n"

        success = await self.bt.send_data(payload)
        if not success:
            logger.error("[WiFiProvisioner] Failed to send data.")
            await self._set_state(ProvisioningState.FAILED)
            if self.on_provisioning_failed:
                await self._call_async(self.on_provisioning_failed, "Bluetooth write failed.")
            return

        await self._set_state(ProvisioningState.WAITING_FOR_ACK)
        logger.info(f"[WiFiProvisioner] Waiting for ACK ({self.ack_timeout_ms}ms timeout)…")

        # Start timeout timer
        self._start_ack_timer()

    async def reset(self) -> None:
        """Reset provisioner to idle state."""
        if self.ack_timer_task:
            self.ack_timer_task.cancel()
            self.ack_timer_task = None
        await self._set_state(ProvisioningState.IDLE)
        logger.info("[WiFiProvisioner] Reset to Idle.")

    def set_ack_timeout(self, ms: int) -> None:
        """
        Set the ACK timeout in milliseconds.
        
        Args:
            ms: Timeout in milliseconds.
        """
        self.ack_timeout_ms = ms
        logger.info(f"[WiFiProvisioner] ACK timeout updated to {ms}ms")

    async def _on_data_received(self, data: str) -> None:
        """Handle incoming Bluetooth data."""
        if self.state != ProvisioningState.WAITING_FOR_ACK:
            return

        logger.debug(f"[WiFiProvisioner] Received while waiting for ACK: {data}")

        # Check for WIFI_OK
        if data.startswith("WIFI_OK"):
            if self.ack_timer_task:
                self.ack_timer_task.cancel()
                self.ack_timer_task = None

            await self._set_state(ProvisioningState.SUCCESS)

            # Extract optional IP address
            parts = data.split()
            esp_ip = parts[1] if len(parts) >= 2 else ""

            logger.info(f"[WiFiProvisioner] Provisioning SUCCEEDED. ESP32 IP: {esp_ip}")
            if self.on_provisioning_succeeded:
                await self._call_async(self.on_provisioning_succeeded, esp_ip)
            return

        # Check for WIFI_FAIL
        if data.startswith("WIFI_FAIL"):
            if self.ack_timer_task:
                self.ack_timer_task.cancel()
                self.ack_timer_task = None

            await self._set_state(ProvisioningState.FAILED)
            logger.error("[WiFiProvisioner] Provisioning FAILED: ESP32 reported WIFI_FAIL.")
            if self.on_provisioning_failed:
                await self._call_async(
                    self.on_provisioning_failed,
                    "ESP32 could not connect to the WiFi network. Check the SSID and password."
                )

    def _start_ack_timer(self) -> None:
        """Start the ACK timeout timer."""
        if self.ack_timer_task:
            return

        async def timer_task():
            await asyncio.sleep(self.ack_timeout_ms / 1000.0)
            if self.state == ProvisioningState.WAITING_FOR_ACK:
                await self._on_ack_timeout()

        self.ack_timer_task = asyncio.create_task(timer_task())

    async def _on_ack_timeout(self) -> None:
        """Handle ACK timeout."""
        logger.error(f"[WiFiProvisioner] ACK timeout after {self.ack_timeout_ms}ms")
        await self._set_state(ProvisioningState.FAILED)
        if self.on_provisioning_failed:
            await self._call_async(
                self.on_provisioning_failed,
                f"No response from ESP32 after {self.ack_timeout_ms // 1000} seconds. "
                "Is the firmware running?"
            )

    async def _set_state(self, new_state: ProvisioningState) -> None:
        """Update provisioning state."""
        if self.state != new_state:
            self.state = new_state
            logger.debug(f"[WiFiProvisioner] State changed to: {new_state.value}")
            if self.on_state_changed:
                await self._call_async(self.on_state_changed, new_state)

    @staticmethod
    def _build_credential_packet(ssid: str, password: str) -> dict:
        """Build the credential JSON packet."""
        return {
            "type": "wifi_config",
            "ssid": ssid,
            "password": password
        }

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

"""Cross-platform notification and system monitoring manager."""

import asyncio
import json
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from enum import Enum

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)


class AlertCategory(Enum):
    """Alert category types."""
    DEV = "dev"
    SYSTEM = "system"
    WELLNESS = "wellness"


class Urgency(Enum):
    """Alert urgency levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class NotificationManager:
    """Manages alerts and cross-platform system monitoring."""

    def __init__(self, comms_manager):
        """
        Initialize the notification manager.
        
        Args:
            comms_manager: CommsManager instance to use for sending alerts.
        """
        self.comms = comms_manager

        # Callbacks
        self.on_alert_sent: Optional[Callable] = None
        self.on_send_failed: Optional[Callable] = None

    async def send_dev_alert(self) -> None:
        """Send a development/compilation alert."""
        await self.send_alert(
            AlertCategory.DEV,
            Urgency.HIGH,
            "Compilation Error",
            "error C2065: 'undeclaredVar' — undeclared identifier  [main.cpp:42]",
            "#FF3333"
        )

    async def send_system_vital(self) -> None:
        """Send a system vital alert (CPU temp or usage)."""
        temp_c = await self._query_cpu_temp_celsius()

        if temp_c >= 0:
            urgency = Urgency.HIGH if temp_c > 90.0 else Urgency.MEDIUM
            color = "#FF3333" if temp_c > 90.0 else "#FF8C00"
            body = f"CPU temperature is {temp_c:.1f} °C — consider closing heavy workloads."
            await self.send_alert(
                AlertCategory.SYSTEM,
                urgency,
                "High CPU Temperature",
                body,
                color
            )
        else:
            # Fallback to CPU usage
            cpu_pct = await self._query_cpu_usage_percent()
            urgency = Urgency.HIGH if cpu_pct > 85.0 else Urgency.MEDIUM
            color = "#FF3333" if cpu_pct > 85.0 else "#FF8C00"
            body = f"CPU usage is {cpu_pct:.1f}% — system may be under heavy load."
            await self.send_alert(
                AlertCategory.SYSTEM,
                urgency,
                "High CPU Usage",
                body,
                color
            )

    async def send_wellness_reminder(self) -> None:
        """Send a wellness reminder (if user is active)."""
        idle_ms = await self._query_idle_time_ms()

        if idle_ms >= 0 and idle_ms > (5 * 60 * 1000):
            logger.info(f"[NotificationManager] User idle ({idle_ms}ms) — skipping reminder.")
            return

        await self.send_alert(
            AlertCategory.WELLNESS,
            Urgency.LOW,
            "Drink Water 💧",
            "You have been coding for a while — grab some water!",
            "#2979FF"
        )

    async def send_alert(
        self,
        category: AlertCategory,
        urgency: Urgency,
        title: str,
        body: str,
        color_hex: str = ""
    ) -> bool:
        """
        Send an alert via CommsManager.
        
        Args:
            category: Alert category.
            urgency: Alert urgency level.
            title: Alert title.
            body: Alert body/description.
            color_hex: Color hex code (default auto-selected by urgency).
            
        Returns:
            True if sent successfully, False otherwise.
        """
        if not color_hex:
            color_hex = self._urgency_to_color_hex(urgency)

        payload = self._build_payload(category, urgency, title, body, color_hex)

        try:
            success = await self.comms.send_json(payload)
            if success:
                logger.info(f"[NotificationManager] Alert sent: {title}")
                if self.on_alert_sent:
                    await self._call_async(self.on_alert_sent, title)
            else:
                logger.warning(f"[NotificationManager] Failed to send: {title}")
                if self.on_send_failed:
                    await self._call_async(self.on_send_failed, title)
            return success
        except Exception as e:
            logger.error(f"[NotificationManager] Send error: {e}")
            if self.on_send_failed:
                await self._call_async(self.on_send_failed, title)
            return False

    @staticmethod
    async def _query_cpu_usage_percent() -> float:
        """
        Query CPU usage percentage.
        
        Returns:
            CPU usage as percentage (0-100), or 0.0 on error.
        """
        if psutil is None:
            logger.warning("[NotificationManager] psutil not available for CPU query.")
            return 0.0

        try:
            # Take two samples with delay to get CPU delta
            await asyncio.sleep(0.5)
            cpu_percent = psutil.cpu_percent(interval=0.5)
            return float(cpu_percent)
        except Exception as e:
            logger.error(f"[NotificationManager] CPU query error: {e}")
            return 0.0

    @staticmethod
    async def _query_cpu_temp_celsius() -> float:
        """
        Query CPU temperature.
        
        Returns:
            Temperature in Celsius, or -1.0 if unavailable.
        """
        system = platform.system()

        if system == "Windows":
            # Windows: WMI/LibreHardwareMonitor needed
            return -1.0
        elif system == "Linux":
            # Linux: Check /sys/class/thermal/
            max_temp = -1.0
            for zone in range(10):
                try:
                    zone_file = Path(f"/sys/class/thermal/thermal_zone{zone}/temp")
                    if zone_file.exists():
                        temp_millidegrees = int(zone_file.read_text().strip())
                        temp_c = temp_millidegrees / 1000.0
                        max_temp = max(max_temp, temp_c)
                except Exception:
                    pass
            return max_temp
        else:
            return -1.0

    @staticmethod
    async def _query_idle_time_ms() -> int:
        """
        Query idle time since last user input.
        
        Returns:
            Milliseconds since last input, or -1 if unavailable.
        """
        system = platform.system()

        if system == "Windows":
            # Windows: GetLastInputInfo via ctypes
            try:
                import ctypes
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]

                lii = LASTINPUTINFO()
                lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
                current_ticks = ctypes.windll.kernel32.GetTickCount()
                return current_ticks - lii.dwTime
            except Exception as e:
                logger.debug(f"[NotificationManager] Idle query error: {e}")
                return -1
        elif system == "Linux":
            # Linux: Use xprintidle if available
            try:
                result = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        "xprintidle",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    ),
                    timeout=2.0
                )
                stdout, _ = await asyncio.wait_for(result.communicate(), timeout=2.0)
                if result.returncode == 0:
                    return int(stdout.decode().strip())
            except Exception as e:
                logger.debug(f"[NotificationManager] xprintidle error: {e}")
            return -1
        else:
            return -1

    @staticmethod
    def _build_payload(
        category: AlertCategory,
        urgency: Urgency,
        title: str,
        body: str,
        color_hex: str
    ) -> dict:
        """Build the alert JSON payload."""
        return {
            "schema_ver": 1,
            "category": category.value,
            "urgency": urgency.value,
            "title": title,
            "body": body,
            "color_hex": color_hex,
            "timestamp": int(datetime.now().timestamp())
        }

    @staticmethod
    def _urgency_to_color_hex(urgency: Urgency) -> str:
        """Map urgency to color hex."""
        color_map = {
            Urgency.HIGH: "#FF3333",
            Urgency.MEDIUM: "#FF8C00",
            Urgency.LOW: "#2979FF"
        }
        return color_map.get(urgency, "#FFFFFF")

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

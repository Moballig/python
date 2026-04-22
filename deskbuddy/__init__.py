"""DeskBuddy - Terminal-based Bluetooth/WiFi/Alert manager for ESP32"""

__version__ = "2.0.0"
__author__ = "DeskBuddy Team"

from .bluetooth_manager import BluetoothManager
from .comms_manager import CommsManager
from .wifi_provisioner import WiFiProvisioner
from .notification_manager import NotificationManager
from .nekobot_manager import NekoBotManager

__all__ = [
    "BluetoothManager",
    "CommsManager",
    "WiFiProvisioner",
    "NotificationManager",
    "NekoBotManager",
]

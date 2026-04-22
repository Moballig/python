#!/usr/bin/env python3
"""
Example: Complete Bluetooth → WiFi → Alert workflow
"""

import asyncio
from deskbuddy import (
    BluetoothManager,
    WiFiProvisioner,
    CommsManager,
    NotificationManager,
)
from deskbuddy.comms_manager import TransportMode


async def main():
    """Run a complete DeskBuddy workflow."""
    
    # Initialize managers
    bt = BluetoothManager()
    comms = CommsManager(TransportMode.TCP)
    provisioner = WiFiProvisioner(bt)
    notifications = NotificationManager(comms)

    print("=" * 60)
    print("DeskBuddy Example: Complete Workflow")
    print("=" * 60)

    # Step 1: Scan for Bluetooth devices
    print("\n[1] Scanning for Bluetooth devices…")
    await bt.start_scan(timeout=10)

    devices = bt.get_discovered_devices()
    if not devices:
        print("No devices found!")
        return

    for idx, device in enumerate(devices):
        print(f"  {idx}: {device.name or '(unnamed)'} [{device.address}]")

    # Connect to first device
    device = devices[0]
    print(f"\n[2] Connecting to {device.name} ({device.address})…")
    success = await bt.connect_to_device(device.address)

    if not success:
        print("Failed to connect!")
        return

    print("✓ Connected")

    # Step 2: Provision WiFi
    print("\n[3] Provisioning WiFi…")

    provisioning_done = asyncio.Event()

    async def on_prov_success(ip: str):
        print(f"✓ WiFi provisioning succeeded! IP: {ip}")
        provisioning_done.set()

    async def on_prov_fail(reason: str):
        print(f"✗ WiFi provisioning failed: {reason}")
        provisioning_done.set()

    provisioner.on_provisioning_succeeded = on_prov_success
    provisioner.on_provisioning_failed = on_prov_fail

    ssid = "YourNetworkName"
    password = "YourPassword"
    await provisioner.send_credentials(ssid, password)

    try:
        await asyncio.wait_for(provisioning_done.wait(), timeout=20)
    except asyncio.TimeoutError:
        print("WiFi provisioning timed out!")
        return

    # Step 3: Connect TCP
    print("\n[4] Connecting to ESP32 over TCP…")

    tcp_connected = asyncio.Event()

    async def on_tcp_connect():
        print("✓ TCP Connected")
        tcp_connected.set()

    async def on_tcp_error(err: str):
        print(f"✗ TCP Error: {err}")

    comms.on_connected = on_tcp_connect
    comms.on_error = on_tcp_error

    esp32_ip = "192.168.1.100"  # From WiFi provisioning or your router
    await comms.connect_to_device(esp32_ip, 8080)

    try:
        await asyncio.wait_for(tcp_connected.wait(), timeout=10)
    except asyncio.TimeoutError:
        print("TCP connection timed out!")
        return

    # Step 4: Send alerts
    print("\n[5] Sending alerts…")

    await notifications.send_dev_alert()
    await asyncio.sleep(1)

    await notifications.send_system_vital()
    await asyncio.sleep(1)

    await notifications.send_wellness_reminder()

    print("\n✓ Workflow completed!")

    # Cleanup
    await bt.disconnect_from_device()
    await comms.disconnect_from_device()


if __name__ == "__main__":
    asyncio.run(main())

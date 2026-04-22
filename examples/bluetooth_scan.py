#!/usr/bin/env python3
"""
Example: Simple Bluetooth scanning and connection
"""

import asyncio
from deskbuddy import BluetoothManager


async def main():
    """Simple Bluetooth example."""

    bt = BluetoothManager()

    print("=" * 60)
    print("DeskBuddy Example: Bluetooth Scanning")
    print("=" * 60)

    # Scan
    print("\n[1] Scanning for Bluetooth devices (10 seconds)…\n")
    await bt.start_scan(timeout=10)

    devices = bt.get_discovered_devices()

    if not devices:
        print("No devices found!")
        return

    print(f"Found {len(devices)} device(s):\n")

    for idx, device in enumerate(devices):
        name = device.name or "(unnamed)"
        addr = device.address
        rssi = getattr(device, 'rssi', 'N/A')
        print(f"  {idx}: {name:30} [{addr:17}] RSSI: {rssi}")

    # Connect to user choice
    try:
        choice = int(input("\nSelect device to connect (0-{}): ".format(len(devices) - 1)))
    except (ValueError, KeyError):
        print("Invalid selection")
        return

    device = devices[choice]
    print(f"\nConnecting to {device.name} ({device.address})…")

    success = await bt.connect_to_device(device.address)

    if success:
        print("✓ Connected!")
        print(f"  Name: {device.name}")
        print(f"  Address: {device.address}")
        print(f"  RSSI: {getattr(device, 'rssi', 'N/A')}")

        # Keep connection open for a bit
        await asyncio.sleep(5)

        print("\nDisconnecting…")
        await bt.disconnect_from_device()
        print("✓ Disconnected")
    else:
        print("✗ Connection failed!")


if __name__ == "__main__":
    asyncio.run(main())

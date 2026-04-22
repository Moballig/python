#!/usr/bin/env python3
"""
Example: Control NekoBot robot via terminal
"""

import asyncio
from deskbuddy import NekoBotManager


async def main():
    """Interactive NekoBot control example."""

    neko = NekoBotManager()

    print("=" * 60)
    print("DeskBuddy Example: NekoBot Control")
    print("=" * 60)

    # Connect
    print("\n[1] Connecting to NekoBot…")

    connected_event = asyncio.Event()

    async def on_connected():
        print("✓ Connected to NekoBot")
        connected_event.set()

    async def on_status(expr, anim, gas, buzzer):
        print(f"  Status: expr={expr}, anim={anim}, gas={gas}, buzzer={buzzer}")

    async def on_gas(level):
        print(f"  Gas Level: {level} ADC")

    async def on_error(msg):
        print(f"✗ Error: {msg}")

    neko.on_connected = on_connected
    neko.on_status_received = on_status
    neko.on_gas_level_received = on_gas
    neko.on_error = on_error

    success = await neko.connect_to_nekobot("192.168.1.100", 9090)

    if not success:
        print("Failed to connect!")
        return

    try:
        await asyncio.wait_for(connected_event.wait(), timeout=5)
    except asyncio.TimeoutError:
        print("Connection timed out!")
        return

    # Control loop
    print("\nAvailable commands:")
    print("  expr 0-4    : Set expression")
    print("  anim 0-3    : Set animation")
    print("  buzzer on   : Turn buzzer on")
    print("  buzzer off  : Turn buzzer off")
    print("  status      : Request status")
    print("  gas         : Check gas level")
    print("  reset       : Reset NekoBot")
    print("  quit        : Exit")

    while True:
        try:
            cmd = input("\n> ").strip().lower()

            if cmd == "quit":
                break

            elif cmd.startswith("expr "):
                expr_id = int(cmd.split()[1])
                await neko.set_expression(expr_id)

            elif cmd.startswith("anim "):
                mode = int(cmd.split()[1])
                await neko.set_animation_mode(mode)

            elif cmd == "buzzer on":
                await neko.set_buzzer(True)

            elif cmd == "buzzer off":
                await neko.set_buzzer(False)

            elif cmd == "status":
                await neko.request_status()
                await asyncio.sleep(0.5)

            elif cmd == "gas":
                await neko.request_gas_level()
                await asyncio.sleep(0.5)

            elif cmd == "reset":
                await neko.reset()

            else:
                print("Unknown command")

        except Exception as e:
            print(f"Error: {e}")

    # Disconnect
    print("\nDisconnecting…")
    await neko.disconnect()
    print("✓ Done")


if __name__ == "__main__":
    asyncio.run(main())

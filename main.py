#!/usr/bin/env python3
"""
DeskBuddy - Terminal-based Bluetooth/WiFi/Alert Manager for ESP32

A Python CLI application for managing ESP32 Bluetooth connectivity,
WiFi provisioning, and sending alerts over TCP/WebSocket.
"""

import asyncio
import logging
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich.markdown import Markdown

from deskbuddy.bluetooth_manager import BluetoothManager
from deskbuddy.comms_manager import CommsManager, TransportMode
from deskbuddy.wifi_provisioner import WiFiProvisioner
from deskbuddy.notification_manager import NotificationManager
from deskbuddy.nekobot_manager import NekoBotManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('deskbuddy.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

console = Console()


class DeskBuddyCLI:
    """Main CLI application for DeskBuddy."""

    def __init__(self):
        """Initialize the CLI application."""
        self.bt = BluetoothManager()
        self.comms = CommsManager(TransportMode.TCP)
        self.provisioner = WiFiProvisioner(self.bt)
        self.notifications = NotificationManager(self.comms)
        self.nekobot = NekoBotManager()

    async def scan_bluetooth(self) -> None:
        """Scan for Bluetooth devices."""
        console.print(Panel("🔍 Bluetooth Device Scan", title="Bluetooth", expand=False))
        
        with console.status("[bold blue]Scanning for Bluetooth devices…"):
            await self.bt.start_scan(timeout=12)

        devices = self.bt.get_discovered_devices()
        
        if not devices:
            console.print("[red]✗ No devices found[/red]")
            return

        # Display discovered devices
        table = Table(title="Discovered Devices")
        table.add_column("Index", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Address", style="magenta")
        table.add_column("RSSI", style="yellow")

        for idx, device in enumerate(devices):
            rssi = getattr(device, 'rssi', 'N/A')
            table.add_row(
                str(idx),
                device.name or "(unnamed)",
                device.address,
                str(rssi)
            )

        console.print(table)

    async def connect_bluetooth(self, device_index: int) -> None:
        """Connect to a specific Bluetooth device."""
        devices = self.bt.get_discovered_devices()
        
        if device_index < 0 or device_index >= len(devices):
            console.print(f"[red]✗ Invalid device index: {device_index}[/red]")
            return

        device = devices[device_index]
        console.print(f"Connecting to {device.name} ({device.address})…")

        success = await self.bt.connect_to_device(device.address)
        if success:
            console.print(f"[green]✓ Connected[/green]")
        else:
            console.print(f"[red]✗ Connection failed[/red]")

    async def provision_wifi(self, ssid: str, password: str) -> None:
        """Provision WiFi credentials."""
        if not self.bt.is_connected:
            console.print("[red]✗ Bluetooth not connected[/red]")
            return

        console.print(
            Panel(
                f"📡 Sending WiFi credentials to ESP32\n"
                f"SSID: [bold]{ssid}[/bold]\n"
                f"(password hidden)",
                title="WiFi Provisioning"
            )
        )

        result_received = asyncio.Event()

        async def on_success(ip: str):
            console.print(f"[green]✓ Provisioning succeeded[/green]")
            if ip:
                console.print(f"  ESP32 IP: [bold cyan]{ip}[/bold cyan]")
            result_received.set()

        async def on_failure(reason: str):
            console.print(f"[red]✗ Provisioning failed: {reason}[/red]")
            result_received.set()

        self.provisioner.on_provisioning_succeeded = on_success
        self.provisioner.on_provisioning_failed = on_failure

        await self.provisioner.send_credentials(ssid, password)

        # Wait for result with timeout
        try:
            await asyncio.wait_for(result_received.wait(), timeout=20.0)
        except asyncio.TimeoutError:
            console.print("[red]✗ Provisioning timeout[/red]")

    async def connect_tcp(self, host: str, port: int = 9090) -> None:
        """Connect to ESP32 over TCP."""
        console.print(f"Connecting to {host}:{port}…")

        async def on_connected():
            console.print("[green]✓ TCP connected[/green]")

        async def on_disconnected():
            console.print("[yellow]⚠ TCP disconnected[/yellow]")

        async def on_error(msg: str):
            console.print(f"[red]✗ TCP error: {msg}[/red]")

        self.comms.on_connected = on_connected
        self.comms.on_disconnected = on_disconnected
        self.comms.on_error = on_error

        success = await self.comms.connect_to_device(host, port)
        if not success:
            console.print("[red]✗ Connection failed[/red]")

    async def send_dev_alert(self) -> None:
        """Send a development alert."""
        if not self.comms.is_connected:
            console.print("[red]✗ TCP not connected[/red]")
            return

        console.print("Sending development alert…")
        await self.notifications.send_dev_alert()

    async def send_system_vital(self) -> None:
        """Send a system vital alert."""
        if not self.comms.is_connected:
            console.print("[red]✗ TCP not connected[/red]")
            return

        console.print("Querying system vitals…")
        await self.notifications.send_system_vital()

    async def send_wellness_reminder(self) -> None:
        """Send a wellness reminder."""
        if not self.comms.is_connected:
            console.print("[red]✗ TCP not connected[/red]")
            return

        console.print("Checking user activity…")
        await self.notifications.send_wellness_reminder()

    async def send_code_error(self, error_msg: str, file: str = "code", line: int = 0) -> None:
        """Send custom code error to ESP32 display."""
        if not self.comms.is_connected:
            console.print("[red]✗ TCP not connected[/red]")
            return

        # Create formatted title
        title = f"❌ Error: {file}:{line}" if line else f"❌ Error in {file}"
        
        # Build payload
        payload = {
            "cmd": "alert",
            "category": "dev",
            "urgency": 3,
            "title": title,
            "body": error_msg,
            "color": "#FF3333",
            "file": file,
            "line": line
        }
        
        # Send to ESP32
        success = await self.comms.send_json(payload)
        if success:
            console.print(f"[green]✓ Error sent to ESP32 display[/green]")
            console.print(f"   [bold]{title}[/bold]")
            console.print(f"   {error_msg}")
        else:
            console.print("[red]✗ Failed to send error to ESP32[/red]")

    async def connect_nekobot(self, host: str, port: int = 9090) -> None:
        """Connect to NekoBot."""
        console.print(f"Connecting to NekoBot at {host}:{port}…")

        async def on_connected():
            console.print("[green]✓ NekoBot connected[/green]")
            await self.nekobot.request_status()

        async def on_error(msg: str):
            console.print(f"[red]✗ NekoBot error: {msg}[/red]")

        self.nekobot.on_connected = on_connected
        self.nekobot.on_error = on_error

        success = await self.nekobot.connect_to_nekobot(host, port)
        if not success:
            console.print("[red]✗ Connection failed[/red]")

    async def nekobot_set_expression(self, expr_id: int) -> None:
        """Set NekoBot expression."""
        if not self.nekobot.is_connected:
            console.print("[red]✗ NekoBot not connected[/red]")
            return

        expressions = ["Normal", "Happy", "Talking", "Sleeping", "Worried"]
        console.print(f"Setting expression to: {expressions[expr_id]}")
        await self.nekobot.set_expression(expr_id)

    async def nekobot_set_buzzer(self, state: bool) -> None:
        """Set NekoBot buzzer."""
        if not self.nekobot.is_connected:
            console.print("[red]✗ NekoBot not connected[/red]")
            return

        console.print(f"Setting buzzer to: {'ON' if state else 'OFF'}")
        await self.nekobot.set_buzzer(state)

    def show_status(self) -> None:
        """Show connection status."""
        table = Table(title="Connection Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")

        bt_status = "🟢 Connected" if self.bt.is_connected else "🔴 Disconnected"
        tcp_status = "🟢 Connected" if self.comms.is_connected else "🔴 Disconnected"
        prov_status = self.provisioner.state.value
        nekobot_status = "🟢 Connected" if self.nekobot.is_connected else "🔴 Disconnected"

        table.add_row("Bluetooth", bt_status)
        table.add_row("TCP/WebSocket", tcp_status)
        table.add_row("WiFi Provisioning", prov_status)
        table.add_row("NekoBot", nekobot_status)

        console.print(table)

    def show_help(self) -> None:
        """Show interactive help menu."""
        help_text = """
# DeskBuddy CLI - Help

## Commands

### Bluetooth Management
- **scan** - Scan for Bluetooth devices
- **connect <index>** - Connect to device by index
- **bt-status** - Show Bluetooth status
- **bt-disconnect** - Disconnect Bluetooth

### WiFi Provisioning
- **provision <ssid> <password>** - Send WiFi credentials to ESP32
- **reset-provisioner** - Reset provisioning state

### Alert System
- **tcp-connect <host> [port]** - Connect to ESP32 over TCP
- **tcp-disconnect** - Disconnect TCP
- **send-dev** - Send development alert
- **send-system** - Send system vital alert
- **send-wellness** - Send wellness reminder
- **send-error <msg> [file] [line]** - Send custom code error to ESP32 display

### NekoBot
- **neko-connect <host> [port]** - Connect to NekoBot
- **neko-expr <0-4>** - Set NekoBot expression
- **neko-buzzer <on|off>** - Control NekoBot buzzer
- **neko-status** - Request NekoBot status
- **neko-gas** - Check NekoBot gas level
- **neko-reset** - Reset NekoBot

### General
- **status** - Show connection status
- **help** - Show this help
- **quit** - Exit the application
"""
        console.print(Markdown(help_text))

    async def run_interactive(self) -> None:
        """Run interactive CLI loop."""
        console.print(Panel(
            "🤖 DeskBuddy - Terminal Edition\n"
            "[cyan]Type 'help' for commands[/cyan]",
            title="Welcome",
            expand=False
        ))

        self.show_status()

        while True:
            try:
                console.print()
                cmd = console.input("[bold cyan]> [/bold cyan]").strip()

                if not cmd:
                    continue

                parts = cmd.split()
                command = parts[0].lower()
                args = parts[1:]

                if command == "quit" or command == "exit":
                    console.print("[yellow]Exiting…[/yellow]")
                    break

                elif command == "help":
                    self.show_help()

                elif command == "status":
                    self.show_status()

                elif command == "scan":
                    await self.scan_bluetooth()

                elif command == "connect" and args:
                    try:
                        idx = int(args[0])
                        await self.connect_bluetooth(idx)
                    except ValueError:
                        console.print("[red]✗ Invalid device index[/red]")

                elif command == "provision" and len(args) >= 2:
                    ssid = args[0]
                    password = " ".join(args[1:])
                    await self.provision_wifi(ssid, password)

                elif command == "tcp-connect" and args:
                    host = args[0]
                    port = int(args[1]) if len(args) > 1 else 9090
                    await self.connect_tcp(host, port)

                elif command == "tcp-disconnect":
                    await self.comms.disconnect_from_device()

                elif command == "send-dev":
                    await self.send_dev_alert()

                elif command == "send-system":
                    await self.send_system_vital()

                elif command == "send-wellness":
                    await self.send_wellness_reminder()

                elif command == "send-error":
                    if len(args) < 1:
                        console.print("[red]Usage: send-error <error_msg> [file] [line][/red]")
                    else:
                        file = args[1] if len(args) > 1 else "code"
                        try:
                            line = int(args[2]) if len(args) > 2 else 0
                        except ValueError:
                            line = 0
                        await self.send_code_error(args[0], file, line)

                elif command == "neko-connect" and args:
                    host = args[0]
                    port = int(args[1]) if len(args) > 1 else 9090
                    await self.connect_nekobot(host, port)

                elif command == "neko-expr" and args:
                    try:
                        expr_id = int(args[0])
                        await self.nekobot_set_expression(expr_id)
                    except ValueError:
                        console.print("[red]✗ Invalid expression ID[/red]")

                elif command == "neko-buzzer" and args:
                    state = args[0].lower() in ["on", "1", "true"]
                    await self.nekobot_set_buzzer(state)

                elif command == "neko-status":
                    if self.nekobot.is_connected:
                        await self.nekobot.request_status()
                    else:
                        console.print("[red]✗ NekoBot not connected[/red]")

                elif command == "neko-gas":
                    if self.nekobot.is_connected:
                        await self.nekobot.request_gas_level()
                    else:
                        console.print("[red]✗ NekoBot not connected[/red]")

                elif command == "neko-reset":
                    if self.nekobot.is_connected:
                        await self.nekobot.reset()
                    else:
                        console.print("[red]✗ NekoBot not connected[/red]")

                else:
                    console.print(f"[red]✗ Unknown command: {command}[/red]")
                    console.print("[cyan]Type 'help' for available commands[/cyan]")

            except KeyboardInterrupt:
                console.print("[yellow]\nInterrupt received[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")

        # Cleanup
        await self.cleanup()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        console.print("[yellow]Cleaning up…[/yellow]")
        await self.bt.disconnect_from_device()
        await self.comms.disconnect_from_device()
        await self.nekobot.disconnect()
        console.print("[green]✓ Goodbye![/green]")


@click.command()
@click.option('--interactive', '-i', is_flag=True, help='Run in interactive mode')
@click.option('--scan', is_flag=True, help='Scan for Bluetooth devices')
@click.option('--bt-connect', type=str, help='Connect to device by address')
def main(interactive, scan, bt_connect):
    """DeskBuddy - Terminal-based ESP32 Manager"""
    cli = DeskBuddyCLI()

    async def run():
        if scan:
            await cli.scan_bluetooth()
            return

        if bt_connect:
            await cli.connect_bluetooth_by_address(bt_connect)
            return

        # Default to interactive mode
        await cli.run_interactive()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()

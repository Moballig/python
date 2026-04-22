# DeskBuddy - Terminal Edition

A terminal-based Python implementation of the DeskBuddy application for managing ESP32 Bluetooth connectivity, WiFi provisioning, and sending alerts over TCP/WebSocket.

## Features

- ✅ **Bluetooth Scanning & Connection** - Discover and connect to nearby Bluetooth devices
- ✅ **WiFi Provisioning** - Send WiFi credentials to ESP32 over Bluetooth
- ✅ **Alert System** - Send development, system, and wellness alerts over TCP
- ✅ **System Monitoring** - Cross-platform CPU, temperature, and idle time tracking
- ✅ **NekoBot Control** - Control NekoBot robot via TCP (expressions, buzzer, status monitoring)
- ✅ **Interactive CLI** - User-friendly terminal interface with rich formatting

## Requirements

- Python 3.8+
- Linux, macOS, or Windows with Bluetooth support

### Linux (Arch)

```bash
sudo pacman -S python python-pip bluez bluez-libs xorg-xprintidle
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install python3 python3-pip libbluetooth-dev xprintidle
```

### Windows

- Python 3.8+
- Bluetooth hardware with driver support

## Installation

```bash
# Clone or copy the project
cd deskbuddy-python

# Install dependencies
pip install -r requirements.txt

# Make the main script executable (Linux/macOS)
chmod +x main.py
```

## Usage

### Interactive Mode (Default)

```bash
python main.py
```

This opens an interactive CLI where you can type commands.

### Available Commands

#### Bluetooth Management

```
scan                        # Scan for Bluetooth devices
connect <index>             # Connect to device by index
bt-status                   # Show current Bluetooth status
```

#### WiFi Provisioning

```
provision <ssid> <password> # Send WiFi credentials to ESP32
```

#### Alert System

```
tcp-connect <host> [port]   # Connect to ESP32 over TCP (default port 8080)
tcp-disconnect              # Disconnect from TCP
send-dev                    # Send a development alert
send-system                 # Send a system vital alert
send-wellness               # Send a wellness reminder
```

#### NekoBot Control

```
neko-connect <host> [port]  # Connect to NekoBot (default port 9090)
neko-expr <0-4>             # Set expression (0=Normal, 1=Happy, 2=Talking, 3=Sleeping, 4=Worried)
neko-buzzer <on|off>        # Control the buzzer
neko-status                 # Request full status
neko-gas                    # Check gas sensor level
neko-reset                  # Reset NekoBot
```

#### General

```
status                      # Show connection status
help                        # Display detailed help
quit / exit                 # Exit the application
```

### Example Workflow

```
> scan
> connect 0                 # Connect to first device
> provision MyNetwork mypassword
> tcp-connect 192.168.1.100
> send-system               # Send a system alert
> status
> quit
```

## Module Architecture

```
deskbuddy/
├── __init__.py
├── bluetooth_manager.py      # Bluetooth Classic RFCOMM handling
├── comms_manager.py          # TCP/WebSocket communication
├── wifi_provisioner.py       # WiFi credential handshake
├── notification_manager.py   # Cross-platform alerts & monitoring
└── nekobot_manager.py        # NekoBot TCP client
```

### Use as a Library

```python
import asyncio
from deskbuddy import BluetoothManager, CommsManager, WiFiProvisioner

async def main():
    bt = BluetoothManager()
    await bt.start_scan()
    devices = bt.get_discovered_devices()

    if devices:
        device = devices[0]
        await bt.connect_to_device(device.address)
        # ... send WiFi credentials, etc.

asyncio.run(main())
```

## Cross-Platform Support

### CPU Monitoring

- **Windows**: Windows Performance Data Helper (PDH)
- **Linux**: `/proc/stat` delta calculation
- **macOS**: Limited support (requires psutil)

### CPU Temperature

- **Windows**: Requires LibreHardwareMonitor driver
- **Linux**: `/sys/class/thermal/thermal_zoneN/temp`
- **macOS**: Limited support

### Idle Time Detection

- **Windows**: Windows API `GetLastInputInfo()`
- **Linux**: `xprintidle` utility
- **macOS**: Limited support

## Logging

Logs are written to `deskbuddy.log` in the current directory and also printed to stderr at INFO level.

You can change the logging level by editing `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # More verbose
```

## Differences from C++ Version

| Feature      | C++ Version     | Python CLI       |
| ------------ | --------------- | ---------------- |
| GUI          | Qt6 with 3 tabs | Rich terminal UI |
| System Tray  | Yes             | No (CLI only)    |
| Bluetooth    | Qt Native       | Bleak library    |
| Network      | Qt sockets      | asyncio          |
| Python       | N/A             | Native           |
| Installation | Qt6 build tools | pip install      |

## Troubleshooting

### "No module named 'bleak'"

```bash
pip install bleak
```

### Bluetooth permission denied (Linux)

```bash
sudo usermod -aG bluetooth $USER
# Log out and back in
```

### xprintidle not found (Linux)

```bash
# Arch
sudo pacman -S xorg-xprintidle

# Ubuntu
sudo apt install xprintidle
```

### Connection timeouts

- Ensure ESP32 is powered on and advertising
- Check WiFi network availability
- Verify correct IP address and port

## Future Enhancements

- [ ] GUI mode using `curses` or `blessed`
- [ ] Persistent configuration file
- [ ] WebSocket support (currently stubbed)
- [ ] Command scripting/automation
- [ ] SQLite logging of alerts
- [ ] Discord/Slack webhook integration
- [ ] Advanced TUI with mouse support

## License

Same as the original DeskBuddy project.

## References

- [Bleak Documentation](https://bleak.readthedocs.io/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

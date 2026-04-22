# Quick Start Guide

## Installation (5 minutes)

### 1. Install Python 3.8+

Check if Python is installed:

```bash
python3 --version
```

### 2. Install Dependencies

```bash
# Navigate to the project directory
cd /path/to/deskbuddy-python

# Install required packages
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python main.py
```

## First Run

When you start the application, you'll see an interactive prompt:

```
>
```

### Workflow: Bluetooth → WiFi → Alerts

```bash
# Step 1: Scan for devices
> scan

# Step 2: Connect to your ESP32 (usually index 0)
> connect 0

# Step 3: Send WiFi credentials
> provision MyNetworkName MyPassword123

# Step 4: Connect over TCP (IP from provisioning or your router)
> tcp-connect 192.168.1.100

# Step 5: Send a test alert
> send-system

# View status anytime
> status

# Exit when done
> quit
```

## Common Tasks

### Just Scan for Devices

```bash
> scan
> quit
```

### Run an Example Script

```bash
python examples/bluetooth_scan.py
python examples/complete_workflow.py
python examples/nekobot_control.py
```

### Edit Configuration

Edit the IP addresses and ports in `main.py` or pass them via commands:

```bash
> tcp-connect 192.168.1.42 8080
> neko-connect 192.168.1.100 9090
```

## Troubleshooting

### "No module named 'bleak'"

```bash
pip install bleak
```

### "No devices found" when scanning

- Ensure your ESP32 is powered on and advertising Bluetooth
- Check if your system's Bluetooth is enabled
- Try scanning again with longer timeout

### Permission Denied on Linux

```bash
sudo usermod -aG bluetooth $USER
# Log out and log back in
```

### Connection Refused

- Check if the ESP32 is running the correct firmware
- Verify the IP address is correct
- Ensure firewall allows the port (default 8080 for TCP, 9090 for NekoBot)

## Using as a Library

Instead of the CLI, you can use DeskBuddy as a Python library:

```python
import asyncio
from deskbuddy import BluetoothManager

async def main():
    bt = BluetoothManager()
    await bt.start_scan()
    devices = bt.get_discovered_devices()
    print(f"Found {len(devices)} devices")

asyncio.run(main())
```

See `examples/` directory for more library usage examples.

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [examples/](examples/) directory for more code samples
- Review [deskbuddy/](deskbuddy/) modules for API reference
- Set up logging by editing main.py (change `logging.INFO` to `logging.DEBUG`)

## Need Help?

Run the help command anytime:

```bash
> help
```

Check the log file for detailed error information:

```bash
tail -f deskbuddy.log
```

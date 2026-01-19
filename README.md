# Griddle Temperature Monitor

A real-time web app for monitoring griddle/grill temperature using **Tuya ZFX-WT01/WT02** WiFi temperature probes. Built with Flask, WebSockets, and Chart.js.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Real-time temperature display** - Fahrenheit/Celsius with live updates
- **Live temperature graph** - 30-minute history with smooth curves
- **Time-to-target prediction** - Estimates when you'll reach cooking temp
- **Configurable alarms** - Ready, too hot, too low alerts
- **Audio + browser notifications** - Never miss an alarm
- **Mobile-friendly** - Responsive design, wake lock prevents screen sleep
- **Auto-discovery** - Finds device IP automatically (handles DHCP changes)
- **Local communication** - Talks directly to device, no cloud required after setup

## Supported Devices

| Device | Sensor Type | Use Case |
|--------|-------------|----------|
| **ZFX-WT01** | K-type thermocouple | High-temp cooking (grills, smokers) |
| **ZFX-WT02** | NTC thermistor | General purpose |

The app **auto-detects** your device type and applies the correct settings.

## Quick Start

### Prerequisites

Before you begin, you need:
1. A **ZFX-WT01 or ZFX-WT02** temperature probe
2. The probe connected to WiFi via the **Tuya Smart** or **Smart Life** app
3. A **Tuya IoT Platform** developer account (free) - see [First-Time Tuya Setup](#first-time-tuya-setup) below

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/lucapinello/griddle-monitor.git
cd griddle-monitor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Get your device credentials (see First-Time Tuya Setup below)
python -m tinytuya wizard

# 4. Start the app
python app.py
```

Open http://localhost:5001 in your browser (or http://YOUR_IP:5001 from phone/tablet).

---

## First-Time Tuya Setup

This one-time setup gets the credentials needed to communicate with your device locally.

### Step 1: Create Tuya IoT Account

1. Go to [iot.tuya.com](https://iot.tuya.com/) and create a free account
2. Create a **Cloud Project**:
   - Click "Cloud" → "Create Cloud Project"
   - Name: anything (e.g., "Griddle Monitor")
   - Industry: "Smart Home"
   - Development Method: "Smart Home"
   - Data Center: Choose your region (us, eu, cn)

### Step 2: Link Your Mobile App

1. In your Tuya IoT project, go to **Devices** → **Link Tuya App Account**
2. Click "Add App Account" and scan the QR code with your **Tuya Smart** or **Smart Life** app
3. Your devices should now appear in the Tuya IoT console

### Step 3: Get API Credentials

1. In your project, go to **Overview**
2. Copy your **Access ID** and **Access Secret**

### Step 4: Run the Wizard

```bash
python -m tinytuya wizard
```

When prompted:
- Enter your **Access ID**
- Enter your **Access Secret**
- Enter your **region** (us, eu, or cn)
- Choose "Y" to poll cloud for devices

This creates `devices.json` with your device credentials. **The app reads this automatically** - no further configuration needed!

---

## Common Scenarios

### Adding a New Device

If you buy a new probe:

1. Add it to your WiFi via the Tuya Smart/Smart Life app
2. Re-run the wizard to update `devices.json`:
   ```bash
   python -m tinytuya wizard
   ```
3. Restart the app - it will auto-detect the new device

### Replacing a Broken Device

If you replace a device:

1. Remove the old device from your Tuya app
2. Add the new device via the Tuya app
3. Re-run the wizard:
   ```bash
   python -m tinytuya wizard
   ```
4. Restart the app

### Multiple Temperature Probes

The app **automatically uses the first WT01/WT02** it finds in `devices.json`.

If you have multiple probes and want to use a specific one:

```bash
# By name (partial match)
TUYA_DEVICE_NAME="Kitchen" python app.py

# By index in devices.json (0 = first, 1 = second, etc.)
TUYA_DEVICE_INDEX=1 python app.py
```

For systemd service, add to `griddle-monitor.service`:
```ini
Environment=TUYA_DEVICE_NAME=Kitchen
```

### Wrong Temperature Reading

If temperature shows 2.5°C instead of 25°C, force the device type:

```bash
# WT01 (K-type thermocouple) - temperature returned directly
TUYA_DEVICE_TYPE="wt01" python app.py

# WT02 (NTC thermistor) - temperature divided by 10
TUYA_DEVICE_TYPE="wt02" python app.py
```

---

## Raspberry Pi

For Raspberry Pi installation with auto-start on boot, see **[RASPBERRY_PI.md](RASPBERRY_PI.md)**.

Includes:
- Python 3.7 compatibility fixes
- Systemd service setup
- Raspbian Buster archived repository fixes

---

## Troubleshooting

### Device not found on network

1. Make sure your probe is powered on and connected to WiFi
2. Run a network scan:
   ```bash
   python -m tinytuya scan
   ```
3. If not found, the device may have a new IP - the app will auto-rescan

### "Local key expired" or connection refused

Your device credentials changed (e.g., you re-paired the device). Re-run the wizard:
```bash
python -m tinytuya wizard
```

### Port 5000 in use (macOS)

macOS uses port 5000 for AirPlay. This app uses port **5001** instead.

### Alarms not working on mobile

Mobile browsers require user interaction before playing audio. **Tap anywhere on the page** after loading to enable sounds.

---

## Advanced Configuration

### Environment Variables

All optional - the app works without any of these:

| Variable | Description |
|----------|-------------|
| `TUYA_DEVICE_NAME` | Select device by name (partial match) |
| `TUYA_DEVICE_INDEX` | Select device by index in devices.json |
| `TUYA_DEVICE_TYPE` | Force device type: `wt01` or `wt02` |
| `TUYA_VERSION` | Protocol version: `3.4` or `3.5` |
| `TUYA_DEVICE_ID` | Device ID (bypasses devices.json) |
| `TUYA_LOCAL_KEY` | Local key (required with DEVICE_ID) |

### Data Points (DPS)

| DPS | Description |
|-----|-------------|
| 101 | Temperature (raw value from device) |
| 102 | Humidity (divide by 10 for %) |
| 119 | Temperature unit setting ("c" or "f") |

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  ZFX-WT01/02    │────▶│  Flask Backend  │────▶│  Browser UI     │
│  (Tuya device)  │     │  + WebSocket    │     │  (Chart.js)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   Local WiFi            Polls every 2s          Real-time updates
                         SocketIO events          via WebSocket
```

## File Structure

```
griddle-monitor/
├── app.py                    # Flask backend
├── requirements.txt          # Python 3.8+ dependencies
├── requirements-rpi.txt      # Python 3.7 dependencies
├── devices.json              # Your device credentials (generated)
├── griddle-monitor.service   # Systemd service for auto-start
├── templates/index.html      # Web UI
└── static/
    ├── app.js                # Frontend logic
    └── style.css             # Styling
```

## Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **Device Communication**: TinyTuya (local network)
- **Real-time Updates**: WebSocket (Socket.IO)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [TinyTuya](https://github.com/jasonacox/tinytuya) - Local Tuya device communication
- [Chart.js](https://www.chartjs.org/) - Beautiful charts
- [NoSleep.js](https://github.com/richtr/NoSleep.js) - Wake lock for mobile

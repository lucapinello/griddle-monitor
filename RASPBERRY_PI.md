# Raspberry Pi Setup Guide

Complete installation guide for running Griddle Monitor on a Raspberry Pi with auto-start on boot.

**Prerequisites:** Before starting, complete the [First-Time Tuya Setup](README.md#first-time-tuya-setup) in the main README to get your device credentials.

## Tested Configurations

| OS | Python | Status |
|----|--------|--------|
| Raspbian Buster | 3.7.x | Works with `requirements-rpi.txt` |
| Volumio (Buster-based) | 3.7.x | Works with `requirements-rpi.txt` |
| Raspbian Bullseye | 3.9.x | Works with `requirements.txt` |
| Raspbian Bookworm | 3.11.x | Works with `requirements.txt` |

## Prerequisites

- Raspberry Pi (any model with WiFi)
- Raspbian Buster, Bullseye, or newer (also works on Volumio, DietPi, etc.)
- Python 3.7 or newer
- ZFX-WT01 or ZFX-WT02 temperature probe on the same network

---

## Installation

### Step 1: Fix Apt Repositories (Buster Only)

If you're on Raspbian Buster and `apt update` fails with 404 errors, the repositories have been archived:

```bash
# Edit main sources
sudo nano /etc/apt/sources.list
# Change: http://raspbian.raspberrypi.org/raspbian
# To:     http://legacy.raspbian.org/raspbian

# Edit raspi sources
sudo nano /etc/apt/sources.list.d/raspi.list
# Change: http://archive.raspberrypi.org/debian
# To:     http://legacy.raspberrypi.org/debian

# Update
sudo apt update
```

### Step 2: Install System Dependencies

```bash
sudo apt update
sudo apt install python3-venv python3-pip git -y
```

### Step 3: Clone and Setup Virtual Environment

```bash
cd ~
git clone https://github.com/lucapinello/griddle-monitor.git
cd griddle-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip (required for older systems)
pip install --upgrade pip setuptools wheel
```

If pip upgrade fails on Python 3.7, use get-pip directly:
```bash
curl https://bootstrap.pypa.io/pip/3.7/get-pip.py -o get-pip.py
python get-pip.py
```

### Step 4: Install Python Dependencies

**For Python 3.8+ (Bullseye, Bookworm):**
```bash
pip install -r requirements.txt
```

**For Python 3.7 (Buster, Volumio):**
```bash
pip install -r requirements-rpi.txt
```

### Step 5: Configure Device Credentials

If you haven't already, complete the [First-Time Tuya Setup](README.md#first-time-tuya-setup), then run:

```bash
python -m tinytuya wizard
```

Enter your Access ID, Access Secret, and region. This creates `devices.json` - the app reads it automatically.

### Step 6: Test the Application

```bash
python app.py
```

Visit `http://<raspberry-pi-ip>:5001` in your browser. Press Ctrl+C to stop.

---

## Auto-Start on Boot (Systemd Service)

### Step 1: Edit the Service File

First, check your username:
```bash
whoami
```

If your username is not `pi`, edit the service file:
```bash
nano griddle-monitor.service
```

Replace all instances of `pi` with your username (e.g., `volumio`).

### Step 2: Install the Service

```bash
sudo cp griddle-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable griddle-monitor
sudo systemctl start griddle-monitor
```

### Step 3: Verify

```bash
sudo systemctl status griddle-monitor
```

Visit `http://<raspberry-pi-ip>:5001` - it should now auto-start on every boot.

---

## Service Management

| Command | Description |
|---------|-------------|
| `sudo systemctl status griddle-monitor` | Check if running |
| `sudo systemctl start griddle-monitor` | Start the service |
| `sudo systemctl stop griddle-monitor` | Stop the service |
| `sudo systemctl restart griddle-monitor` | Restart after changes |
| `sudo systemctl disable griddle-monitor` | Disable auto-start |
| `sudo journalctl -u griddle-monitor -f` | View live logs |
| `sudo journalctl -u griddle-monitor --since "10 min ago"` | Recent logs |

---

## Troubleshooting

### Service Won't Start

Check the logs:
```bash
sudo journalctl -u griddle-monitor -n 50 --no-pager
```

Verify paths exist:
```bash
ls -la /home/pi/griddle-monitor/app.py
/home/pi/griddle-monitor/venv/bin/python --version
```

### Permission Denied

Make sure the service User/Group matches your actual username:
```bash
whoami  # Use this value in the service file
```

### Device Not Found

```bash
cd ~/griddle-monitor
source venv/bin/activate
python -m tinytuya scan
```

### Port Already in Use

The app uses port 5001. Check if something else is using it:
```bash
sudo lsof -i :5001
```

### Flask 3.0 Error on Python 3.7

If you see `Could not find a version that satisfies the requirement flask>=3.0.0`:
```bash
pip install -r requirements-rpi.txt
```

### SocketIO AttributeError

If you see `AttributeError: type object 'Server' has no attribute 'reason'`, you have mismatched SocketIO versions:
```bash
pip uninstall flask-socketio python-socketio python-engineio -y
pip install -r requirements-rpi.txt
```

### Temperature Reading is Wrong / Multiple Devices

See [Common Scenarios](README.md#common-scenarios) in the main README.

For systemd service, add environment variables to `griddle-monitor.service`:
```ini
[Service]
Environment=TUYA_DEVICE_TYPE=wt01
# or
Environment=TUYA_DEVICE_NAME=Kitchen
```

Then restart: `sudo systemctl restart griddle-monitor`

---

## Known Issues on Older Systems

### Issue: Raspbian Buster Repository Deprecated

**Error:**
```
E: The repository 'http://raspbian.raspberrypi.org/raspbian buster Release' no longer has a Release file.
```

**Solution:** See Step 1 above - update apt sources to use legacy URLs.

### Issue: Flask 3.0+ Requires Python 3.8+

**Error:**
```
Could not find a version that satisfies the requirement flask>=3.0.0
```

**Solution:** Use `requirements-rpi.txt` which pins Flask 2.2.5.

### Issue: Ancient Pip Cannot Parse Modern TOML

**Error:**
```
pytoml.core.TomlError: heterogenous_array
```

**Solution:** Upgrade pip before installing packages (see Step 3).

#!/usr/bin/env python3
"""
Griddle Temperature Monitor
Real-time temperature monitoring web app for ZFX-WT02 device.
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
import tinytuya
import threading
import time
import json
import os
from collections import deque
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'griddle-monitor-secret'
socketio = SocketIO(app, cors_allowed_origins="*")


def load_device_config():
    """Load device configuration from devices.json or environment variables."""
    # Try environment variables first
    device_id = os.environ.get('TUYA_DEVICE_ID')
    local_key = os.environ.get('TUYA_LOCAL_KEY')
    version = float(os.environ.get('TUYA_VERSION', '3.4'))

    if device_id and local_key:
        return device_id, local_key, version

    # Fall back to devices.json
    devices_file = os.path.join(os.path.dirname(__file__), 'devices.json')
    if os.path.exists(devices_file):
        with open(devices_file, 'r') as f:
            devices = json.load(f)
            if devices:
                device = devices[0]  # Use first device
                return device['id'], device['key'], float(device.get('version', 3.4))

    raise ValueError(
        "No device configuration found. Either:\n"
        "  1. Run 'python -m tinytuya wizard' to create devices.json, or\n"
        "  2. Set TUYA_DEVICE_ID and TUYA_LOCAL_KEY environment variables"
    )


# Device configuration
DEVICE_ID, LOCAL_KEY, VERSION = load_device_config()

# Current device IP (discovered automatically)
device_ip = None

# Temperature history (30 minutes at 2-second intervals = 900 readings)
MAX_HISTORY = 900
temperature_history = deque(maxlen=MAX_HISTORY)

# Polling control
polling_active = True
consecutive_errors = 0
scan_in_progress = False


def discover_device_ip():
    """Scan network to find device IP by device ID."""
    global device_ip, scan_in_progress

    if scan_in_progress:
        return device_ip  # Don't start another scan

    scan_in_progress = True
    print(f"Scanning network for device {DEVICE_ID}...")

    try:
        devices = tinytuya.deviceScan(verbose=False, maxretry=2)
        for ip, info in devices.items():
            if info.get('gwId') == DEVICE_ID:
                device_ip = ip
                print(f"Found device at {ip}")
                scan_in_progress = False
                return ip
        print("Device not found in scan")
        scan_in_progress = False
        return None
    except Exception as e:
        print(f"Scan error: {e}")
        scan_in_progress = False
        return None


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9/5) + 32


def get_device_status():
    """Connect to device and read status."""
    global device_ip, consecutive_errors

    # If scan is in progress, return scanning state
    if scan_in_progress:
        return {'scanning': True}

    if not device_ip:
        discover_device_ip()
        if not device_ip:
            return {'Error': 'Device not found on network'}

    try:
        device = tinytuya.Device(
            dev_id=DEVICE_ID,
            address=device_ip,
            local_key=LOCAL_KEY,
            version=VERSION
        )
        device.set_socketTimeout(3)
        status = device.status()

        # Check for connection errors
        if 'Error' in status and '901' in str(status.get('Err', '')):
            consecutive_errors += 1
            if consecutive_errors >= 3:
                print("Multiple connection failures, re-scanning network...")
                device_ip = None
                consecutive_errors = 0
                discover_device_ip()
        else:
            consecutive_errors = 0

        return status
    except Exception as e:
        consecutive_errors += 1
        if consecutive_errors >= 3:
            print("Multiple connection failures, re-scanning network...")
            device_ip = None
            consecutive_errors = 0
        return {'Error': str(e)}


def poll_temperature():
    """Background thread to poll temperature and emit updates."""
    global polling_active

    while polling_active:
        status = get_device_status()

        # If scanning, emit scanning state and skip
        if status.get('scanning'):
            socketio.emit('temperature_update', {
                'scanning': True,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            time.sleep(2)
            continue

        if 'dps' in status:
            dps = status['dps']
            temp_c = dps.get('101', 0) / 10
            temp_f = celsius_to_fahrenheit(temp_c)
            humidity = dps.get('102', 0) / 10

            timestamp = datetime.now().strftime('%H:%M')

            # Store in history
            temperature_history.append({
                'time': timestamp,
                'temp_f': round(temp_f, 1),
                'temp_c': round(temp_c, 1),
                'humidity': round(humidity, 1)
            })

            # Emit to all connected clients
            socketio.emit('temperature_update', {
                'temp_f': round(temp_f, 1),
                'temp_c': round(temp_c, 1),
                'humidity': round(humidity, 1),
                'timestamp': timestamp
            })
        else:
            # Emit error state
            socketio.emit('temperature_update', {
                'error': status.get('Error', 'Unknown error'),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })

        time.sleep(2)


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection - send history."""
    # Send temperature history to new client
    socketio.emit('history', list(temperature_history))


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    pass


@socketio.on('rescan')
def handle_rescan():
    """Handle rescan request from client."""
    global device_ip
    print("Rescan requested by client...")
    device_ip = None
    new_ip = discover_device_ip()
    if new_ip:
        socketio.emit('rescan_result', {'success': True, 'ip': new_ip})
    else:
        socketio.emit('rescan_result', {'success': False, 'error': 'Device not found'})


def start_polling():
    """Start the background polling thread."""
    thread = threading.Thread(target=poll_temperature, daemon=True)
    thread.start()


if __name__ == '__main__':
    print("Starting Griddle Temperature Monitor...")
    print(f"Device ID: {DEVICE_ID}")
    print("Discovering device on network...")
    discover_device_ip()
    if device_ip:
        print(f"Device found at {device_ip}")
    else:
        print("Warning: Device not found, will retry during polling")
    start_polling()
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)

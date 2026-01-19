#!/usr/bin/env python3
"""
Griddle Temperature Monitor
Real-time temperature monitoring web app for ZFX-WT01/WT02 devices.
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
import tinytuya
import threading
import time
import json
import os
import re
from collections import deque
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'griddle-monitor-secret'
socketio = SocketIO(app, cors_allowed_origins="*")


# Device type configurations
# WT01: K-type thermocouple, returns temperature directly (no division needed)
# WT02: NTC thermistor, returns temperature * 10
DEVICE_PROFILES = {
    'wt01': {
        'name': 'ZFX-WT01 (K-type thermocouple)',
        'temp_divisor': 1,      # Temperature returned directly
        'humidity_divisor': 10,
        'default_version': 3.5,
    },
    'wt02': {
        'name': 'ZFX-WT02 (NTC thermistor)',
        'temp_divisor': 10,     # Temperature * 10
        'humidity_divisor': 10,
        'default_version': 3.4,
    },
}


def detect_device_type(device_info):
    """Detect device type from device info (name, model, product_name)."""
    # Check various fields for device type indicators
    fields_to_check = [
        device_info.get('name', ''),
        device_info.get('model', ''),
        device_info.get('product_name', ''),
    ]

    combined = ' '.join(fields_to_check).upper()

    if 'WT01' in combined or 'WT-01' in combined:
        return 'wt01'
    elif 'WT02' in combined or 'WT-02' in combined:
        return 'wt02'

    # Default to wt02 for backward compatibility
    return 'wt02'


def is_temperature_probe(device_info):
    """Check if a device is a supported temperature probe (WT01/WT02)."""
    fields_to_check = [
        device_info.get('name', ''),
        device_info.get('model', ''),
        device_info.get('product_name', ''),
    ]
    combined = ' '.join(fields_to_check).upper()
    return 'WT01' in combined or 'WT-01' in combined or 'WT02' in combined or 'WT-02' in combined


def find_device_in_list(devices, device_name=None, device_index=None):
    """Find a device in the devices list by name, index, or auto-detect."""
    if not devices:
        return None

    # If device_name specified, search for it
    if device_name:
        device_name_lower = device_name.lower()
        for device in devices:
            name = device.get('name', '').lower()
            model = device.get('model', '').lower()
            product_name = device.get('product_name', '').lower()
            device_id = device.get('id', '').lower()

            if (device_name_lower in name or
                device_name_lower in model or
                device_name_lower in product_name or
                device_name_lower == device_id):
                return device

        print(f"Warning: Device '{device_name}' not found")

    # If device_index specified, use it
    if device_index is not None:
        if 0 <= device_index < len(devices):
            return devices[device_index]
        else:
            print(f"Warning: Device index {device_index} out of range")

    # Auto-detect: find the first temperature probe device (WT01/WT02)
    for device in devices:
        if is_temperature_probe(device):
            print(f"Auto-detected temperature probe: {device.get('name', device.get('id'))}")
            return device

    # No temperature probe found, show available devices and fail gracefully
    print("No ZFX-WT01/WT02 temperature probe found in devices.json")
    print("Available devices:")
    for i, d in enumerate(devices):
        print(f"  [{i}] {d.get('name', 'Unknown')} ({d.get('product_name', d.get('id'))})")
    print("\nUse TUYA_DEVICE_INDEX=N to select a specific device")

    return None


def load_device_config():
    """
    Load device configuration from environment variables or devices.json.

    Environment variables:
        TUYA_DEVICE_ID: Device ID (required if not using devices.json)
        TUYA_LOCAL_KEY: Local key (required if not using devices.json)
        TUYA_VERSION: Protocol version (default: auto-detect or 3.5)
        TUYA_DEVICE_TYPE: Force device type ('wt01' or 'wt02')
        TUYA_DEVICE_NAME: Select device by name from devices.json
        TUYA_DEVICE_INDEX: Select device by index from devices.json (0-based)
    """
    # Check for direct device credentials in environment
    device_id = os.environ.get('TUYA_DEVICE_ID')
    local_key = os.environ.get('TUYA_LOCAL_KEY')
    env_version = os.environ.get('TUYA_VERSION')
    env_device_type = os.environ.get('TUYA_DEVICE_TYPE', '').lower()

    if device_id and local_key:
        # Using environment variables directly
        device_type = env_device_type if env_device_type in DEVICE_PROFILES else 'wt02'
        profile = DEVICE_PROFILES[device_type]
        version = float(env_version) if env_version else profile['default_version']

        return {
            'id': device_id,
            'key': local_key,
            'version': version,
            'type': device_type,
            'profile': profile,
        }

    # Fall back to devices.json
    devices_file = os.path.join(os.path.dirname(__file__), 'devices.json')
    if os.path.exists(devices_file):
        with open(devices_file, 'r') as f:
            devices = json.load(f)

            if devices:
                # Find device by name or index
                device_name = os.environ.get('TUYA_DEVICE_NAME')
                device_index_str = os.environ.get('TUYA_DEVICE_INDEX')
                device_index = int(device_index_str) if device_index_str else None

                device = find_device_in_list(devices, device_name, device_index)

                if not device:
                    raise ValueError(
                        "No compatible temperature probe found in devices.json.\n"
                        "Supported devices: ZFX-WT01, ZFX-WT02\n"
                        "Use TUYA_DEVICE_INDEX=N to select a specific device from the list above."
                    )

                if device:
                    # Auto-detect device type or use environment override
                    if env_device_type in DEVICE_PROFILES:
                        device_type = env_device_type
                    else:
                        device_type = detect_device_type(device)

                    profile = DEVICE_PROFILES[device_type]

                    # Use version from device, env, or profile default
                    if env_version:
                        version = float(env_version)
                    elif device.get('version'):
                        version = float(device['version'])
                    else:
                        version = profile['default_version']

                    return {
                        'id': device['id'],
                        'key': device['key'],
                        'version': version,
                        'type': device_type,
                        'profile': profile,
                        'name': device.get('name', 'Unknown'),
                    }

    raise ValueError(
        "No device configuration found. Either:\n"
        "  1. Run 'python -m tinytuya wizard' to create devices.json, or\n"
        "  2. Set TUYA_DEVICE_ID and TUYA_LOCAL_KEY environment variables\n"
        "\n"
        "Optional environment variables:\n"
        "  TUYA_DEVICE_NAME  - Select device by name from devices.json\n"
        "  TUYA_DEVICE_INDEX - Select device by index (0-based)\n"
        "  TUYA_DEVICE_TYPE  - Force device type: 'wt01' or 'wt02'\n"
        "  TUYA_VERSION      - Protocol version (e.g., '3.4' or '3.5')"
    )


# Load device configuration
DEVICE_CONFIG = load_device_config()
DEVICE_ID = DEVICE_CONFIG['id']
LOCAL_KEY = DEVICE_CONFIG['key']
VERSION = DEVICE_CONFIG['version']
DEVICE_TYPE = DEVICE_CONFIG['type']
DEVICE_PROFILE = DEVICE_CONFIG['profile']

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
            # Use device profile for correct divisors
            temp_c = dps.get('101', 0) / DEVICE_PROFILE['temp_divisor']
            temp_f = celsius_to_fahrenheit(temp_c)
            humidity = dps.get('102', 0) / DEVICE_PROFILE['humidity_divisor']

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
    print(f"Device: {DEVICE_CONFIG.get('name', 'Unknown')}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Device Type: {DEVICE_PROFILE['name']}")
    print(f"Protocol Version: {VERSION}")
    print(f"Temperature Divisor: {DEVICE_PROFILE['temp_divisor']}")
    print("Discovering device on network...")
    discover_device_ip()
    if device_ip:
        print(f"Device found at {device_ip}")
    else:
        print("Warning: Device not found, will retry during polling")
    start_polling()
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)

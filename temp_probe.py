#!/usr/bin/env python3
"""
ZFX-WT02 Temperature Probe
Reads temperature from the Tuya ZFX-WT02 device.
"""

import tinytuya
import json
import time

# Device configuration
DEVICE_ID = "eb4c567f712d29939ctxw3"
LOCAL_KEY = "R$8(xl*fX;&f5iA@"
VERSION = 3.4


def discover_device_ip():
    """Scan network to find device IP by device ID."""
    print("Scanning network for device...")
    try:
        devices = tinytuya.deviceScan(verbose=False, maxretry=2)
        for ip, info in devices.items():
            if info.get('gwId') == DEVICE_ID:
                print(f"Found device at {ip}")
                return ip
        print("Device not found in scan")
        return None
    except Exception as e:
        print(f"Scan error: {e}")
        return None


def get_temperature():
    """Connect to device and read temperature."""
    device_ip = discover_device_ip()
    if not device_ip:
        return {'Error': 'Device not found on network'}

    device = tinytuya.Device(
        dev_id=DEVICE_ID,
        address=device_ip,
        local_key=LOCAL_KEY,
        version=VERSION
    )
    device.set_socketTimeout(5)

    # Get status
    status = device.status()
    return status


def main():
    print("ZFX-WT02 Temperature Probe")
    print("=" * 40)

    status = get_temperature()

    if 'Error' in status:
        print(f"Error: {status['Error']}")
        print(f"Details: {status.get('Err', 'Unknown')}")
        return

    if 'dps' in status:
        dps = status['dps']

        # ZFX-WT02 Data Point mappings (values divided by 10)
        temp = dps.get('101', 0) / 10
        humidity = dps.get('102', 0) / 10
        unit = dps.get('119', 'c').upper()
        mode = dps.get('115', 'unknown')

        print(f"\nTemperature: {temp}°{unit}")
        print(f"Humidity:    {humidity}%")
        print(f"Mode:        {mode}")

        # Additional info
        print(f"\n--- All Data Points ---")
        for dp_id, value in sorted(dps.items(), key=lambda x: int(x[0])):
            print(f"  DP {dp_id}: {value}")


if __name__ == "__main__":
    main()

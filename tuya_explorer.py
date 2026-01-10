#!/usr/bin/env python3
"""
Tuya ZFX-WT02 Device Explorer
Discover and interact with your Tuya device to see what it exposes.
"""

import tinytuya
import json
import time

# =============================================================================
# CONFIGURATION - Fill these in from your Tuya IoT Platform
# =============================================================================
# Get these from: https://iot.tuya.com/ -> Cloud -> Your Project -> Devices

DEVICE_ID = "YOUR_DEVICE_ID"           # e.g., "bf1234567890abcdef"
DEVICE_IP = "YOUR_DEVICE_IP"           # e.g., "192.168.1.100" (or use scanner)
LOCAL_KEY = "YOUR_LOCAL_KEY"           # 16-character key from Tuya IoT Platform
API_REGION = "us"                       # us, eu, cn, in

# For cloud API access (optional but useful for getting device info)
API_KEY = "YOUR_API_KEY"               # Access ID from Tuya IoT Platform
API_SECRET = "YOUR_API_SECRET"         # Access Secret from Tuya IoT Platform


def scan_network():
    """Scan local network for Tuya devices."""
    print("\n" + "="*60)
    print("SCANNING NETWORK FOR TUYA DEVICES...")
    print("="*60)

    devices = tinytuya.deviceScan(verbose=True)

    if devices:
        print(f"\nFound {len(devices)} device(s):")
        for ip, info in devices.items():
            print(f"\n  IP: {ip}")
            print(f"  Device ID: {info.get('gwId', 'N/A')}")
            print(f"  Product Key: {info.get('productKey', 'N/A')}")
            print(f"  Version: {info.get('version', 'N/A')}")
    else:
        print("No devices found. Make sure devices are on the same network.")

    return devices


def get_device_status(device):
    """Get current status/state from device."""
    print("\n" + "="*60)
    print("GETTING DEVICE STATUS...")
    print("="*60)

    status = device.status()
    print(f"\nRaw status response:")
    print(json.dumps(status, indent=2))

    if 'dps' in status:
        print("\n--- Data Points (DPS) ---")
        for dp_id, value in status['dps'].items():
            print(f"  DP {dp_id}: {value} ({type(value).__name__})")

    return status


def get_device_info(device):
    """Get device properties and capabilities."""
    print("\n" + "="*60)
    print("GETTING DEVICE PROPERTIES...")
    print("="*60)

    # Try to get device properties
    try:
        props = device.updatedps()
        print(f"\nUpdated DPS response: {props}")
    except Exception as e:
        print(f"Could not get updated DPS: {e}")


def poll_device(device, duration=30, interval=2):
    """Poll device for changes over time."""
    print("\n" + "="*60)
    print(f"POLLING DEVICE FOR {duration} SECONDS...")
    print("(Change device state to see updates)")
    print("="*60)

    start = time.time()
    last_status = None

    while time.time() - start < duration:
        status = device.status()

        if status != last_status:
            print(f"\n[{time.strftime('%H:%M:%S')}] Status changed:")
            if 'dps' in status:
                for dp_id, value in status['dps'].items():
                    print(f"  DP {dp_id}: {value}")
            last_status = status

        time.sleep(interval)


def test_set_value(device, dp_id, value):
    """Test setting a data point value."""
    print(f"\nSetting DP {dp_id} to {value}...")
    result = device.set_value(dp_id, value)
    print(f"Result: {result}")
    return result


def explore_all_dps(device):
    """Try to discover all available data points."""
    print("\n" + "="*60)
    print("EXPLORING DATA POINTS...")
    print("="*60)

    # Request update on common DP ranges
    # ZFX-WT02 likely uses DPs in range 1-20 for temp/humidity sensors
    print("\nRequesting DPS updates for common ranges...")

    try:
        # Try to force device to report all DPs
        device.updatedps([1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                         11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                         101, 102, 103, 104, 105])
        time.sleep(1)
        status = device.status()

        if 'dps' in status:
            print("\nDiscovered Data Points:")
            print("-" * 40)

            # Common ZFX-WT02 DPS mappings (may vary)
            dp_names = {
                1: "Switch/Power",
                2: "Temperature Set Point",
                3: "Current Temperature",
                4: "Mode",
                5: "Eco Mode",
                6: "Lock",
                7: "Heating Status",
                8: "Schedule",
                9: "Unknown",
                10: "Fault",
                13: "Max Temp",
                14: "Min Temp",
                15: "Unknown",
                16: "Current Humidity",
                17: "Humidity Set Point",
                18: "Temperature Unit",
                19: "Temperature Calibration",
                101: "Unknown Extended",
                102: "Unknown Extended",
            }

            for dp_id, value in sorted(status['dps'].items(), key=lambda x: int(x[0])):
                name = dp_names.get(int(dp_id), "Unknown")
                print(f"  DP {dp_id:>3}: {str(value):>15}  ({name})")

    except Exception as e:
        print(f"Error exploring DPS: {e}")


def cloud_api_info():
    """Get device info from Tuya Cloud API."""
    print("\n" + "="*60)
    print("CLOUD API DEVICE INFO")
    print("="*60)

    if API_KEY == "YOUR_API_KEY":
        print("Skipping cloud API (credentials not configured)")
        return

    try:
        cloud = tinytuya.Cloud(
            apiRegion=API_REGION,
            apiKey=API_KEY,
            apiSecret=API_SECRET,
            apiDeviceID=DEVICE_ID
        )

        # Get device info
        result = cloud.getdevices()
        print("\nDevices from cloud:")
        print(json.dumps(result, indent=2))

        # Get device status from cloud
        status = cloud.getstatus(DEVICE_ID)
        print("\nCloud status:")
        print(json.dumps(status, indent=2))

        # Get device functions/capabilities
        functions = cloud.getfunctions(DEVICE_ID)
        print("\nDevice functions/capabilities:")
        print(json.dumps(functions, indent=2))

        # Get device properties
        props = cloud.getproperties(DEVICE_ID)
        print("\nDevice properties:")
        print(json.dumps(props, indent=2))

    except Exception as e:
        print(f"Cloud API error: {e}")


def main():
    print("="*60)
    print("  TUYA ZFX-WT02 DEVICE EXPLORER")
    print("="*60)

    # Step 1: Scan network if IP unknown
    if DEVICE_IP == "YOUR_DEVICE_IP":
        print("\nDevice IP not configured. Running network scan...")
        devices = scan_network()
        print("\nUpdate DEVICE_IP in the script and re-run.")
        return

    # Step 2: Connect to device
    print(f"\nConnecting to device...")
    print(f"  Device ID: {DEVICE_ID}")
    print(f"  IP: {DEVICE_IP}")

    # Create device object - try different device types
    # The ZFX-WT02 is likely a standard device or outlet type
    device = tinytuya.Device(
        dev_id=DEVICE_ID,
        address=DEVICE_IP,
        local_key=LOCAL_KEY,
        version=3.3  # Most modern Tuya devices use 3.3 or 3.4
    )

    # Set socket timeout
    device.set_socketTimeout(5)

    # Step 3: Get device status
    get_device_status(device)

    # Step 4: Explore all data points
    explore_all_dps(device)

    # Step 5: Get cloud info (if configured)
    cloud_api_info()

    # Step 6: Poll for changes
    print("\n" + "="*60)
    print("INTERACTIVE OPTIONS:")
    print("="*60)
    print("1. Poll device for 30 seconds")
    print("2. Test setting a value")
    print("3. Exit")

    choice = input("\nChoice (1/2/3): ").strip()

    if choice == "1":
        poll_device(device)
    elif choice == "2":
        dp = input("Enter DP ID: ").strip()
        val = input("Enter value: ").strip()
        # Try to convert to appropriate type
        if val.lower() in ['true', 'false']:
            val = val.lower() == 'true'
        elif val.isdigit():
            val = int(val)
        test_set_value(device, dp, val)
        time.sleep(1)
        get_device_status(device)


if __name__ == "__main__":
    main()

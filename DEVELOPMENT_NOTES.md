# Development Notes - Griddle Temperature Monitor

This document contains detailed technical notes about the development of the Griddle Temperature Monitor web app. It serves as a reference for future development sessions.

## Project Overview

A real-time web application for monitoring griddle temperature using a Tuya ZFX-WT02 temperature probe. The app provides live temperature display, historical graphing, and configurable alarms.

## Device Information

- **Device**: ZFX-WT02 WiFi Temperature/Humidity Probe
- **Device ID**: `eb4c567f712d29939ctxw3`
- **Local Key**: `R$8(xl*fX;&f5iA@`
- **Protocol Version**: 3.4
- **Communication**: TinyTuya library (local network, no cloud required)

### Data Points (DPS)

| DPS | Description | Format |
|-----|-------------|--------|
| 101 | Temperature | Integer, divide by 10 for °C |
| 102 | Humidity | Integer, divide by 10 for % |
| 119 | Temperature unit | String: "c" or "f" |

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  ZFX-WT02       │────▶│  Flask Backend  │────▶│  Browser UI     │
│  (Tuya device)  │     │  + WebSocket    │     │  (Chart.js)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   Local WiFi            Polls every 2s          Real-time updates
                         SocketIO events          via WebSocket
```

## Key Features Implemented

### 1. Real-time Temperature Display
- Large temperature readout in Fahrenheit (primary) and Celsius (secondary)
- Humidity display
- Color-coded background based on temperature range:
  - Blue (cold): < 150°F
  - Orange (warm): 150-300°F
  - Red (hot): 300-400°F
  - Dark red with pulse (danger): > 400°F

### 2. Temperature Graph
- Chart.js line graph showing 30 minutes of history
- Thick line (3px) without data point dots
- Target temperature line (dashed orange) when target alarm is enabled
- Time labels in HH:MM format (no seconds)

### 3. Time-to-Target Prediction
- Calculates estimated time to reach target temperature
- Uses multiple time windows (1, 2, 3 minutes) for rate calculation
- Confidence levels: high (consistent rate), medium, low (erratic)
- Hidden when target is reached or temperature is cooling

### 4. Configurable Alarms
- **Ready at**: Notifies when griddle reaches target cooking temperature
- **Too hot**: Warns when temperature exceeds maximum safe limit
- **Too low**: Alerts if temperature drops below minimum (after reaching it)
- Audio beep (440Hz sine wave) + browser notifications
- Alarm notification bar appears between chart and config section
- Alarms reset when temperature crosses back through threshold

### 5. Auto-Discovery
- Automatically finds device IP by scanning network for device ID
- Handles DHCP IP address changes gracefully
- Re-scans automatically after 3 consecutive connection failures
- Manual "Rescan Network" button for user-triggered discovery

### 6. Mobile Optimizations
- Responsive design works on phone/tablet/desktop
- Wake Lock API prevents phone from sleeping while monitoring
- Touch-friendly toggle switches and buttons

## Implementation Details

### Backend (app.py)

**Key globals:**
- `device_ip`: Current discovered IP (None if not found)
- `scan_in_progress`: Prevents concurrent network scans
- `consecutive_errors`: Tracks failures to trigger re-scan
- `temperature_history`: Deque of last 900 readings (30 min at 2s intervals)

**Socket events:**
- `temperature_update`: Emitted every 2 seconds with temp data
- `history`: Sent on client connect with historical data
- `rescan`: Client requests network scan
- `rescan_result`: Server responds with scan result

**Error handling:**
- 3-second socket timeout for fast failure detection
- After 3 consecutive errors, triggers automatic re-scan
- Returns `{scanning: true}` during scan to prevent UI errors

### Frontend (static/app.js)

**Alarm state tracking:**
```javascript
const alarms = {
    target: { enabled: false, temp: 350, triggered: false },
    max: { enabled: false, temp: 450, triggered: false },
    min: { enabled: false, temp: 300, triggered: false, wasAbove: false }
};
```

**Chart configuration:**
- `tension: 0.3` for smooth curves
- `pointRadius: 0` to hide all dots
- `pointHoverRadius: 0` to prevent hover dots
- `pointHitRadius: 10` for click detection
- Target line as second dataset when alarm enabled

**Time prediction algorithm:**
1. Samples temperature at 1, 2, and 3 minute intervals
2. Calculates rate of change (°F/min) for each window
3. Uses average rate if values are consistent (within 20%)
4. Reports confidence based on rate consistency

### Styling (static/style.css)

**Color scheme:**
- Primary accent: `#ff6b35` (orange)
- Success: `#44bb44` (green)
- Danger: `#ff4444` (red)
- Warning: `#ffaa00` (amber)
- Background: Dark gradient `#1a1a2e` to `#16213e`

**Responsive breakpoints:**
- Mobile: < 480px (stacked alarm rows)
- Tablet/Desktop: > 768px (larger temperature display)

## Issues Encountered and Solutions

### 1. Port 5000 Conflict
**Problem**: macOS uses port 5000 for AirPlay Receiver.
**Solution**: Changed to port 5001.

### 2. Device IP Changes
**Problem**: Device gets new IP from DHCP, breaking connection.
**Solution**: Implemented auto-discovery that scans by device ID, not IP.

### 3. Status Bar Stuck on Error
**Problem**: "Device Error" status never cleared after recovery.
**Solution**: Added explicit `statusEl.textContent = 'Connected'` on success.

### 4. Race Condition During Scan
**Problem**: Polling continued during rescan, causing errors.
**Solution**: Added `scan_in_progress` flag; return `{scanning: true}` to frontend.

### 5. Alarms Only Trigger Once
**Problem**: After first trigger, alarms never fire again.
**Solution**: Reset `triggered` flag when temperature crosses back through threshold.

### 6. Chart Font Compression
**Problem**: Chart fonts appeared squeezed/compressed.
**Solution**: Explicit font family, proper `devicePixelRatio`, correct container sizing.

### 7. X-axis Labels Outside Chart
**Problem**: Time labels were cut off at bottom.
**Solution**: Adjusted chart container height and `layout.padding`.

### 8. Browser Caching Old JavaScript
**Problem**: Browser cached old app.js, changes not visible.
**Solution**: Added cache-busting query param: `app.js?v=2.2`

### 9. Mobile Audio Not Playing
**Problem**: Alarm sounds don't play on iOS/Android browsers.
**Cause**: Mobile browsers require user interaction before playing audio. AudioContext starts in "suspended" state.
**Solution**:
- Added `setupAudioUnlock()` that listens for first tap/click on page
- On first interaction, creates AudioContext, resumes it, and plays a silent sound to fully unlock
- `playAlarmSound()` now calls `audioContext.resume()` before playing
- Made sounds louder (0.5 gain) and longer (3 beeps, 1.3 seconds)

### 10. Audio Stops Working After Screen Lock/Unlock
**Problem**: After locking and unlocking the phone, alarm sounds stop working.
**Cause**: iOS suspends the AudioContext when the page is backgrounded. On return, it remains suspended and requires user interaction to resume.
**Solution**:
- Added `visibilitychange` event listener to detect when page returns from background
- When audio context is suspended after return, show a "Tap to enable alarm sounds" overlay
- User taps overlay, which re-unlocks audio and plays confirmation beep
- Only shows prompt if alarms are enabled

### 11. Screen Locks While Monitoring
**Problem**: Phone screen turns off during monitoring, missing alarms.
**Cause**: The native Wake Lock API has limited support and can be overridden.
**Solution**:
- Integrated NoSleep.js library (https://github.com/richtr/NoSleep.js)
- NoSleep uses Wake Lock API when available
- Falls back to playing a tiny looping video (browsers keep screen on for video)
- Enabled on first user interaction (tap/click)
- Works on iOS, Android, and desktop browsers

## Future Improvements (Not Implemented)

- Temperature logging to file/database
- Multiple device support
- Custom alarm sounds
- Temperature presets for different foods
- Historical data viewing (past days)
- HTTPS support for secure notifications

## Tuya Setup Reference

To get device credentials:

1. Create account at https://iot.tuya.com/
2. Create a Cloud Project (choose "Smart Home" and your region)
3. Go to Devices > Link Tuya App Account
4. Get QR code and scan with Tuya Smart/Smart Life app
5. Run `python -m tinytuya wizard` with:
   - Access ID from Tuya project
   - Access Secret from Tuya project
   - Region code (us, eu, cn)
6. This generates `devices.json` with Device ID and Local Key

## Testing Checklist

- [ ] Temperature displays and updates every 2 seconds
- [ ] Graph shows smooth line with no dots
- [ ] Target line appears when alarm enabled
- [ ] Prediction shows when heating toward target
- [ ] Alarms trigger with sound and notification
- [ ] Alarms can re-trigger after temperature crosses back
- [ ] Rescan button appears on connection error
- [ ] Wake lock keeps phone screen on
- [ ] Works on mobile viewport
- [ ] Works after device IP change

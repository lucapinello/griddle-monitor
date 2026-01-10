// Griddle Monitor - Frontend Logic
// v2.4 - NoSleep + iOS audio fix

// WebSocket connection
const socket = io();

// NoSleep.js instance - prevents screen from sleeping
let noSleep = null;

// Audio context for alert sounds (must be unlocked by user interaction on iOS)
let audioContext = null;
let audioUnlocked = false;

// Initialize NoSleep.js to prevent screen from sleeping
function initNoSleep() {
    if (typeof NoSleep !== 'undefined') {
        noSleep = new NoSleep();
        console.log('NoSleep.js initialized');
    } else {
        console.log('NoSleep.js not available');
    }
}

// Enable NoSleep - must be called from user interaction
function enableNoSleep() {
    if (noSleep && !noSleep.isEnabled) {
        noSleep.enable();
        console.log('NoSleep enabled - screen will stay on');
    }
}

// Create or get audio context
function getAudioContext() {
    if (!audioContext) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
            audioContext = new AudioContextClass();
        }
    }
    return audioContext;
}

// Check if audio needs to be re-enabled (after screen lock/unlock)
function checkAudioState() {
    if (audioContext && audioContext.state === 'suspended') {
        audioUnlocked = false;
        return false;
    }
    return audioUnlocked;
}

// Show the audio prompt overlay
function showAudioPrompt() {
    document.getElementById('audio-prompt').classList.add('visible');
}

// Hide the audio prompt overlay
function hideAudioPrompt() {
    document.getElementById('audio-prompt').classList.remove('visible');
}

// Unlock audio on user interaction (required for iOS Safari)
// Must be called synchronously during a touch/click event
function unlockAudio() {
    try {
        const ctx = getAudioContext();
        if (!ctx) return false;

        // Resume if suspended (iOS starts in suspended state)
        if (ctx.state === 'suspended') {
            ctx.resume();
        }

        // Play a real oscillator to fully unlock iOS audio
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.frequency.value = 200;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.001; // Nearly silent

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        oscillator.start();
        oscillator.stop(ctx.currentTime + 0.1);

        audioUnlocked = true;
        console.log('Audio unlocked for iOS');

        // Hide prompt if it was showing
        hideAudioPrompt();

        return true;
    } catch (e) {
        console.log('Audio unlock failed:', e);
        return false;
    }
}

// Play a short confirmation beep when enabling an alarm
// This serves dual purpose: unlocks audio AND confirms to user that sound works
function playConfirmationBeep() {
    try {
        const ctx = getAudioContext();
        if (!ctx) return;

        // Resume if suspended
        if (ctx.state === 'suspended') {
            ctx.resume();
        }

        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.15;

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        oscillator.start();
        // Quick fade out
        gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
        oscillator.stop(ctx.currentTime + 0.1);

        audioUnlocked = true;
        hideAudioPrompt();
    } catch (e) {
        console.log('Confirmation beep failed:', e);
    }
}

// Handle user interaction - unlock audio and enable NoSleep
function handleUserInteraction() {
    // Enable NoSleep on first interaction
    enableNoSleep();

    // Unlock audio
    unlockAudio();
}

// Add unlock listener to user interactions
function setupAudioUnlock() {
    // Use touchend for iOS (touchstart can be canceled by scrolling)
    // Use click for desktop
    const unlockEvents = ['touchend', 'click'];

    unlockEvents.forEach(event => {
        document.addEventListener(event, handleUserInteraction, { passive: true });
    });

    // Setup audio prompt click handler
    document.getElementById('audio-prompt').addEventListener('click', () => {
        unlockAudio();
        playConfirmationBeep();
    });

    // When page becomes visible again, check if audio needs re-unlock
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            console.log('Page visible, checking audio state...');

            // Give iOS a moment to update the audio context state
            setTimeout(() => {
                if (audioContext && audioContext.state === 'suspended') {
                    audioUnlocked = false;
                    console.log('Audio context suspended after return - showing prompt');

                    // Check if any alarms are enabled - only show prompt if needed
                    if (alarms.target.enabled || alarms.max.enabled || alarms.min.enabled) {
                        showAudioPrompt();
                    }
                } else if (audioContext && audioContext.state === 'running') {
                    console.log('Audio context still running');
                    hideAudioPrompt();
                }
            }, 100);
        }
    });
}

// Chart setup
let tempChart;
const chartData = {
    labels: [],
    datasets: [
        {
            label: 'Temperature (°F)',
            data: [],
            borderColor: '#ff6b35',
            backgroundColor: 'rgba(255, 107, 53, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 0,
            pointHitRadius: 10,
            order: 1
        },
        {
            label: 'Target',
            data: [],
            borderColor: '#44bb44',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 0,
            pointHoverRadius: 0,
            fill: false,
            order: 0
        }
    ]
};

// Alarm state
const alarms = {
    target: { enabled: false, temp: 350, triggered: false },
    max: { enabled: false, temp: 450, triggered: false },
    min: { enabled: false, temp: 300, triggered: false, wasAbove: false }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    initAlarmControls();
    initRescanButton();
    initNotificationDismiss();
    requestNotificationPermission();
    initNoSleep();  // NoSleep is enabled on first user interaction
    setupAudioUnlock();
});

// Request notification permission
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// Initialize Chart.js
function initChart() {
    const ctx = document.getElementById('temp-chart').getContext('2d');
    tempChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            devicePixelRatio: window.devicePixelRatio || 1,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            layout: {
                padding: { left: 0, right: 5, top: 5, bottom: 0 }
            },
            scales: {
                x: {
                    display: true,
                    title: { display: false },
                    ticks: {
                        maxTicksLimit: 6,
                        color: '#aaa',
                        font: {
                            size: 12,
                            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                        },
                        maxRotation: 0
                    },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: '°F',
                        color: '#aaa',
                        font: {
                            size: 12,
                            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                        }
                    },
                    ticks: {
                        color: '#aaa',
                        font: {
                            size: 12,
                            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                        },
                        padding: 4
                    },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    suggestedMin: 50,
                    suggestedMax: 500
                }
            },
            plugins: {
                legend: { display: false }
            },
            animation: { duration: 0 }
        }
    });
}

// Initialize rescan button
function initRescanButton() {
    const btn = document.getElementById('rescan-btn');
    btn.addEventListener('click', () => {
        btn.textContent = 'Scanning...';
        btn.classList.add('scanning');
        btn.disabled = true;
        socket.emit('rescan');
    });
}

// Initialize notification dismiss button
function initNotificationDismiss() {
    document.getElementById('alarm-notification-dismiss').addEventListener('click', dismissNotification);
}

// Update target line on chart
function updateTargetLine() {
    const targetDataset = chartData.datasets[1];

    if (alarms.target.enabled && chartData.labels.length > 0) {
        // Create array of target temp values matching the labels length
        targetDataset.data = chartData.labels.map(() => alarms.target.temp);
    } else {
        targetDataset.data = [];
    }

    if (tempChart) {
        tempChart.update('none'); // Update without animation
    }
}

// Initialize alarm controls
function initAlarmControls() {
    // Target alarm
    document.getElementById('target-enabled').addEventListener('change', (e) => {
        alarms.target.enabled = e.target.checked;
        alarms.target.triggered = false;
        updateAlarmUI('target');
        updateTargetLine();
        updateTimePrediction();
        // Play confirmation beep when enabled (also unlocks iOS audio)
        if (e.target.checked) {
            playConfirmationBeep();
        }
    });
    document.getElementById('target-temp').addEventListener('change', (e) => {
        alarms.target.temp = parseInt(e.target.value);
        alarms.target.triggered = false;
        updateTargetLine();
        updateTimePrediction();
    });

    // Max alarm
    document.getElementById('max-enabled').addEventListener('change', (e) => {
        alarms.max.enabled = e.target.checked;
        alarms.max.triggered = false;
        updateAlarmUI('max');
        if (e.target.checked) {
            playConfirmationBeep();
        }
    });
    document.getElementById('max-temp').addEventListener('change', (e) => {
        alarms.max.temp = parseInt(e.target.value);
        alarms.max.triggered = false;
    });

    // Min alarm
    document.getElementById('min-enabled').addEventListener('change', (e) => {
        alarms.min.enabled = e.target.checked;
        alarms.min.triggered = false;
        updateAlarmUI('min');
        if (e.target.checked) {
            playConfirmationBeep();
        }
    });
    document.getElementById('min-temp').addEventListener('change', (e) => {
        alarms.min.temp = parseInt(e.target.value);
        alarms.min.triggered = false;
    });
}

// Update alarm row UI
function updateAlarmUI(type) {
    const row = document.getElementById(`alarm-${type}`);
    const enabled = alarms[type].enabled;
    row.classList.toggle('enabled', enabled);
}

// Socket.IO event handlers
socket.on('connect', () => {
    document.getElementById('connection-status').textContent = 'Connected';
    document.getElementById('connection-status').classList.add('connected');
});

socket.on('disconnect', () => {
    document.getElementById('connection-status').textContent = 'Disconnected';
    document.getElementById('connection-status').classList.remove('connected');
});

socket.on('history', (history) => {
    // Load historical data into chart
    history.forEach(point => {
        chartData.labels.push(point.time);
        chartData.datasets[0].data.push(point.temp_f);
    });
    // Keep last 150 points for display (5 minutes)
    if (chartData.labels.length > 150) {
        chartData.labels = chartData.labels.slice(-150);
        chartData.datasets[0].data = chartData.datasets[0].data.slice(-150);
    }
    tempChart.update();
    updateTargetLine();
    updateTimePrediction();
});

socket.on('rescan_result', (data) => {
    const btn = document.getElementById('rescan-btn');
    btn.classList.remove('scanning');
    btn.disabled = false;

    if (data.success) {
        btn.textContent = 'Found: ' + data.ip;
        setTimeout(() => {
            btn.textContent = 'Rescan Network';
            btn.classList.remove('visible');
        }, 3000);
    } else {
        btn.textContent = 'Not Found - Retry';
        setTimeout(() => {
            btn.textContent = 'Rescan Network';
        }, 2000);
    }
});

socket.on('temperature_update', (data) => {
    const rescanBtn = document.getElementById('rescan-btn');
    const statusEl = document.getElementById('connection-status');

    // Handle scanning state - don't show error, just wait
    if (data.scanning) {
        statusEl.textContent = 'Scanning...';
        statusEl.classList.remove('connected');
        return;
    }

    if (data.error) {
        document.getElementById('current-temp').textContent = 'ERR';
        statusEl.textContent = 'Device Error';
        statusEl.classList.remove('connected');
        rescanBtn.classList.add('visible');
        return;
    }

    // Success - reset status and hide rescan button
    statusEl.textContent = 'Connected';
    statusEl.classList.add('connected');
    rescanBtn.classList.remove('visible');
    rescanBtn.textContent = 'Rescan Network';

    // Update display
    document.getElementById('current-temp').textContent = data.temp_f.toFixed(1);
    document.getElementById('current-temp-c').textContent = data.temp_c.toFixed(1);
    document.getElementById('current-humidity').textContent = data.humidity.toFixed(1);
    document.getElementById('last-update').textContent = data.timestamp;

    // Update chart
    chartData.labels.push(data.timestamp);
    chartData.datasets[0].data.push(data.temp_f);

    // Keep last 150 points
    if (chartData.labels.length > 150) {
        chartData.labels.shift();
        chartData.datasets[0].data.shift();
    }

    // Update target line if enabled
    if (alarms.target.enabled) {
        chartData.datasets[1].data.push(alarms.target.temp);
        if (chartData.datasets[1].data.length > 150) {
            chartData.datasets[1].data.shift();
        }
    }

    tempChart.update();

    // Check alarms
    checkAlarms(data.temp_f);

    // Update time prediction
    updateTimePrediction();

    // Update temperature display color based on temp
    updateTempDisplayColor(data.temp_f);
});

// Calculate time to reach target temperature
function calculateTimeToTarget() {
    const data = chartData.datasets[0].data;
    const minPoints = 30; // Need at least 1 minute of data (30 points at 2s intervals)

    if (!alarms.target.enabled || data.length < minPoints) {
        return { minutes: null, confidence: 'none' };
    }

    const currentTemp = data[data.length - 1];
    const targetTemp = alarms.target.temp;

    // Already at or above target
    if (currentTemp >= targetTemp) {
        return { minutes: 0, confidence: 'high' };
    }

    // Calculate rates over multiple time windows for robustness
    const windows = [30, 60, 90]; // 1, 2, 3 minutes worth of data
    const rates = [];

    for (const windowSize of windows) {
        if (data.length >= windowSize) {
            const startTemp = data[data.length - windowSize];
            const endTemp = data[data.length - 1];
            const tempChange = endTemp - startTemp;
            const timeMinutes = (windowSize * 2) / 60; // 2 seconds per point
            const rate = tempChange / timeMinutes; // °F per minute

            if (rate > 0) {
                rates.push(rate);
            }
        }
    }

    // Not heating or not enough positive rates
    if (rates.length === 0) {
        return { minutes: null, confidence: 'none' };
    }

    // Use average rate
    const avgRate = rates.reduce((a, b) => a + b, 0) / rates.length;

    // Too slow (less than 1°F per minute)
    if (avgRate < 1) {
        return { minutes: null, confidence: 'low' };
    }

    // Calculate variance to determine confidence
    let confidence = 'high';
    if (rates.length >= 2) {
        const variance = rates.reduce((sum, r) => sum + Math.pow(r - avgRate, 2), 0) / rates.length;
        const stdDev = Math.sqrt(variance);
        const coeffOfVariation = stdDev / avgRate;

        if (coeffOfVariation > 0.5) {
            confidence = 'low';
        } else if (coeffOfVariation > 0.25) {
            confidence = 'medium';
        }
    }

    // Calculate time to target
    const tempToGo = targetTemp - currentTemp;
    const minutesToTarget = tempToGo / avgRate;

    // Sanity check - if more than 30 minutes, too uncertain
    if (minutesToTarget > 30 || minutesToTarget < 0) {
        return { minutes: null, confidence: 'none' };
    }

    return { minutes: Math.round(minutesToTarget), confidence };
}

// Update the time prediction display
function updateTimePrediction() {
    const separatorEl = document.getElementById('prediction-separator');
    const textEl = document.getElementById('prediction-text');

    // No target alarm enabled - hide prediction part
    if (!alarms.target.enabled) {
        separatorEl.classList.remove('visible');
        textEl.classList.add('hidden');
        textEl.classList.remove('low-confidence');
        return;
    }

    const prediction = calculateTimeToTarget();

    // Already at or above target - hide prediction (alarm notification handles this)
    if (prediction.minutes === 0) {
        separatorEl.classList.remove('visible');
        textEl.classList.add('hidden');
        return;
    }

    // Show the separator and prediction
    separatorEl.classList.add('visible');
    textEl.classList.remove('hidden');

    if (prediction.minutes === null) {
        if (prediction.confidence === 'low') {
            textEl.textContent = 'heating slowly';
        } else {
            textEl.textContent = 'calculating...';
        }
        textEl.classList.add('low-confidence');
    } else {
        const minText = prediction.minutes === 1 ? 'min' : 'min';
        textEl.textContent = `reaching ${alarms.target.temp}°F in ~${prediction.minutes} ${minText}`;
        textEl.classList.toggle('low-confidence', prediction.confidence === 'low');
    }
}

// Check alarm thresholds
function checkAlarms(tempF) {
    // Target alarm (ready to cook)
    if (alarms.target.enabled) {
        if (tempF >= alarms.target.temp) {
            if (!alarms.target.triggered) {
                alarms.target.triggered = true;
                triggerAlarm('target', `Ready! Reached ${alarms.target.temp}°F`);
            }
        } else {
            // Reset when temp drops below target (allows re-triggering)
            alarms.target.triggered = false;
        }
    }

    // Max alarm (too hot)
    if (alarms.max.enabled) {
        if (tempF > alarms.max.temp) {
            if (!alarms.max.triggered) {
                alarms.max.triggered = true;
                triggerAlarm('max', `TOO HOT! Over ${alarms.max.temp}°F`);
            }
        } else {
            alarms.max.triggered = false;
        }
    }

    // Min alarm (dropped too low)
    if (alarms.min.enabled) {
        if (tempF >= alarms.min.temp) {
            alarms.min.wasAbove = true;
            // Reset when temp is back above min (allows re-triggering)
            alarms.min.triggered = false;
        }
        if (alarms.min.wasAbove && tempF < alarms.min.temp && !alarms.min.triggered) {
            alarms.min.triggered = true;
            triggerAlarm('min', `Dropped below ${alarms.min.temp}°F!`);
        }
    }

    // Update status indicators
    updateAlarmStatuses(tempF);
}

// Update alarm status indicators
function updateAlarmStatuses(tempF) {
    // Target status
    const targetStatus = document.getElementById('target-status');
    if (alarms.target.enabled) {
        if (tempF >= alarms.target.temp) {
            targetStatus.textContent = 'READY';
            targetStatus.className = 'alarm-status triggered';
        } else {
            const diff = alarms.target.temp - tempF;
            targetStatus.textContent = `${diff.toFixed(0)}° to go`;
            targetStatus.className = 'alarm-status pending';
        }
    } else {
        targetStatus.textContent = '';
        targetStatus.className = 'alarm-status';
    }

    // Max status
    const maxStatus = document.getElementById('max-status');
    if (alarms.max.enabled) {
        if (tempF > alarms.max.temp) {
            maxStatus.textContent = 'TOO HOT';
            maxStatus.className = 'alarm-status danger';
        } else {
            const margin = alarms.max.temp - tempF;
            maxStatus.textContent = `${margin.toFixed(0)}° margin`;
            maxStatus.className = 'alarm-status safe';
        }
    } else {
        maxStatus.textContent = '';
        maxStatus.className = 'alarm-status';
    }

    // Min status
    const minStatus = document.getElementById('min-status');
    if (alarms.min.enabled) {
        if (tempF < alarms.min.temp) {
            minStatus.textContent = 'TOO LOW';
            minStatus.className = 'alarm-status warning';
        } else {
            minStatus.textContent = 'OK';
            minStatus.className = 'alarm-status safe';
        }
    } else {
        minStatus.textContent = '';
        minStatus.className = 'alarm-status';
    }
}

// Trigger an alarm - shows notification bar above chart
function triggerAlarm(type, message) {
    const notification = document.getElementById('alarm-notification');
    const textEl = document.getElementById('alarm-notification-text');

    textEl.textContent = message;
    notification.className = `alarm-notification active ${type}`;

    // Play sound
    playAlarmSound(type);

    // Browser notification
    showNotification(message);
}

// Dismiss notification bar
function dismissNotification() {
    document.getElementById('alarm-notification').classList.remove('active');
}

// Play alarm sound using Web Audio API
async function playAlarmSound(type) {
    try {
        const ctx = getAudioContext();
        if (!ctx) {
            console.log('No audio context available');
            return;
        }

        // Try to resume if suspended
        if (ctx.state === 'suspended') {
            console.log('Attempting to resume suspended audio context...');
            try {
                await ctx.resume();
            } catch (e) {
                console.log('Could not resume audio context (need user interaction)');
            }
        }

        // If still not running, audio won't play
        if (ctx.state !== 'running') {
            console.log('Audio context not running, state:', ctx.state);
            // Still try to play - iOS sometimes works anyway
        }

        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        // Different sounds for different alarms
        if (type === 'max') {
            // Urgent high-pitched beeps
            oscillator.frequency.value = 880;
            oscillator.type = 'square';
        } else if (type === 'target') {
            // Pleasant ding
            oscillator.frequency.value = 660;
            oscillator.type = 'sine';
        } else {
            // Warning tone
            oscillator.frequency.value = 440;
            oscillator.type = 'triangle';
        }

        gainNode.gain.value = 0.5;  // Louder for mobile

        oscillator.start();

        // Beep pattern - longer and louder for mobile
        setTimeout(() => gainNode.gain.value = 0, 250);
        setTimeout(() => gainNode.gain.value = 0.5, 350);
        setTimeout(() => gainNode.gain.value = 0, 600);
        setTimeout(() => gainNode.gain.value = 0.5, 700);
        setTimeout(() => gainNode.gain.value = 0, 950);
        setTimeout(() => gainNode.gain.value = 0.5, 1050);
        setTimeout(() => {
            gainNode.gain.value = 0;
            oscillator.stop();
        }, 1300);

        console.log('Alarm sound playing');

    } catch (e) {
        console.log('Audio playback failed:', e);
    }
}

// Show browser notification
function showNotification(message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Griddle Monitor', {
            body: message,
            icon: '/static/icon.png',
            requireInteraction: true
        });
    }
}

// Update temperature display color based on value
function updateTempDisplayColor(tempF) {
    const display = document.getElementById('temp-display');

    // Remove existing classes
    display.classList.remove('cold', 'warm', 'hot', 'danger');

    if (tempF < 200) {
        display.classList.add('cold');
    } else if (tempF < 350) {
        display.classList.add('warm');
    } else if (tempF < 450) {
        display.classList.add('hot');
    } else {
        display.classList.add('danger');
    }
}

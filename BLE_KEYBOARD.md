# BLE HID Gesture Keyboard - nRF54L15DK

BLE keyboard that converts TinyML gesture classifications to arrow keys.

## Quick Start

```bash
west build -b nrf54l15dk/nrf54l15/cpuapp . --pristine
west flash
# Press RESET button after flashing!
```

## Connect

1. Phone: Bluetooth → ON → Select "nRF Keyboard"
2. LED2 + LED4 ON = ready

## Re-pairing (if connection fails)

```bash
# Phone: Forget "nRF Keyboard" in Bluetooth settings
# Board:
nrfjprog --eraseall
west flash
# Press RESET, pair again
```

## Test with Buttons

| Button | Gesture | Key |
|--------|---------|-----|
| BTN1 | Swipe Up | ↑ |
| BTN2 | Swipe Down | ↓ |
| BTN3 | Swipe Left | ← |
| BTN4 | Swipe Right | → |

## TinyML Integration

```c
gesture_submit(GESTURE_SWIPE_UP, 0.95f);    // With confidence
gesture_submit_simple(GESTURE_SWIPE_LEFT);  // 100% confidence

if (gesture_hid_is_ready()) { /* connected */ }
```

### Gesture Types

```c
GESTURE_NONE        // Ignored
GESTURE_SWIPE_UP    // ↑
GESTURE_SWIPE_DOWN  // ↓
GESTURE_SWIPE_LEFT  // ←
GESTURE_SWIPE_RIGHT // →
GESTURE_TAP         // Enter
GESTURE_DOUBLE_TAP  // Space
```

## Configuration

```c
gesture_config_t config = {
    .confidence_threshold = 0.7f,  // Min confidence to accept
    .debounce_ms = 200,            // Min gap between gestures
    .key_hold_ms = 50,             // Key press duration
    .key_gap_ms = 25,              // Gap between repeats
    .key_repeat_count = 10,        // Keys per gesture
};
gesture_set_config(&config);
```

## LEDs

| LED | Meaning |
|-----|---------|
| LED1 blink | Running |
| LED2 on | HID ready |
| LED3 flash | Gesture sent |
| LED4 on | Connected |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Not visible | Reset board + toggle phone Bluetooth |
| Pairing fails | Forget on phone + erase board + reflash |
| Connects but no keys | Check LED2 ON, re-pair if needed |
| Was working, now fails | Forget on phone, reset board, pair again |

## Memory

```
Current: ~46 KB RAM / 188 KB available
```

---

Serial: `screen /dev/ttyACM0 115200` | Device name: change in `prj.conf` → `CONFIG_BT_DEVICE_NAME`
# EdgeAI Gesture Translation System — BLE Subsystem

## Overview

BLE keyboard subsystem that converts TinyML gesture classifications from the IMU into HID arrow key events. The system acts as a wireless keyboard, translating detected gestures into corresponding arrow key presses that can control any Bluetooth-enabled device.

## Architecture Integration

The BLE subsystem receives gesture classifications from the IMU gesture detection thread and translates them into HID keyboard events.

- BLE Connection Thread runs at priority 7 (COOPERATIVE)
- Handles Bluetooth connection management and pairing
- Processes HID service notifications
- Sends key events to connected device

## Subsystem Features

### HID Keyboard Service

The BLE subsystem implements standard HID (Human Interface Device) keyboard protocol allowing the nRF54L15 to appear as a wireless keyboard to any Bluetooth-enabled device including phones, tablets, computers, and smart TVs.

**Key press generation:**
- Each detected gesture triggers multiple rapid key presses
- Adjustable repeat count allows fine-tuning of cursor movement distance
- Separate repeat counts for vertical (UP/DOWN) and horizontal (LEFT/RIGHT) gestures
- Key hold duration controls how long each key remains pressed
- Gap between keys controls smoothness of repeated presses

### Gesture to Key Mapping

| Gesture Type | Arrow Key | Default Repeat Count |
|-------------|-----------|---------------------|
| UP | ↑ | 7 presses |
| DOWN | ↓ | 7 presses |
| LEFT | ← | 1 press |
| RIGHT | → | 1 press |
| TAP | Enter | 1 press |
| DOUBLE_TAP | Space | 1 press |

### Fine-Tuning Parameters

All timing and behavior parameters are configurable at compile time in ble_keyboard.c:

**DEFAULT_KEY_HOLD_MS equals 50**
- Controls how long each key press is held down before release
- Lower values (20-30ms) create faster, more responsive key presses
- Higher values (70-100ms) ensure key press is registered on slower devices
- Trade-off: Speed versus compatibility

**DEFAULT_KEY_GAP_MS equals 10**
- Time delay between consecutive key presses in a repeat sequence
- Lower values (5-10ms) create smooth continuous motion
- Higher values (20-50ms) create discrete stepped motion
- Trade-off: Smoothness versus perception of separate actions

**DEFAULT_KEY_REPEAT_COUNT equals 10**
- Default number of key presses sent for each gesture (fallback value)
- Used if gesture-specific counts not defined
- Higher values move cursor further per gesture

**DEFAULT_KEY_REPEAT_COUNT_VERT equals 7**
- Number of arrow up or arrow down key presses per UP/DOWN gesture
- Tuned for typical vertical scrolling distances in menus and lists
- Empirically determined to move approximately one menu item or list entry
- Adjust based on target application: increase for faster scrolling, decrease for fine control

**DEFAULT_KEY_REPEAT_COUNT_HORIZ equals 1**
- Number of arrow left or arrow right key presses per LEFT/RIGHT gesture
- Set to single press for precise horizontal navigation
- Single press prevents overshooting in horizontal menus or text cursor movement
- Increase to 3-5 for rapid side-scrolling applications like image galleries

**Rationale for asymmetric repeat counts:**
- Vertical gestures (UP/DOWN) typically used for scrolling through lists requiring multiple steps
- Horizontal gestures (LEFT/RIGHT) typically used for binary choices or single-step navigation
- Asymmetry matches common UI patterns in mobile apps and media players

### Timing Characteristics

**Key press sequence timing:**

Gesture detected 

↓ 

[Key Down] ─── 50ms (KEY_HOLD_MS) ──→ [Key Up]

↓

[Gap] ────────── 10ms (KEY_GAP_MS) ──→
↓

[Key Down] ─── 50ms ──→ [Key Up]

↓

Repeat for KEY_REPEAT_COUNT times
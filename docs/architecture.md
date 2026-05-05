# EdgeAI Gesture Translation System — System Architecture

## Table of Contents
- [Overview](#overview)
- [Hardware Configuration](#hardware-configuration)
- [Sensor Configuration](#sensor-configuration)
- [Motion Detection Interrupt](#motion-detection-interrupt)
- [Dual-Thread Architecture](#dual-thread-architecture)

## Overview

This document describes the IMU subsystem for the EdgeAI Gesture Translation System, implementing real-time gesture detection on the Nordic nRF54L15 DK using an LSM6DS3 6-axis accelerometer and gyroscope. The system uses a dual-thread architecture where a high-priority sampling thread continuously buffers sensor data while motion detection triggers capture gesture signatures spanning both pre-jolt and post-jolt data for machine learning inference.
```
┌─────────────────────────────────────────────────────────────────┐
│                     EdgeAI Gesture Translation                  │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ LSM6DS3  │───►│ nRF54L15 │───►│ BLE HID  │───►│  Phone   │   │
│  │   IMU    │I2C │  + ML    │    │ Keyboard │    │  Tablet  │   │
│  └──────────┘    └──────────┘    └──────────┘    │    PC    │   │
│   104 Hz           Inference        Arrow Keys   └──────────┘   │
│   6-axis           <50ms            ↑ ↓ ← →                     │
│                                                                 │
│  Hand Gesture → Motion Detection → ML Classification → Action   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

- Motion-triggered sampling that only perfrom inference on data when deliberate motion is detected
- Dual-thread architecture separating continuous buffering from event-driven processing
- Pre-jolt plus post-jolt data capture preserving anticipatory movements before the main gesture
- On-device ML inference using Random Forest classifier running entirely on the nRF54L15
- Ultra-low power consumption averaging 360 microamps enabling 25 plus days on CR2032 battery

### System Architecture

The LSM6DS3 IMU with accelerometer and gyroscope samples at 104 Hz output data rate. It connects via I2C bus at 400 kHz and sends motion interrupts via INT1 GPIO interrupt to the nRF54L15 MCU. Inside the MCU, a high-priority sampling thread reads sensor at 104Hz and writes to circular buffer of 300 samples overwriting oldest data. A normal-priority gesture detection thread waits for motion interrupt, copies pre-jolt data, collects post-jolt data, extracts features, and runs inference. Once the gesture is detected, coresponding action is performed on the target device via BLE

## Hardware Configuration

### LSM6DS3 Breakout Module

The LSM6DS3TR-C is a 6-axis inertial measurement unit combining a 3-axis accelerometer with selectable ranges of plus minus 2g 4g 8g 16g and a 3-axis gyroscope with selectable ranges of plus minus 245 500 1000 2000 degrees per second.

We use a breakout module because the LSM6DS3TR-C is only available as a bare die in LGA-14 package requiring PCB-level reflow soldering. The breakout board includes decoupling capacitors and pulls CS high for I2C mode.

Zephyr does not include an upstream LSM6DS3 driver so this project uses a modified lsm6dsl driver that is register-compatible with the WHO_AM_I register value changed from 0x6A to 0x69. The driver is located in drivers/lsm6ds3 directory.

### Communication Interface

We use I2C instead of SPI for the following reasons. I2C requires only 2 wires SDA plus SCL compared to 4 for SPI which needs MOSI MISO SCK CS. At 400 kHz I2C fast mode the bandwidth is sufficient since 6 channels times 2 bytes times 104 Hz equals 1.25 kbps which is less than 1 percent bus utilization. The utilization calculation is 1.25 kbps divided by 400 kbps equals 0.3 percent. SPI would be overkill for this application and requires more complex wiring.

The I2C controller used is i2c21 on P1.11 and P1.12 pins. The nRF54L15 DK has three GPIO ports P0 P1 P2. Port P2 is occupied by onboard SPI flash and not available. Pins P0.02 and P0.03 are NFC antenna pins not routed to GPIO headers by default. Pins P1.11 and P1.12 are free GPIO pins with i2c21 peripheral so we selected these.

The I2C address is 0x6A. The LSM6DS3 SAO slave address option pin selects between two addresses. When SAO equals LOW the address is 0x6A and when SAO equals HIGH the address is 0x6B. We tie SAO to GND to use address 0x6A avoiding the need for an external pull-up resistor.

### Pin Connections

Wiring between LSM6DS3 breakout and nRF54L15 DK Port 1 header is as follows. 

| Breakout Pin | DK Pin | Notes |
|-------------|--------|-------|
| VIN | VDD.IO | 3.3V power |
| GND | GND | Ground |
| SDA | P1.11 | I2C data |
| SCL | P1.12 | I2C clock |
| CS | VDD.IO (tie high) | Selects I2C mode over SPI |
| SAO | GND (tie low) | Sets I2C address to 0x6A |
| INT1 | P1.13 | Data-ready interrupt (trigger) |

**Note**: P1.02 and P1.03 are NFC pins on the nRF54L15 not available as standard GPIO. CS must be tied to VDD to enable I2C mode because pulled low selects SPI. INT1 is configured as active-high push-pull output from the IMU.

## Sensor Configuration

### Output Data Rate

The target sampling rate for gesture recognition is 100 Hz with 10 millisecond period. The LSM6DS3 does not support an exact 100 Hz ODR so the closest standard rate is 104 Hz with 9.615 millisecond period.

Both sensors are synchronized to 104 Hz. The accelerometer is set with lsm6ds3_xl_data_rate_set function passing LSM6DS3_XL_ODR_104Hz. The gyroscope is set with lsm6ds3_gy_data_rate_set function passing LSM6DS3_GY_ODR_104Hz.

We chose 104 Hz because Nyquist theorem states human gestures have frequency content up to approximately 20 Hz requiring greater than 40 Hz sampling. 104 Hz provides margin for high-frequency components like sharp taps and flicks. It is also a standard ODR option on LSM6DS3 with no need for custom dividers.

## Motion Detection Interrupt

### Traditional vs Motion-Triggered Approach

The traditional data-ready interrupt approach which we do NOT use has IMU fire INT at 104 Hz continuously, MCU wakes up 104 times per second, MCU must filter motion from noise in software, and average current is approximately 500 microamps because MCU wake-ups dominate.

The motion-triggered interrupt approach which we DO use has IMU monitor acceleration internally, INT fires only when threshold exceeded at approximately 1 to 10 Hz, MCU stays asleep during idle periods, and average current is approximately 105 microamps for 95 percent reduction.

### Wake-Up Interrupt Configuration

The LSM6DS3 has a built-in wake-up motion detection engine that compares the high-pass filtered accelerometer magnitude against a programmable threshold.

The threshold is 32 LSBs which is approximately 1 meter per second squared or 0.1g. 

Threshold selection rationale is as follows. Less than 16 LSBs is too sensitive and triggers on hand tremor, table vibration, and device pickup. 32 LSBs is optimal and detects deliberate gestures while ignoring ambient noise. Greater than 64 LSBs is too insensitive and misses gentle gestures requiring exaggerated movements.

## Dual-Thread Architecture

The system uses two threads to separate continuous data acquisition from gesture processing.

### Thread 1: High-Priority Sampling Thread

**Purpose:** Continuously read IMU sensor at 104 Hz and write to circular buffer.

**Priority:** HIGH (Zephyr priority 5) to prevent missed samples.

**Operation:**
- Read sensor data: accelerometer and gyroscope for 6 channels total
- Write sensor data to circular buffer at current write index
- Sleep approximately 10 milliseconds to maintain 104 Hz sampling rate

**Buffer:** 300 samples times 6 channels equals always contains last approximately 2.88 seconds of data.

### Thread 2: Gesture Detection Thread

**Purpose:** Wait for motion interrupt, then run inference on buffered data.

**Priority:** NORMAL (Zephyr priority 10) which is lower than sampling to avoid data loss.

**Operation:**
- Wait for motion interrupt using semaphore blocking call
- Delay 480 milliseconds for new data to be written to circular buffer after motion is detected
- Extract data from buffer and run inference
- Perform action on connected device (i.e mobile/laptop) via BLE based on the detected gesture
- Cooldown delay 500 milliseconds to prevent duplicate detections

### Circular Buffer Operation

**Buffer structure:** 300-sample ring buffer continuously overwritten by sampling thread.

Circular Buffer (300 samples, ~2.88 seconds at 104 Hz)
┌────────────────────────────────────────────────────────────────┐
│  [280] [281] [282] ... [299] [0] [1] [2] ... [150] ... [279]   │
│   old   old   old       old   ▲oldest      newest►     old     │
│                              write_idx                         │
└────────────────────────────────────────────────────────────────┘
▲                                                    ▲
└─────── Wraps around ──────────────────────────────┘

**Motion interrupt fires at time T:**

Timeline:
T-2880ms              T-480ms    T=0          T+480ms       T+980ms
|                     |         |              |             |
└─────────────────────┴─────────┴──────────────┴─────────────┘
Buffer contains history    INT1         Gesture        Done
fires        completes

**Buffer state when interrupt fires at T equals 0:**

Circular Buffer at T=0:
┌────────────────────────────────────────────────────────────────┐
│                  [PRE-JOLT DATA] ← write_idx                   │
│  T-2880ms ──────────► T-480ms ──────────► T=0                  │
│   oldest              anticipatory          trigger point      │
└────────────────────────────────────────────────────────────────┘

**Buffer state after 480 millisecond delay at T plus 480 milliseconds:**Circular Buffer at T+480ms:
┌────────────────────────────────────────────────────────────────┐
│  [PRE-JOLT DATA]       [POST-JOLT DATA] ← write_idx           │
│  T-2400ms ──► T=0 ──────────────────────► T+480ms             │
│   anticipatory   trigger   primary motion   follow-through      │
└────────────────────────────────────────────────────────────────┘
|<─────── Gesture Window ───────>|
(extracted for inference)

**Gesture extraction for inference:**

The inference function reads backward from current write index to extract the gesture window:

Extract 100 samples (960ms) centered around trigger:
┌──────────────────────────────────────────────────────────┐
│        PRE-JOLT          │         POST-JOLT             │
│     (50 samples)         │      (50 samples)             │
│     T-480ms to T=0       │      T=0 to T+480ms           │
│    anticipatory motion   │   primary motion + follow-up  │
└──────────────────────────────────────────────────────────┘
▲                            ▲
Hand preparation            Main gesture movement

## System Flow

**Step 1: Continuous sampling**
- Sampling thread runs continuously at 104 Hz filling circular buffer
- Buffer always contains most recent 2.88 seconds of sensor data

**Step 2: Motion detected**
- IMU hardware detects acceleration exceeds threshold of 32 LSBs
- INT1 pin goes high triggering GPIO interrupt

**Step 3: Interrupt handler**
- Posts semaphore taking less than 10 microseconds
- Does not process data in interrupt context for fast response

**Step 4: Gesture thread wakes**
- Semaphore unblocks gesture detection thread
- Immediately starts 480 millisecond delay

**Step 5: During delay**
- Sampling thread continues filling buffer with post-jolt data
- Buffer now contains both pre-jolt and post-jolt portions

**Step 6: Inference**
- Extracts 100 samples from buffer spanning signals pre-jolt and post-jolt
- Processes data through machine learning model
- Returns gesture classification index

**Step 7: Output**
- If valid gesture detected not unknown then process result
- Send to appropriate BLE handler for performing action on connected device

**Step 8: Cooldown**
- Delay 500 milliseconds prevents re-triggering on same gesture
- Ensures each detection corresponds to distinct user intention

**Step 9: Flush**
- Clear any interrupts that fired during 980 millisecond processing time
- Prevents accumulated triggers from immediate re-entry
- Drains semaphore queue back to zero

**Step 10: Repeat**
- Return to waiting for next motion interrupt
- Cycle repeats for continuous gesture detection
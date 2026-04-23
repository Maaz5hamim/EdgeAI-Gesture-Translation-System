# EdgeAI-Gesture-Translation-System
**An end-to-end Edge AI gesture recognition system built on the Nordic nRF54L15 SoC.**  
This project classifies finger-based gestures using a 6-axis IMU and translates them into real-time control commands for mobile devices over Bluetooth Low Energy (BLE).

---

## Overview

The **Gesture Ring** is a low-latency, on-device machine learning system that enables intuitive finger-motion control.  
Using a lightweight TinyML model running entirely on the nRF54L15, the system converts IMU-based motion signatures into actionable mobile commands (e.g., media control, UI navigation).

---

## 1. System Architecture

The system consists of **three fully integrated pipelines**, optimized for real-time inference on a resource-constrained device.

### I. Data Acquisition (IMU → nRF54L15)

- 6-axis IMU: **LSM6DS3 breakout module**
- Data: accelerometer + gyroscope
- Sampling rate: **104 Hz** (closest standard ODR to 100 Hz target)
- Interface: **I2C, 400 kHz fast mode**
- Raw IMU streams are fed directly to the preprocessing/inference engine on the SoC

---

### II. Edge Inference (TinyML Classification)

The nRF54L15's **Arm Cortex-M33** runs a quantized TinyML model (CNN/GRU).

#### Sliding Window Mechanism

To model temporal motion patterns:

```
W_i = { x_t | t ∈ [i·s, i·s + L] }
```

- **L** — Window length (50 samples)
- **s** — Stride

Each window: 50 samples × 6 channels × 2 bytes = **600 bytes** (fits in 256 KB RAM).

Inference is executed fully on-device with INT8 operations to achieve sub-millisecond latency.

---

### III. Translation & Communication (Mobile Bridge)

After classification:

- Gestures → **HID events** or custom **GATT characteristics**
- Communication: **BLE 6.0**
- Mobile device (iOS/Android) receives updates via BLE notifications

Example mapping:  
`Left Flick → Previous Song`

---

## 2. Development Stages

### Stage 1: Sensor Bring-Up (current)

- Bring up LSM6DS3 over I2C on the nRF54L15 DK using the Zephyr `lsm6dsl` driver
- Validate 104 Hz accelerometer + gyroscope readings over serial console
- Interrupt-driven sampling via INT1 data-ready trigger

### Stage 2: Sampling Pipeline

- 100 Hz sampling loop using `k_timer` → ring buffer (`k_msgq`)
- Sliding window extraction (50-sample, 6-channel)
- Zero-mean normalization and unit-variance scaling

### Stage 3: Model Training & Deployment

- **Hybrid dataset**: public IMU datasets + custom finger-gesture recordings
- **Model architecture**: compact CNN/GRU (optimized for 256 KB RAM)
- **Quantization**: INT8 using TFLite Micro or Edge Impulse
- Export model to C++ inference library and flash via nRF Connect SDK

### Stage 4: Mobile Translation Layer

- Mapping engine converts inference outputs → BLE commands
- BLE GATT service with configurable characteristics for gesture streaming
- Low-latency notifications to iOS/Android

---

## 3. Hardware

| Component | Details |
|-----------|---------|
| **SoC** | Nordic nRF54L15 Dev Kit |
| **Sensor** | LSM6DS3 breakout module (6-axis IMU) |
| **Power** | USB (dev) / Li-Po (ring form factor) |
| **Mobile** | BLE-capable iOS or Android |
| **Dev Tools** | macOS Apple Silicon M4, VS Code, nRF Connect extension |

### Wiring (nRF54L15 DK PORT 1 header)

| Breakout Pin | DK Pin | Notes |
|---|---|---|
| VIN | VDD.IO | 3.3V power |
| GND | GND | Ground |
| SDA | P1.02 | I2C data |
| SCL | P1.03 | I2C clock |
| CS | 3V3 (tie high) | Selects I2C mode over SPI |
| SAO | GND (tie low) | Sets I2C address to 0x6A |
| INT1 | P1.00 | Data-ready interrupt (trigger mode) |

---

## 4. Design Decisions

**LSM6DS3 breakout module (not bare chip)**  
The LSM6DS3TR-C is chip-only and requires PCB-level soldering. A breakout module is used for prototyping. The Zephyr `lsm6dsl` driver is register-compatible with the LSM6DS3 — no driver changes needed.

**I2C over SPI**  
I2C requires only 2 signal wires. At 400 kHz with 6 channels × 2 bytes × 104 Hz, bus utilization is under 1% — SPI's higher bandwidth is unnecessary for this data rate.

**P1.02 / P1.03 for SDA/SCL**  
P2 is occupied by onboard SPI flash. P0/P1 pins 4–14 are used by UART, buttons, and LEDs. P1.02 and P1.03 are the first free pins on PORT 1, routed to `i2c21`.

**I2C address 0x6A (SAO tied low)**  
The SAO pin selects between 0x6A (low) and 0x6B (high). Tying low gives the default address and requires no pull-up on SAO.

**ODR 104 Hz**  
The LSM6DS3 does not have an exact 100 Hz output data rate. 104 Hz is the closest standard rate the chip supports.

**Interrupt-driven trigger mode**  
INT1 pulses when a new sample is ready (~104 Hz), waking the MCU via GPIO interrupt rather than polling a timer. More precise sample timing, lower CPU overhead. Controlled by `CONFIG_LSM6DSL_TRIGGER_GLOBAL_THREAD=y`.

**50-sample window**  
50 samples × 6 channels × 2 bytes = 600 bytes per window — well within the nRF54L15's 256 KB RAM.

---

## 5. Build & Flash

Open the `lsm6dsl/` folder in VS Code with the nRF Connect extension. Add a build configuration with board target:

```
nrf54l15dk/nrf54l15/cpuapp
```

The device tree overlay in `boards/nrf54l15dk_nrf54l15_cpuapp.overlay` is picked up automatically. Flash using the **Flash** button in the nRF Connect panel. Console output appears on the USB serial port at 115200 baud.

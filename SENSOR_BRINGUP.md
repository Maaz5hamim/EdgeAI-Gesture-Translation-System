# EdgeAI Gesture Translation System — Sensor Bring-Up

## Overview

This is Stage 1 of the EdgeAI Gesture Translation System: bringing up the LSM6DS3
6-axis IMU over I2C on the Nordic nRF54L15 DK. The firmware reads accelerometer and
gyroscope data at 104 Hz using the Zephyr `lsm6dsl` driver (register-compatible with
the LSM6DS3) and prints samples to the console via interrupt-driven trigger mode.

This stage validates the hardware connection before proceeding to the 100 Hz sampling
loop, sliding window extraction, TFLite Micro inference, and BLE gesture streaming.

## Hardware

| Component | Details |
|-----------|---------|
| SoC | Nordic nRF54L15 (on nRF54L15 DK) |
| IMU | LSM6DS3 breakout module (6-axis, I2C) |
| Host | macOS Apple Silicon M4 |
| IDE | VS Code + nRF Connect extension |

## Wiring (nRF54L15 DK PORT 1 header)

| Breakout Pin | DK Pin | Notes |
|-------------|--------|-------|
| VIN | VDD.IO | 3.3V power |
| GND | GND | Ground |
| SDA | P1.11 | I2C data |
| SCL | P1.12 | I2C clock |
| CS | VDD.IO (tie high) | Selects I2C mode over SPI |
| SAO | GND (tie low) | Sets I2C address to 0x6A |
| INT1 | P1.13 | Data-ready interrupt (trigger) |

> **Note:** P1.02 and P1.03 are NFC pins on the nRF54L15 DK and are not routed
> to GPIO by default. P1.11/P1.12/P1.13 are free GPIO pins confirmed working.

## Design Decisions

**IMU: LSM6DS3 breakout module**
The LSM6DS3TR-C is available as a bare chip only, which requires PCB-level
soldering. A breakout module is used instead for prototyping. Zephyr has no
upstream LSM6DS3 driver; an out-of-tree driver is included in `drivers/lsm6ds3/`,
patched from the `lsm6dsl` driver with WHO_AM_I changed from 0x6A to 0x69.

**Interface: I2C (not SPI)**
I2C requires only 2 signal wires (SDA + SCL) vs 4 for SPI. At 400 kHz fast
mode with 6 channels × 2 bytes × 104 Hz, bus utilization is well under 1%,
so SPI's higher bandwidth is unnecessary.

**I2C controller: i2c21 on P1.11 / P1.12**
The nRF54L15 DK exposes three ports (P0, P1, P2). P2 is occupied by the
onboard SPI flash. P1.02 and P1.03 are NFC pins not routed to GPIO by default.
P1.11 and P1.12 are free GPIO pins routed to `i2c21`.

**I2C address: 0x6A (SAO tied low)**
The SAO pin selects between 0x6A (low) and 0x6B (high). Tying low gives the
default address and avoids the need for an explicit pull-up resistor on SAO.

**ODR: 104 Hz**
The target sampling rate is 100 Hz. The LSM6DS3 does not have an exact 100 Hz
output data rate; 104 Hz is the closest standard rate supported by the chip.

**Trigger mode (interrupt-driven)**
The INT1 pin pulses when a new sample is ready (~104 Hz). This wakes the MCU
via GPIO interrupt rather than polling on a timer, giving more precise sample
timing and lower CPU overhead. Controlled by
`CONFIG_LSM6DS3_TRIGGER_GLOBAL_THREAD=y` in `prj.conf`.

**Window size: 50 samples**
Each inference window is 50 samples × 6 channels × 2 bytes = 600 bytes.
This fits comfortably in the nRF54L15's 256 KB RAM.

## Building and Running

Open this project in VS Code with the nRF Connect extension. Add a build
configuration with board target `nrf54l15dk/nrf54l15/cpuapp`. The device tree
overlay in `boards/nrf54l15dk_nrf54l15_cpuapp.overlay` is picked up automatically.

Flash using the **Flash** button in the nRF Connect panel. Console output appears
on the USB serial port at 115200 baud.

## Sample Output

```console
*** Booting nRF Connect SDK v3.2.1 ***
[00:00:00.040] <inf> imu: IMU started at 104 Hz
[00:00:01.002] <inf> imu: sample rate: 103 Hz
[00:00:01.052] <inf> main: accel x:-22 mg y:-593 mg z:816 mg | gyro x:2559 mdps y:-5731 mdps z:-1364 mdps
```

Gyro values at rest reflect the LSM6DS3's zero-rate offset (up to ±10 dps
per datasheet). This is expected and corrected during model training normalization.

## Status

- **Stage 1 ✓** — LSM6DS3 detected on I2C, accel/gyro confirmed
- **Stage 2 ✓** — 104 Hz interrupt-driven sampling, k_msgq ring buffer, ~103 Hz confirmed
- **Stage 3** — Sliding window extraction (next)
- **Stage 4** — TFLite Micro / Edge Impulse inference
- **Stage 5** — BLE GATT gesture streaming

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
| SDA | P1.02 | I2C data |
| SCL | P1.03 | I2C clock |
| CS | 3V3 (tie high) | Selects I2C mode over SPI |
| SAO | GND (tie low) | Sets I2C address to 0x6A |
| INT1 | P1.00 | Data-ready interrupt (trigger) |

## Design Decisions

**IMU: LSM6DS3 breakout module**
The LSM6DS3TR-C is available as a bare chip only, which requires PCB-level
soldering. A breakout module is used instead for prototyping. The Zephyr
`lsm6dsl` driver is register-compatible with the LSM6DS3, so no driver
changes are needed.

**Interface: I2C (not SPI)**
I2C requires only 2 signal wires (SDA + SCL) vs 4 for SPI. At 400 kHz fast
mode with 6 channels × 2 bytes × 104 Hz, bus utilization is well under 1%,
so SPI's higher bandwidth is unnecessary.

**I2C controller: i2c21 on P1.02 / P1.03**
The nRF54L15 DK exposes three ports (P0, P1, P2). P2 is occupied by the
onboard SPI flash. P0 and P1 pins 4–14 are used by UART, buttons, and LEDs.
P1.02 and P1.03 are the first free pins on PORT 1 and are routed to `i2c21`.

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
`CONFIG_LSM6DSL_TRIGGER_GLOBAL_THREAD=y` in `prj.conf`.

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
LSM6DSL sensor samples:

accel x:-3.184000 ms/2 y:-0.697000 ms/2 z:9.207000 ms/2
gyro x:0.065000 dps y:-0.029000 dps z:0.002000 dps
loop:1 trig_cnt:1

<repeats every 2 seconds>
```

## Next Steps

1. Confirm sensor readings over serial console
2. Replace 2-second print loop with 100 Hz ring buffer (`k_timer` + `k_msgq`)
3. Implement sliding window extraction (50-sample, 6-channel)
4. Integrate TFLite Micro or Edge Impulse inference (INT8, CNN/GRU)
5. Add BLE GATT notifications for classified gestures

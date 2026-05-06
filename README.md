# LSM6DS3 Gesture Recognition System with Nordic nRF54L15-DK

## Table of Contents
- [Introduction](#introduction)
- [Hardware Details](#hardware-details)
- [Physical Assembly](#physical-assembly)
- [Software Environment](#software-environment)
- [Reproducibility Guide](#reproducibility-guide)
- [Troubleshooting](#troubleshooting)

---

## Introduction

### Problem Statement
Traditional human-computer interaction relies heavily on physical input devices (keyboards, mice, touchscreens). This project addresses the need for intuitive, contactless gesture-based control systems suitable for applications in:
- VR/AR environments
- Accessibility tools for users with limited mobility
- Industrial/medical settings requiring hands-free operation
- Smart home/IoT device control

### Target Application
A wearable gesture recognition glove that translates hand movements into wireless commands for mobile devices, laptops, and IoT systems via Bluetooth Low Energy (BLE).

### High-Level Architecture
```
┌─────────────────────────────────────────────────┐
│  LSM6DS3 IMU Sensor (Finger-mounted)            │
│  ├─ Accelerometer (±2g to ±16g)                 │
│  └─ Gyroscope (±125 to ±2000 dps)               │
└────────────────┬────────────────────────────────┘
                 │ I2C/SPI
                 ▼
┌─────────────────────────────────────────────────┐
│  Nordic nRF54L15-DK (Processing Unit)           │
│  ├─ Background Thread: Circular Buffer (100)    │
│  ├─ IMU Interrupt: Jolt Detection               │
│  ├─ ML Inference Engine                         │
│  │  ├─ Random Forest (gesture_app_rf)           │
│  │  └─ CNN TFLite (gesture_app_cnn)             │
│  └─ BLE Stack (Bluetooth 5.4)                   │
└────────────────┬─────────────────────────────── ┘
                 │ BLE GATT
                 ▼
┌─────────────────────────────────────────────────┐
│  Client Device (Mobile/Laptop)                  │
│  └─ Gesture Command Interpreter                 │
└─────────────────────────────────────────────────┘
```

### Key Features
- **8 Gesture Classes**: Slide Up, Slide Down, Slide Right, Slide Left, Tap, Double Tap, Static, None
- **Dual ML Models**: 
  - Random Forest (currently superior performance)
  - CNN (TensorFlow Lite optimized)
- **Interrupt-Driven Inference**: IMU hardware interrupt triggers on significant motion jolt
- **Smart Windowing**: 100-sample window (50 pre-jolt, 50 post-jolt) captures complete gesture signature
- **Low Latency**: <50ms inference time (Random Forest)
- **Wireless Range**: 10-15m typical BLE range
- **Energy Efficient**: Interrupt-driven architecture minimizes active processing time

### Performance Summary
| Metric | Value |
|--------|-------|
| **Inference Latency** | 30-50ms (RF), 60-80ms (CNN) |
| **Gesture Accuracy** | 91-94% (RF), 80-83% (CNN) |
| **Sampling Rate** | 100Hz (IMU) |

---

## Hardware Details

### i. Board and MCU
*   **Core**: Nordic Semiconductor **nRF54L15** (ARM Cortex-M33).
*   **Development Kit**: nRF54L15DK.

### ii. Additional Peripherals
*   **IMU**: STMicroelectronics **LSM6DS3** (6-axis Accelerometer and Gyroscope) — [Purchase](https://www.amazon.com/LSM6DS3-Accelerometer-Gyroscope-Temperature-Interface/dp/B0FKT9ZR2X/) | [Datasheet](https://www.st.com/resource/en/datasheet/lsm6ds3.pdf).
*   **Interface**: I2C protocol for sensor data acquisition.

### iii. Power Subsystem
*   **Power Source**: CR2032 coin cell (3V, 225mAh) or USB via nRF54L15DK.
*   **Average Current Draw**: ~360µA (interrupt-driven idle + periodic BLE advertising).
*   **Estimated Runtime**: ~600 hours (~25 days) on a CR2032 at 360µA average.
*   **Active Inference Current**: ~5-8mA during gesture inference window (~50ms burst).
*   **Charging**: USB-powered when connected to DK; no charging circuit for coin cell configuration.

### iv. RF Specifications
*   **Band**: 2.4 GHz ISM.
*   **Protocol**: Bluetooth Low Energy 5.4.
*   **PHY**: 1M PHY (default); 2M PHY supported by nRF54L15.
*   **Output Power**: 0 dBm (default nRF54L15 TX power).
*   **Expected Range**: 10–15m line-of-sight; 5–8m through walls.
*   **Advertising Interval**: 100ms during pairing; connection interval ~20ms during active use.
*   **Compliance**: nRF54L15 is FCC/CE/IC certified by Nordic Semiconductor.

---

## Physical Assembly

### i. Glove Integration:

![Glove Assembly - Front View](images/Mounting_Setup.jpeg)
*Figure 1: LSM6DS3 mounted on index finger and connected to nrf54l15dk attached to a glove*

![Glove Assembly - Side View](images/IMU_Orientation.jpeg)
*Figure 2: Side view showing sensor orientation*

### ii. IMU Orientation:
```
Glove Coordinate System (when worn on right hand, palm down):

┌─────────────────────────────────────┐
│                                     │
│         -Z (Toward Finger Tip)      │
│              ▲                      │
│              │                      │
│              │                      │
│    +Y        │        +X            │
│   (Up)       └────────►             │
│   ⊙          (Toward Middle Finger) │
│                                     │
│   LSM6DS3 Sensor                    │
│  (Top view)                         |
│                                     │
└─────────────────────────────────────┘
```
---

## Software Environment

### i. Firmware
*   **Toolchain**: nRF Connect SDK (NCS) **v3.2.1**.
*   **RTOS**: Zephyr RTOS (bundled with NCS v3.2.1).
*   **Build System**: West / CMake.
*   **Compiler**: arm-zephyr-eabi-gcc 12.2.0 (Zephyr SDK 0.17.0).

### ii. Machine Learning Module
The repository contains two distinct inference approaches for gesture classification:
*   **Random Forest (`gesture_app_rf`)**: The recommended implementation due to superior stability and lower resource overhead on the nRF54.
*   **CNN (`gesture_app_cnn`)**: An alternative deep learning approach for experimental comparison.
*   **Training**: Developed using Python 3.11, Scikit-learn, and NumPy.

### iii. Radio Stack
*   **Protocol**: Bluetooth Low Energy (BLE) 5.4.
*   **Profile**: HID Over GATT (HOGP).
*   **Appearance**: Keyboard (961).
*   **PHY**: 1M PHY default.
*   **Channel**: Auto-managed by BLE stack (channels 0–36, advertising on 37/38/39).
*   **Data Rate**: 1 Mbps (1M PHY).

### iv. OS Compatibility and Drivers
*   **Host OS**: macOS, Windows 10/11, Linux, iOS, Android — any OS with native BLE HID support.
*   **Special Drivers**: None required. The device enumerates as a standard Bluetooth keyboard; no custom drivers needed on the host side.
*   **Programming Tools**: nRF Connect for VS Code (extension pack), `west` CLI (bundled with NCS v3.2.1).

---

## Reproducibility Guide

### i. Prerequisites & Environment Setup
1.  **Clone the Repository**:
    ```bash
    git clone <your-repo-url>
    cd <repo-name>
    
2. **VS Code Extension**: Install the nRF Connect for VS Code Extension Pack.
3. **SDK Version**: Ensure you are using nRF Connect SDK (NCS) v3.2.1.
4. **Toolchain**: Verify that the toolchain is correctly linked within the VS Code extension settings to match the SDK version.

### ii. Hardware Assembly
1. Connect the LSM6DS3 IMU to the nRF54L15DK according to the following pin map:
   
  | Breakout Pin | DK Pin | Notes |
  |-------------|--------|-------|
  | VIN | VDD.IO | 3.3V power |
  | GND | GND | Ground |
  | SDA | P1.11 | I2C data |
  | SCL | P1.12 | I2C clock |
  | CS | VDD.IO (tie high) | Selects I2C mode over SPI |
  | SAO | GND (tie low) | Sets I2C address to 0x6A |
  | INT1 | P1.13 | Data-ready interrupt (trigger) |
  
2. Ensure that the orientation of IMU is same as previously shown

### iii. Build and Flash Instructions

You can build either the Random Forest or the CNN version of the application

#### Option A: Random Forest (gesture_app_rf) - Recommended

This version is more stable and resource-efficient for the nRF54L15.
  ```bash
  cd gesture_app_rf
  rm -rf build/
  west build -b nrf54l15dk/nrf54l15/cpuapp
  west flash
  ```

#### Option B: CNN (gesture_app_cnn)

**Note**: To build the CNN app, the tflite-micro library must be manually added to your Zephyr allowlist.

1. Update your west.yaml file to include tflite-micro to the zephyr allowlist

2. Run the following command to sync the library:
   ```bash
   west update -f always

4. Build and Flash:
    ```bash
    cd gesture_app_cnn
    rm -rf build/
    west build -b nrf54l15dk/nrf54l15/cpuapp
    west flash
    ```

### iv. Running the Demo

* **Pairing**: Once flashed, the device will advertise as "GestureRing".
* **Connection**: Open the Bluetooth settings on your phone or laptop and connect to the device.
* **Gestures**: After connecting, perform gestures to control your device.

**Note**: Gestures are optimized for navigation in Safari and Chrome and may not work on some applications.

**Expected log output** (via `west build` serial monitor or nRF Connect app):
```
*** Booting nRF Connect SDK v3.2.1 ***
[00:00:00.123] BLE HID initialized
[00:00:00.456] IMU initialized at 100Hz
[00:00:00.789] Advertising as "GestureRing"...
[00:00:05.001] BLE connected
[00:00:08.345] Jolt detected — capturing window
[00:00:08.395] Inference result: SLIDE_UP (confidence: 0.94)
[00:00:08.400] BLE HID keycode sent: PAGE_UP
```

### v. Testing and Measurement

**Reproducing accuracy metrics:**
1. Collect test data using `machine_learning/data_collector.py` with the device connected over serial.
2. Run preprocessing: `python machine_learning/preprocess.py`
3. Train and evaluate: `python machine_learning/random_forest/train.py` — prints overall accuracy on the held-out test set.
4. The reported 91–94% RF accuracy is measured on a held-out 20% split of 900 labeled gesture samples (720 train / 180 test).

**Reproducing latency measurements:**
- Inference time is printed to serial on each gesture event (see expected log above).
- Measure end-to-end latency (jolt detection → keycode received on host) using a stopwatch or BLE sniffer.

**Power measurement:**
- Use a Nordic PPK2 (Power Profiler Kit II) connected to the DK's power measurement pins to observe current draw during idle and inference bursts.

### vi. Offline Mode

The system operates fully offline — all inference runs on-device with no cloud dependency. If Bluetooth connectivity to the host is unavailable:
- The device will continue advertising as "GestureRing" and retry connection automatically.
- Inference still runs locally; keycode output is simply not delivered until a host connects.
- No internet connection is required at any point.

## Troubleshooting

**Device Not Visible**: If "GestureRing" does not appear in your Bluetooth list:

* Press the RESET button on the nRF54L15DK.
* Toggle Bluetooth OFF and ON on your laptop or phone to refresh the cache.

**Pairing Fails**:
* Forget the "GestureRing" device phone 
* Erase nrf54l15dk 
* Flash nrf54l15dk

**Gestures No Longer Working**: 
* Forget the "GestureRing" device phone 
* Reset nrf54l15dk 
* Pair to "GestureRing" again

**Missing TFLite Libraries**: If the CNN build fails with missing library errors, double-check that your *west.yaml* was modified correctly and that you ran **west update -f always**.

**I2C Errors**: Ensure the jumpers are securely connected to the correct pins.

---

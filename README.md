# EdgeAI-Gesture-Translation-System
**An end-to-end Edge AI gesture recognition system built on the Nordic nRF54L15 SoC.**  
This project classifies finger-based gestures using a 6-axis IMU and translates them into real-time control commands for mobile devices over Bluetooth Low Energy (BLE).

---

## 🚀 Overview

The **Gesture Ring** is a low-latency, on-device machine learning system that enables intuitive finger-motion control.  
Using a lightweight TinyML model running entirely on the nRF54L15, the system converts IMU-based motion signatures into actionable mobile commands (e.g., media control, UI navigation).

---

## 📐 1. System Architecture

The system consists of **three fully integrated pipelines**, optimized for real-time inference on a resource-constrained device.

### **I. Data Acquisition (IMU → nRF54L15)**

- 6-axis IMU: **LSM6DS3**
- Data: accelerometer + gyroscope  
- Sampling rate: **100 Hz**
- Interface: **I²C bus**
- Raw IMU streams are fed directly to the preprocessing/inference engine on the SoC.

---

### **II. Edge Inference (TinyML Classification)**

The nRF54L15’s **Arm Cortex-M33** runs a quantized TinyML model (CNN/GRU).

#### **Sliding Window Mechanism**
To model temporal motion patterns:

\[
W_i = \{x_t \mid t \in [i \cdot s,\; i \cdot s + L]\}
\]

- **L** — Window length  
- **s** — Stride

Inference is executed fully on-device with INT8 operations to achieve sub-millisecond latency.

---

### **III. Translation & Communication (Mobile Bridge)**

After classification:

- Gestures → **HID events** or custom **GATT characteristics**
- Communication: **BLE 6.0**  
- Mobile Device (iOS/Android) receives updates via BLE notifications

Example mapping:  
`Left Flick → Previous Song`

---

## 🛠️ 2. Development Stages

### **Stage 1: Data Collection & Preparation**

- **Hybrid Dataset Strategy**
  - Public IMU datasets for baseline learning
  - Custom IMU recordings for finger-specific motion signatures  
- **Preprocessing**
  - Zero-mean normalization  
  - Unit-variance scaling  
  - Timestamp alignment + window segmentation

---

### **Stage 2: Model Training & Deployment**

- **Model Architecture**: Compact CNN/GRU (optimized for **256 KB RAM**)
- **Quantization**: INT8 using TFLite Micro or Edge Impulse
- **Deployment**
  - Export model to optimized C++ inference library  
  - Flash firmware via **nRF Connect SDK** (Zephyr)

---

### **Stage 3: Mobile Translation Layer**

- **Firmware**: Zephyr RTOS  
- **Mapping Engine**
  - Converts inference outputs → BLE commands  
- **BLE Communication**
  - Low-latency updates  
  - Configurable services/characteristics for gesture streaming

---

## 🔧 3. Hardware Requirements

| Component | Description |
|----------|-------------|
| **SoC** | Nordic **nRF54L15** Dev Kit |
| **Sensor** | LSM6DS3 (6-axis IMU) |
| **Power** | Portable Li-Po / USB |
| **Mobile** | BLE-capable iOS or Android |
| **Development Tools** | macOS (Apple Silicon M4), VS Code, nRF Connect Toolchain |

---

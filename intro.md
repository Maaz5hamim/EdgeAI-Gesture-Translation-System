# EdgeAI Gesture Translation System
### Hands-Free Control Through Motion: TinyML Gesture Recognition on nRF54L15

---

## Transform Your Hand Movements Into Digital Commands

Imagine controlling your phone, computer, or smart TV with simple hand gestures—no buttons, no touchscreen, just natural motion. The **EdgeAI Gesture Translation System** brings this vision to life using cutting-edge TinyML technology running entirely on a coin-sized Nordic nRF54L15 microcontroller.

This project combines a 6-axis IMU sensor with on-device machine learning to recognize eight gesture classes in real-time, translating them into Bluetooth keyboard commands. The system achieves **93% accuracy** while consuming only **360µA average power**—enabling weeks of battery life on a single CR2032 coin cell.

**What makes this special?**
- **Fully embedded intelligence:** No cloud, no smartphone processing—inference runs directly on the 256KB RAM nRF54L15
- **Motion-triggered efficiency:** Smart interrupt-driven architecture captures gesture signatures spanning both anticipatory and reactive movements
- **Dual ML architectures:** Choose between lightweight Random Forest (50KB) or high-accuracy CNN (36-145KB) depending on your needs
- **Universal compatibility:** Works as a standard Bluetooth keyboard with any device—phones, tablets, computers, smart TVs
- **Complete ML pipeline:** From raw IMU data collection through training to optimized C deployment, all tools included

Whether you're building accessible interfaces for mobility-impaired users, hands-free controls for medical environments, or next-generation gaming controllers, this open-source platform provides the foundation for gesture-based interaction at the extreme edge.

---

## 🎥 See It In Action

<video src="https://youtu.be/0bSiu9pfk04" controls>
  Your browser does not support the video tag.
</video>

![Setup](images/Mounting_Setup.jpeg)

*Real-time gesture recognition in action*

**[📹 Watch Full Video](https://www.youtube.com/watch?v=0bSiu9pfk04)**



## Use Cases
- **Accessibility**: Hands-free control for users with limited mobility
- **Medical environments**: Touchless interface for sterile settings
- **Gaming**: Motion-based controller for VR/AR applications
- **Smart home**: Gesture control for lights, TV, appliances
- **Wearables**: Smartwatch or ring-based input device
- **Automotive**: Driver gesture recognition for infotainment systems

## Future Roadmap
- Add gesture velocity/intensity classification (slow vs fast swipes)
- Implement on-device model fine-tuning based on user corrections
- Expand gesture vocabulary: circles, figure-8, multi-finger gestures
- Add IMU fusion with magnetometer for absolute orientation
- Create gesture macro system for complex command sequences
- Develop smartphone companion app for gesture customization
- Port to other nRF5x and STM32 platforms

## Documentation

- **[System Architecture](docs/architecture.md)** — Sensor configuration, motion detection, dual-thread architecture
- **[BLE Subsystem](docs/bluetooth.md)** — HID keyboard protocol, connection management, tuning parameters
- **[Machine Learning](docs/machine_learning.md)** — Data collection, training, optimization, deployment

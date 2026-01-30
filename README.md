# AfA2026-PhysicalAI — SafeGuard AI  
**Intelligent Fall Detection and Emergency Response System**

**SafeGuard AI** is an edge-based biometric monitoring system built on the Arduino UNO Q. It leverages TinyML using TensorFlow Lite to detect fall events in real time and automatically initiate emergency response actions via the Twilio API. The system incorporates a smart calibration mechanism that adapts sensitivity based on the user’s gait and includes a complete end-to-end model training pipeline.

![Project Banner](assets/SafeGuard-AI-banner.png)

---

## Project Overview

Falls among elderly and high-risk individuals constitute a serious medical emergency where response time is critical. SafeGuard AI addresses this challenge by performing intelligent inference directly on the device, eliminating latency, privacy risks, and cloud dependency.

The Arduino UNO Q processes inertial sensor data locally using a quantized neural network. Upon detecting a fall, the system executes a structured emergency workflow:

1. **Local Alert:** A countdown warning is triggered on the web dashboard.
2. **Automated Voice Call:** If the alert is not cancelled within 10 seconds, an emergency call is placed to predefined contacts using the Twilio API.
3. **Data Logging:** Impact force (G), posture orientation, and skin temperature are recorded for medical analysis.

---

## Hardware Lineup

- **Main Board:** Arduino UNO Q  
- **Sensors:** Modulino Movement (LSM6DSOX accelerometer and gyroscope)  
- **Connectivity:** Wi-Fi (web dashboard and Twilio API integration)  
- **Power Supply:** USB-C or LiPo battery  

---

## Software Architecture

The system is developed using **Arduino App Lab** and takes advantage of the dual-core architecture of the Arduino UNO Q to separate real-time sensing from AI inference and networking tasks.

### 1. Microcontroller Layer (C++)

- **Location:** `SafeGuard-AI/sketch/`  
- **Role:**  
  Acts as the high-speed sensor acquisition layer. It polls the LSM6DSOX accelerometer and gyroscope at 100 Hz and transmits raw 6-axis IMU data along with temperature readings to the Python runtime via RPC (Remote Procedure Call).

### 2. AI Processing Layer (Python)

- **Location:** `SafeGuard-AI/python/`  
- **Role:**  
  - Signal preprocessing (jerk computation, magnitude calculation, sliding window buffering of 200 samples)  
  - TinyML inference using an int8 quantized TensorFlow Lite model  
  - Management of calibration logic and emergency call handling through the Twilio API  

### 3. Model Training Pipeline (Python)

- **Location:** `SafeGuard-AI/tinyml/`  
- **Role:**  
  Contains scripts for feature extraction, model training, and deployment-ready conversion.
  - `feature_extract.py`: Converts raw CSV sensor logs into engineered features (jerk, mean, standard deviation).
  - `train.py`: Trains the TensorFlow model and converts it into an int8 quantized TensorFlow Lite model.

### 4. Web Dashboard (HTML/CSS/JavaScript)

- **Location:** `SafeGuard-AI/assets/`  
- **Role:**  
  Provides a real-time medical dashboard displaying live sensor streams, fall probability, alert status, and system health.

---

## AI Model and Calibration Strategy

SafeGuard AI uses a custom TensorFlow Lite model trained on fall detection datasets and optimized for edge inference.

- **Input Features:**  
  - 6-axis IMU data (accelerometer and gyroscope)  
  - Derived features such as jerk and acceleration magnitude  

- **Model Type:** Quantized int8 TensorFlow Lite neural network  
- **Inference Objective:** Binary classification of fall versus non-fall motion patterns  

### Smart Calibration Mode

The system includes an adaptive calibration phase during which it learns the user’s movement characteristics over a 15-second interval:

- **Sedentary Profile:**  
  - Lower detection threshold (approximately 0.45)  
  - Optimized for frail or low-mobility users  

- **Active Profile:**  
  - Higher detection threshold (approximately 0.85)  
  - Reduces false positives during vigorous activities  

---

## How to Run

1. **Hardware Setup:**  
   Connect the Modulino Movement sensor to the Arduino UNO Q using the Qwiic/I2C interface.

2. **Software Setup:**  
   Open the `SafeGuard-AI` directory in **Arduino App Lab**.

3. **Twilio Configuration:**  
   - Open `SafeGuard-AI/python/main.py`.  
   - Insert your `TWILIO_SID`, `TWILIO_TOKEN`, and verified phone numbers.

4. **Execution:**  
   Click the **Run** button in Arduino App Lab to start the system.

---

## Repository Structure

```text
├── SafeGuard-AI/
│   ├── app.yaml              # Arduino App Lab configuration
│   ├── python/               # Inference engine
│   │   ├── main.py
│   │   ├── fall_model_int8.tflite
│   │   └── requirements.txt
│   ├── tinyml/               # Model training pipeline
│   │   ├── feature_extract.py
│   │   └── train.py
│   ├── sketch/               # Firmware
│   │   ├── sketch.ino
│   │   └── sketch.yaml
│   ├── assets/               # Web dashboard
│   └── docs_assets/          # Documentation images
├── LICENSE.txt               # Mozilla Public License 2.0
└── README.md                 # Project documentation

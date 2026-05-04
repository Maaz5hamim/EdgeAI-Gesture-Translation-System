import serial
import numpy as np
import joblib
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constant import GESTURE_MAP


MODEL_PATH = 'gesture_random_forest.joblib'

# 1. Load your trained Random Forest model
try:
    clf = joblib.load(MODEL_PATH)
    print("Model loaded successfully.")
except FileNotFoundError:
    print("Error: 'gesture_random_forest.joblib' not found. Please train and save the model first.")
    exit()

# 2. Configure Serial
SERIAL_PORT = '/dev/cu.usbmodem0010577695733' 
BAUD_RATE = 115200
WINDOW_SIZE = 100

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

print(f"Listening on {SERIAL_PORT}...")

try:
    while True:
        # Read a line and ignore decoding errors
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        # Check for the start of a gesture capture
        if line == "START_WINDOW":
            window_data = []
            
            # Capture exactly 100 IMU samples
            while len(window_data) < WINDOW_SIZE:
                data_line = ser.readline().decode('utf-8').strip()
                
                # Exit loop if we hit the end marker prematurely
                if data_line == "END_WINDOW": 
                    break
                
                try:
                    # Parse ax, ay, az, gx, gy, gz
                    values = [float(x) for x in data_line.split(',')]
                    if len(values) == 6:
                        window_data.append(values)
                except ValueError:
                    continue
            
            # 3. Run Inference once the window is complete
            if len(window_data) == WINDOW_SIZE:
                # Convert to numpy array (100, 6)
                imu_array = np.array(window_data, dtype=np.float32)
                
                # Flatten for Random Forest: (100, 6) -> (1, 600)
                input_tensor = imu_array.reshape(1, -1)
                
                # Predict
                prediction = clf.predict(input_tensor)[0]
                probabilities = clf.predict_proba(input_tensor)
                confidence = np.max(probabilities)
                
                print(f"Predicted Gesture ID: {GESTURE_MAP.get(prediction)} | Confidence: {confidence:.2%}")
            else:
                print(f"Incomplete window received ({len(window_data)} samples). Skipping...")

except KeyboardInterrupt:
    print("\nInference stopped by user.")
finally:
    ser.close()
    print("Serial port closed.")
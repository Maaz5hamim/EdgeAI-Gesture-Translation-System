import serial
import numpy as np
import tensorflow as tf # Changed from joblib
import sys
import os

# Ensure project paths are visible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constant import GESTURE_MAP

# 1. Load your TensorFlow/Keras model
MODEL_PATH = 'best_model.h5' # or 'gesture_model.keras'
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print("TensorFlow model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    exit()

# 2. Configure Serial
SERIAL_PORT = '/dev/cu.usbmodem0010577695733' 
BAUD_RATE = 115200
WINDOW_SIZE = 100

ser = serial.serial_for_url(SERIAL_PORT, baudrate=BAUD_RATE, timeout=1)
print(f"Listening for Ring Gestures on {SERIAL_PORT}...")

try:
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        if line == "START_WINDOW":
            window_data = []
            
            while len(window_data) < WINDOW_SIZE:
                data_line = ser.readline().decode('utf-8').strip()
                if data_line == "END_WINDOW": 
                    break
                
                try:
                    values = [float(x) for x in data_line.split(',')]
                    if len(values) == 6:
                        window_data.append(values)
                except ValueError:
                    continue
            
            # 3. Run TensorFlow Inference
            if len(window_data) == WINDOW_SIZE:
                # Convert to numpy array (100, 6)
                imu_array = np.array(window_data, dtype=np.float32)
                
                # IMPORTANT: TensorFlow expects (Batch, TimeSteps, Features)
                # Shape: (1, 100, 6)
                input_tensor = np.expand_dims(imu_array, axis=0)
                
                # Predict
                predictions = model.predict(input_tensor, verbose=0)
                predicted_id = np.argmax(predictions[0])
                confidence = np.max(predictions[0])
                
                gesture_name = GESTURE_MAP.get(predicted_id, "Unknown")
                print(f"Gesture: {gesture_name:10} | Confidence: {confidence:.2%}")
            else:
                print(f"Incomplete window: {len(window_data)} samples.")

except KeyboardInterrupt:
    print("\nInference stopped.")
finally:
    ser.close()
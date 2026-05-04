import numpy as np
import serial
import os
import csv
from datetime import datetime
from constant import GESTURE_NAMES, FEATURE_COLS

SERIAL_PORT = '/dev/cu.usbmodem0010577695733' 
WINDOW_SIZE = 100
FEATURE_COUNT = 6
DATA_FOLDER = "dataset/data"
LABEL_FOLDER = "dataset/label"

# Ensure directories exist
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)

print(f"--- Data Collection Ready ---")
print(f"Available Gestures: {GESTURE_NAMES}")
print("Waiting for 'START_WINDOW' from nRF54L15...")

try:
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        if line == "START_WINDOW":
            window_data = []
            print("\nCapturing gesture window...", end="", flush=True)
            
            while len(window_data) < WINDOW_SIZE:
                data_line = ser.readline().decode('utf-8', errors='ignore').strip()
                if data_line == "END_WINDOW": 
                    break
                try:
                    # Parse ax, ay, az, gx, gy, gz
                    values = [float(x) for x in data_line.split(',')]
                    if len(values) == FEATURE_COUNT:
                        window_data.append(values)
                except ValueError: 
                    continue
            
            if len(window_data) == WINDOW_SIZE:
                print(" Done.")
                
                # Manual Labeling
                for i, name in enumerate(GESTURE_NAMES):
                    print(f"{i}: {name}", end="  ")
                
                feedback = input("\nAssign Label [0-7] or 's' to skip: ").strip().lower()
                
                if feedback.isdigit() and int(feedback) < len(GESTURE_NAMES):
                    target_label = int(feedback)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    
                    # 1. Save raw data file
                    filename = f"gesture_{timestamp}_data.csv"
                    filepath = os.path.join(DATA_FOLDER, filename)
                    with open(filepath, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(FEATURE_COLS)
                        writer.writerows(window_data)
                    
                    filename = f"gesture_{timestamp}_label.csv"
                    filepath =  os.path.join(LABEL_FOLDER, filename)
                    with open(filepath, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["label"])
                        writer.writerow([target_label])
                    
                    print(f"✓ Saved {filename} as '{GESTURE_NAMES[target_label]}'")
                else:
                    print("× Window discarded.")
            else:
                print(f"× Error: Captured only {len(window_data)} samples.")

except KeyboardInterrupt:
    print("\nStopping data collection...")
    ser.close()
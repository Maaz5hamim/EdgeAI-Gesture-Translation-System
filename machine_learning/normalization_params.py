"""
extract_normalization_params.py
Extract normalization parameters for embedded deployment
"""

import numpy as np
from preprocess import Preprocess

# Load your training data
data = np.load('data/imu_gesture_data.npz', allow_pickle=True)

train_features = data['features']
train_labels = data['labels']

# Fit preprocessor
preprocessor = Preprocess(target_length=128, normalize=True, augment=False)
preprocessor.fit(train_features)

# Get normalization parameters
mean = preprocessor.scaler.mean_
std = preprocessor.scaler.scale_

print("=" * 70)
print("NORMALIZATION PARAMETERS FOR EMBEDDED SYSTEM")
print("=" * 70)
print("\nCopy these values to your C/C++ code:\n")

feature_names = ['ACCEL_X', 'ACCEL_Y', 'ACCEL_Z', 'GYRO_X', 'GYRO_Y', 'GYRO_Z']

print("// Mean values")
for i, name in enumerate(feature_names):
    print(f"#define {name}_MEAN {mean[i]:.6f}f")

print("\n// Standard deviation values")
for i, name in enumerate(feature_names):
    print(f"#define {name}_STD {std[i]:.6f}f")

print("\n" + "=" * 70)

# Save to file
np.savez('normalization_params.npz', mean=mean, std=std)
print("\n✓ Saved to normalization_params.npz")
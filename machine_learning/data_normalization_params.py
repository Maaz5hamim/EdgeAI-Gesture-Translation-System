import numpy as np
from preprocess import Preprocess
from constant import FEATURE_COLS

DATA_DIR = 'dataset/gesture_data_consolidated.npz'
OUTPUT_DIR = 'dataset/normalization_params.npz'

# Load your training data
data = np.load(DATA_DIR, allow_pickle=True)

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


print("// Mean values")
for i, name in enumerate(FEATURE_COLS):
    print(f"#define {name}_MEAN {mean[i]:.6f}f")

print("\n// Standard deviation values")
for i, name in enumerate(FEATURE_COLS):
    print(f"#define {name}_STD {std[i]:.6f}f")

print("\n" + "=" * 70)

# Save to file
np.savez(OUTPUT_DIR, mean=mean, std=std)
print(f"\n✓ Saved to {OUTPUT_DIR}")
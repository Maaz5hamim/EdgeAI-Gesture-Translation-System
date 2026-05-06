import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import sys
import os

DATA_DIR = '../dataset/gesture_data_consolidated.npz'
OUTPUT_DIR = 'gesture_random_forest.joblib'

# Load your existing data
data = np.load(DATA_DIR, allow_pickle=True)
X = data['features'] # Shape (900, 100, 6)
y = data['labels']   # Shape (900,)

# Flatten the windows: (900, 100, 6) -> (900, 600)
X_flattened = X.reshape(X.shape[0], -1)

# Split and Train
X_train, X_test, y_train, y_test = train_test_split(X_flattened, y, test_size=0.2)
clf = RandomForestClassifier(
    n_estimators=35,  
    max_depth=10,       
    min_samples_leaf=5,   
    random_state=42
)

clf.fit(X_train, y_train)

print(f"Random Forest Accuracy: {clf.score(X_test, y_test):.2%}")
joblib.dump(clf, OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}")
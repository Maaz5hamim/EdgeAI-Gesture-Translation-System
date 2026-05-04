import m2cgen as m2c
import joblib
import os

MODEL_PATH = 'gesture_random_forest.joblib'
OUTPUT_PATH = "gesture_model.h"

# 1. Load your trained Random Forest model
clf = joblib.load(MODEL_PATH)

# 2. Transpile the model to C code
code = m2c.export_to_c(clf)

# 3. Save the header file

with open(OUTPUT_PATH, "w") as f:
    f.write(code)

# 4. Calculate size metrics
code_size_bytes = os.path.getsize(OUTPUT_PATH)
code_size_kb = code_size_bytes / 1024

# Complexity metrics from the classifier
n_trees = len(clf.estimators_)
max_depth = clf.max_depth if clf.max_depth else "Unlimited"
total_nodes = sum(tree.tree_.node_count for tree in clf.estimators_)

print("--- nRF54 Deployment Metrics ---")
print(f"Generated Header: {OUTPUT_PATH}")
print(f"Estimated Flash Impact: ~{code_size_kb:.2f} KB")
print(f"Number of Trees: {n_trees}")
print(f"Max Depth: {max_depth}")
print(f"Total Decision Nodes: {total_nodes}")

if code_size_kb > 256:
    print("\nWARNING: Model size is large. Consider reducing n_estimators or max_depth.")
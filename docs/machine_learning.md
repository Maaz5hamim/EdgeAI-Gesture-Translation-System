# EdgeAI Gesture Translation System — Machine Learning Subsystem

## Overview

The Machine Learning subsystem handles the complete pipeline from data collection through model training to on-device deployment. It supports two model architectures: Random Forest for lightweight statistical classification and Convolutional Neural Network (CNN) for deep learning-based pattern recognition. The subsystem provides tools for data collection, visualization, training, optimization, and real-time validation.

## Table of Contents
- [Data Collection](#data-collection)
- [Data Consolidation and Visualization](#data-consolidation-and-visualization)
- [Random Forest Workflow](#random-forest-workflow)
- [CNN Workflow](#cnn-workflow)
- [Model Comparison](#model-comparison)

## Data Collection

### Preparing Firmware for Data Collection

Navigate to the appropriate application directory:
- For Random Forest: `gesture_app_rf/`
- For CNN: `gesture_app_cnn/`

**Modify main_functions.cpp:**

Comment out inference code and enable streaming:

```cpp
void loop(void)
{
    // Wait for motion interrupt
    k_sem_take(&gesture_trigger_sem, K_FOREVER); 

    // Delay for gesture completion
    k_msleep(480);

    // Enable data streaming for collection
    StreamIMUData();  // Uncomment this line

    // Disable inference during collection
    // int gesture_index = run_inference();
    // if (gesture_index != 7){
    //     HandleOutput(gesture_index);
    // }

    // Cooldown period
    k_msleep(500); 
    
    // Flush pending interrupts
    while (k_sem_take(&gesture_trigger_sem, K_NO_WAIT) == 0);
}
```

### What StreamIMUData does:
- Extracts 100-sample gesture window from circular buffer
- Formats data as CSV: timestamp, ax, ay, az, gx, gy, gz
- Sends data over USB serial at 115200 baud
- One row per sample, 100 rows per gesture

### Running Data Collector
1. Navigate to machine_learning/ directory:
2. Run the following commands:
```bash
cd machine_learning
pip install -r requirements.txt
```
3. Run data collector:
```bash
python data_collector.py
```

### Data collection flow:
1. Script connects to nRF54L15 via USB serial port (typically /dev/ttyACM0 or COM port on Windows)
2. Waits for motion interrupt and data stream from device
3. Receives 100 samples of 6-channel IMU data
4. Prompts user with GUI window to select gesture label
5. Saves data to two files:
    - gesture_YYYYMMDD_HHMMSS_data.csv: 100 rows × 6 columns (ax, ay, az, gx, gy, gz)
    - gesture_YYYYMMDD_HHMMSS_label.csv: Single value 
6. Repeats for next gesture

### File Organization
machine_learning/
└── dataset/
    └── data/
        ├── gesture_20240115_143022_data.csv
        ├── gesture_20240115_143145_data.csv
    └── label
        ├── gesture_20240115_143145_label.csv
        ├── gesture_20240115_143022_label.csv

## Data Consolidation and Visualization
### Consolidating CSV Files
After collecting multiple gesture samples, consolidate into single dataset:
```bash
python data_consolidator.py
```

#### What it does:

- Scans dataset/ directory for all *_data.csv and *_label.csv pairs
- Loads each gesture window and corresponding label
- Stacks all samples into single dataset
- Saves as dataset/imu_gesture_data.npz with two arrays:
- features: shape (N, 100, 6) where N is number of samples
- labels: shape (N,) with gesture indices

### Visualizing Gesture Signatures
Visualize collected gestures to verify data quality:
```bash
python data_visualization.py
```

#### Visualization features:

- Interactive plot with gesture selector
- Accelerometer subplot: ax, ay, az over time
- Gyroscope subplot: gx, gy, gz over time
- Mean trajectory per gesture class
- Standard deviation shading showing variability

## Training 

### Random Forest
Navigate to Random Forest directory:
```bash
cd random_forest
python train.py
```

####  Training process:

1. **Load data**: Reads dataset/imu_gesture_data.npz
2. **Train-test split**: 80% training, 20% testing, stratified by class
3. **Model training**: sklearn RandomForestClassifier with hyperparameters
4. **Evaluation**: Accuracy
**Model saving: Exports to models/random_forest_model.pkl

#### Hyperparameters:
- **n_estimators**: Number of decision trees (default 40, optimize to 10-20 for size)
- **max_depth**: Maximum tree depth (default 6, reduce to 5 for simplicity)
- **min_samples_leaf**: Minimum samples per leaf node (increase to 10 to prevent overfitting)
- **random_state**: 42 for reproducibility

#### Converting Random Forest to C
Convert trained model to C code for embedded deployment:
```bash
python model_converter.py
```
- Generates gesture_model.h header file
- Contains decision tree structures as nested if-else statements

#### Real-Time Random Forest Validation
Test trained model with live data before deployment:

1. Prepare firmware: Ensure StreamIMUData() is enabled in main_functions.cpp and device is flashed.
2. Run predictor:
```bash
python real-time-predictor.py
```

#### Deploying Random Forest Model
After validation, deploy model to device:

1. Rename converted model:
```bash
mv gesture_model.h gesture_model.c
```
2. Replace in firmware:
```bash
cp gesture_model.c ../../gesture_app_rf/src/
```
3. Build and flash *gesture_app_rf*

### CNN
Navigate to Random Forest directory:
```bash
cd cnn
python train.py
```

####  Training process:

1. **Load data**: Reads dataset/imu_gesture_data.npz
2. **Train-test split**: 80% training, 20% testing, stratified by class
3. **Model training**: model architecture defined in *model.py*
4. **Evaluation**: Accuracy
**Model saving: Exports to best_model.h5

#### Optimize CNN Model
Reduce model size for embedded deployment using quantization:
```bash
python model_optimizer.py
```
**Optimization techniques**:
- Float32 (baseline): No optimization
- Float16: Half-precision floating point
- INT8 (quantization): 8-bit integer weights

**Generated model files**:

    model_c_headers/
    ├── model_float32.h
    ├── model_float16.h
    └── model_int8.h

#### Real-Time Random CNN Validation
Test trained model with live data before deployment:

1. Prepare firmware: Ensure StreamIMUData() is enabled in main_functions.cpp and device is flashed.
2. Run predictor:
```bash
python real-time-predictor.py
```

#### Deploying Random Forest Model
After optimization, deploy chosen model variant:

1. Rename converted model:
```bash
cd model_c_headers
cp model_float16.h gesture_model.cpp
```
2. Replace in firmware:
```bash
cp gesture_model.cpp ../../gesture_app_cnn/src/
```
3. Build and flash *gesture_app_cnn*

## Model Comparison
### Random Forest vs CNN
**Random Forest advantages**:
- Smaller model size: 50 KB vs 36-145 KB for CNN
- Faster training: Minutes vs hours for CNN
- Interpretable: Can inspect decision tree logic
- Lower RAM usage:

**CNN advantages**:
- Generalizes better to new users

### Recommendation:
- Use Random Forest for: Size-constrained deployment, fast iteration, interpretability requirements
- Use CNN for: Maximum accuracy, generalization across users, future extensibility



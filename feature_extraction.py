import pandas as pd
import os

# Path to the data and label directories, and the output file name
data_dir = 'data/Kaggle_IMU_Dataset/data/data'
label_dir = 'data/Kaggle_IMU_Dataset/data/label'
output_dir = 'data/Kaggle_IMU_Dataset/restructured_data'

# 1: SLIDE_UP, 2: SLIDE_DOWN, 3: SLIDE_LEFT, 4: SLIDE_RIGHT
target_labels = [1, 2, 3, 4]

count = 1

for data_filename in os.listdir(data_dir):
    # Load the sensor data
    df_data = pd.read_csv(os.path.join(data_dir, data_filename))

    label_filename = data_filename.replace('data', 'label')
    
    # Load the corresponding label
    df_label = pd.read_csv(os.path.join(label_dir, label_filename))

    if df_label['label'].iloc[0] not in target_labels:
        continue 
    
    # Keep only Imu1 (Index Finger) columns
    imu1_cols = [col for col in df_data.columns if 'Imu1' in col and 'orientation' not in col]

    filtered_df = df_data[['timestamp'] + imu1_cols]

    filtered_df.columns = [c.replace('Imu1_', '') for c in filtered_df.columns]

    new_filename = str(count) + '_' + "04_16_2026_" + str(df_label['label'].iloc[0]) + ".csv"

    filtered_df.to_csv(os.path.join(output_dir, new_filename), index=False)
    count += 1
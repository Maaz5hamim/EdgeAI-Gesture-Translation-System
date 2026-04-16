import pandas as pd
import os

# Path to the data and label directories, and the output file name
data_dir = 'data/Kaggle_IMU_Dataset/data/data'
label_dir = 'data/Kaggle_IMU_Dataset/data/label'
output_file = 'data/Kaggle_IMU_Dataset/restructured_index_finger_training_data.csv'

# 1: SLIDE_UP, 2: SLIDE_DOWN, 3: SLIDE_LEFT, 4: SLIDE_RIGHT
target_labels = [1, 2, 3, 4]

restructured_data = []

for data_filename in os.listdir(data_dir):
    # Load the sensor data
    df_data = pd.read_csv(os.path.join(data_dir, data_filename))

    label_filename = data_filename.replace('data', 'label')
    
    # Load the corresponding label
    df_label = pd.read_csv(os.path.join(label_dir, label_filename))
    
    # Select only Imu1 (Index Finger) columns
    imu1_cols = [col for col in df_data.columns if 'Imu1' in col and 'orientation' not in col]
    
    # Append the label column
    df_data['label'] = df_label['label'].iloc[0]

    filtered_df = df_data[df_data['label'].isin(target_labels)][['timestamp'] + imu1_cols + ['label']]

    filtered_df.columns = [c.replace('Imu1_', '') for c in filtered_df.columns]
    
    if not filtered_df.empty:
        restructured_data.append(filtered_df)

# Combine everything into one master CSV
master_df = pd.concat(restructured_data, ignore_index=True)
master_df.to_csv(output_file, index=False)

print(f"Successfully created {output_file} with {len(master_df)} rows.")
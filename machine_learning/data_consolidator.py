import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

FILTERED_LABELS = [1, 2, 3, 4]

FEATURE_COLS = [
    'timestamp',
    'Imu1_linear_accleration_x', 
    'Imu1_linear_accleration_y', 
    'Imu1_linear_accleration_z',
    'Imu1_angular_velocity_x', 
    'Imu1_angular_velocity_y', 
    'Imu1_angular_velocity_z'
]

def find_matching_files(data_dir, labels_dir):
    """
    Find matching data and label files
    data files end with _data.csv
    label files end with _label.csv
    """
    
    data_dir = Path(data_dir)
    labels_dir = Path(labels_dir)
    
    # Find all data files
    data_files = list(data_dir.glob('*_data.csv'))
    print(f"\n✓ Found {len(data_files)} data files in {data_dir}/")
    
    # Find all label files
    label_files = list(labels_dir.glob('*_label.csv'))
    print(f"✓ Found {len(label_files)} label files in {labels_dir}/")
    
    # Match by base name (remove _data.csv and _label.csv)
    matched_files = []
    unmatched_data = []
    unmatched_labels = []
    
    # Create dictionaries with base names
    data_dict = {}
    for f in data_files:
        base_name = f.name.replace('_data.csv', '')
        data_dict[base_name] = f
    
    label_dict = {}
    for f in label_files:
        base_name = f.name.replace('_label.csv', '')
        label_dict[base_name] = f
    
    # Find matches
    for base_name, data_path in data_dict.items():
        if base_name in label_dict:
            matched_files.append({
                'name': base_name,
                'data_path': data_path,
                'label_path': label_dict[base_name]
            })
        else:
            unmatched_data.append(base_name)
    
    # Find unmatched labels
    for base_name in label_dict.keys():
        if base_name not in data_dict:
            unmatched_labels.append(base_name)
    
    print(f"\n✓ Matched pairs: {len(matched_files)}")
    
    if unmatched_data:
        print(f"⚠ Unmatched data files: {len(unmatched_data)}")
        if len(unmatched_data) <= 10:
            for name in unmatched_data:
                print(f"  - {name}")
    
    if unmatched_labels:
        print(f"⚠ Unmatched label files: {len(unmatched_labels)}")
        if len(unmatched_labels) <= 10:
            for name in unmatched_labels:
                print(f"  - {name}")
    
    return matched_files

def load_label_file(label_path):
    """
    Load label from label CSV file
    Returns the gesture label if it exists within filtered list
    """
    try:
        df = pd.read_csv(label_path)

        label = int(df['label'].iloc[0])

        if label in FILTERED_LABELS:
            return label
        
        return None
        
    except Exception as e:
        print(f"✗ Error loading label from {label_path.name}: {e}")
        return None

def load_data_file(data_path):
    """
    Load sensor data from data CSV file
    Returns dict with timestamps, features, and stats
    """
    try:
        df = pd.read_csv(data_path)
        
        features = df[FEATURE_COLS].values
        
        return features
        
    except Exception as e:
        print(f"✗ Error loading data from {data_path.name}: {e}")
        return None

def load_all_data(matched_files):
    """
    Load all matched data and label files
    """
    print("\n" + "=" * 80)
    print("LOADING ALL DATA")
    print("=" * 80)
    
    sequences = []
    labels = []
    
    print(f"\nProcessing {len(matched_files)} files...")
    
    for file_info in tqdm(matched_files, desc="Loading"):
        # Load label
        label = load_label_file(file_info['label_path'])
        if label is None:
            continue

        # Load data
        data = load_data_file(file_info['data_path'])
        
        sequences.append(data)
        labels.append(label)
    
    labels = np.array(labels)
    
    return sequences, labels

def save_consolidated_data(sequences, labels, output_path='imu_gesture_data.npz'):
    """
    Save all data in a single compressed NumPy file
    """
    print("\n" + "=" * 80)
    print("SAVING CONSOLIDATED DATA")
    print("=" * 80)
    
    features_array = np.empty(len(sequences), dtype=object)
    
    for i, features in enumerate(sequences):
        features_array[i] = features

    np.savez_compressed(
        output_path,
        features=features_array,
        labels=labels,
    )
    
    file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
    
    print(f"\n✓ Data saved to: {output_path}")
    print(f"  File size: {file_size:.2f} MB")
    print(f"  Total sequences: {len(sequences)}")

    return output_path

def load_consolidated_data(filepath='imu_gesture_data.npz'):
    """
    Load the consolidated data file
    
    Returns:
        sequences: list of dicts with 'timestamps' and 'features'
        labels: numpy array of gesture labels
        metadata: list of metadata dicts
    """

    data = np.load(filepath, allow_pickle=True)
    
    timestamps_array = data['timestamps']
    features_array = data['features']
    labels = data['labels']
    metadata = data['metadata']
    
    # Reconstruct sequences
    sequences = []
    for i in range(len(labels)):
        sequences.append({
            'timestamps': timestamps_array[i],
            'features': features_array[i],
            'stats': {
                'n_samples': len(timestamps_array[i]),
                'duration': timestamps_array[i][-1] - timestamps_array[i][0] if len(timestamps_array[i]) > 1 else 0
            }
        })
    
    print(f"✓ Loaded {len(sequences)} sequences")
    print(f"  Gesture types: {len(set(labels))}")
    print(f"  Features per sample: {sequences[0]['features'].shape[1]}")
    
    return sequences, labels, list(metadata)

if __name__ == "__main__":
    DATA_DIR = '/Users/maazshamim/Library/Mobile Documents/com~apple~CloudDocs/GitHub/EdgeAI-Gesture-Translation-System/data/Kaggle_IMU_Dataset/data/data_clean'     
    LABELS_DIR = '/Users/maazshamim/Library/Mobile Documents/com~apple~CloudDocs/GitHub/EdgeAI-Gesture-Translation-System/data/Kaggle_IMU_Dataset/data/label'         
    OUTPUT_FILE = 'imu_gesture_data.npz' 
    
    # Step 1: Find matching files
    matched_files = find_matching_files(DATA_DIR, LABELS_DIR)
    
    # Step 2: Load all data
    sequences, labels = load_all_data(matched_files)
    
    # Step 3: Save consolidated data
    save_consolidated_data(sequences, labels, OUTPUT_FILE)

    
    # ========================================================================
    # TEST LOADING
    # ========================================================================
    
    # if sequences is not None:
    #     print("\n" + "=" * 80)
    #     print("TESTING DATA LOADING")
    #     print("=" * 80)
        
    #     # Test loading the saved file
    #     sequences_test, labels_test, metadata_test = load_consolidated_data(OUTPUT_FILE)
        
    #     print(f"\n✓ Successfully loaded and verified data!")
    #     print(f"  Example sequence shape: {sequences_test[0]['features'].shape}")
    #     print(f"  Example label: {labels_test[0]} ({GESTURE_MAP[labels_test[0]]})")
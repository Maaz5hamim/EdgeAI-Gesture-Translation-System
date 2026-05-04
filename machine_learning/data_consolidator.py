import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import warnings
from constant import FEATURE_COLS, WINDOW_SIZE
warnings.filterwarnings('ignore')



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
        
        return label
        
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
        label = load_label_file(file_info['label_path'])
        data = load_data_file(file_info['data_path'])
        
        # VALIDATION: Only keep windows that are exactly 100x6
        if data is not None and data.shape == (WINDOW_SIZE, len(FEATURE_COLS)) and label is not None:
            sequences.append(data)
            labels.append(label)
        else:
            # This identifies the "jagged" files during consolidation
            print(f"Skipping {file_info['name']}: Invalid shape {data.shape if data is not None else 'None'}")
    
    return sequences, labels

def save_consolidated_data(sequences, labels, output_path):
    """
    Save all data in a single compressed NumPy file
    """
    print("\n" + "=" * 80)
    print("SAVING CONSOLIDATED DATA")
    print("=" * 80)
    
    features = np.array(sequences, dtype=np.float32)
    labels = np.array(labels)

    np.savez_compressed(
        output_path,
        features=features,
        labels=labels,
    )
    
    file_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
    
    print(f"\n✓ Data saved to: {output_path}")
    print(f"  File size: {file_size:.2f} MB")
    print(f"  Total sequences: {len(sequences)}")

    return output_path

if __name__ == "__main__":
    DATA_DIR = './dataset/data'     
    LABELS_DIR = './dataset/label'      
    OUTPUT_FILE = 'dataset/gesture_data_consolidated.npz' 
    
    # Step 1: Find matching files
    matched_files = find_matching_files(DATA_DIR, LABELS_DIR)
    
    # Step 2: Load all data
    sequences, labels = load_all_data(matched_files)
    
    # Step 3: Save consolidated data
    save_consolidated_data(sequences, labels, OUTPUT_FILE)
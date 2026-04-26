"""
Explore consolidated IMU data
Analyze frequency, sample counts, distributions, and temporal characteristics
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# ============================================================================
# CONFIGURATION
# ============================================================================

GESTURE_MAP = {
    1: 'SLIDE_UP',
    2: 'SLIDE_DOWN',
    3: 'SLIDE_LEFT',
    4: 'SLIDE_RIGHT'
}

# ============================================================================
# DATA LOADING
# ============================================================================

def load_data(filepath='imu_gesture_data_filtered.npz'):
    """
    Load consolidated data file
    
    Returns:
        features: numpy array (object) where each element is a 2D array (n_samples, 7)
        labels: numpy array of labels
    """
    print("\n" + "=" * 80)
    print("LOADING DATA")
    print("=" * 80)
    print(f"\nFile: {filepath}")
    
    data = np.load(filepath, allow_pickle=True)
    
    features = data['features']
    labels = data['labels']
    
    print(f"✓ Loaded {len(labels)} sequences")
    print(f"  Features shape: {features.shape}")
    print(f"  Labels shape: {labels.shape}")
    
    # Check first sequence structure
    sample = features[0]
    print(f"\nFirst sequence:")
    print(f"  Shape: {sample.shape}")
    print(f"  Columns: [timestamp, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z]")
    print(f"  Label: {labels[0]} ({GESTURE_MAP.get(labels[0], 'UNKNOWN')})")
    
    return features, labels

def compute_basic_stats(features, labels):
    """
    Compute basic statistics about the dataset
    """
    print("\n" + "=" * 80)
    print("BASIC STATISTICS")
    print("=" * 80)
    
    n_sequences = len(labels)
    n_gestures = len(set(labels))
    
    # Get sequence lengths (number of samples per sequence)
    sequence_lengths = [len(seq) for seq in features]
    
    print(f"\nDataset Overview:")
    print(f"-" * 80)
    print(f"  Total sequences:        {n_sequences}")
    print(f"  Number of gesture types: {n_gestures}")
    print(f"  Features per sample:     {features[0].shape[1]} (timestamp + 6 sensors)")
    
    print(f"\nSequence Length (samples per recording):")
    print(f"-" * 80)
    print(f"  Min:     {np.min(sequence_lengths):6d} samples")
    print(f"  Max:     {np.max(sequence_lengths):6d} samples")
    print(f"  Mean:    {np.mean(sequence_lengths):6.1f} samples")
    print(f"  Median:  {np.median(sequence_lengths):6.1f} samples")
    print(f"  Std:     {np.std(sequence_lengths):6.1f} samples")
    print(f"  25th %:  {np.percentile(sequence_lengths, 25):6.1f} samples")
    print(f"  75th %:  {np.percentile(sequence_lengths, 75):6.1f} samples")
    
    return sequence_lengths

def analyze_label_distribution(labels):
    """
    Analyze distribution of gesture labels
    """
    print("\n" + "=" * 80)
    print("GESTURE LABEL DISTRIBUTION")
    print("=" * 80)
    
    unique_labels, counts = np.unique(labels, return_counts=True)
    
    print(f"\nTotal recordings: {len(labels)}")
    print(f"-" * 80)
    
    for label, count in zip(unique_labels, counts):
        percentage = (count / len(labels)) * 100
        gesture_name = GESTURE_MAP.get(label, 'UNKNOWN')
        bar = '█' * int(percentage / 2)
        print(f"  {label} - {gesture_name:15s}: {count:4d} ({percentage:5.1f}%) {bar}")
    
    # Check balance
    max_count = np.max(counts)
    min_count = np.min(counts)
    imbalance_ratio = max_count / min_count if min_count > 0 else float('inf')
    
    print(f"\nDataset Balance:")
    print(f"-" * 80)
    print(f"  Max count: {max_count}")
    print(f"  Min count: {min_count}")
    print(f"  Imbalance ratio: {imbalance_ratio:.2f}:1")
    
    if imbalance_ratio < 1.5:
        print(f"  Status: ✓ Well balanced")
    elif imbalance_ratio < 3:
        print(f"  Status: ⚠ Slightly imbalanced")
    else:
        print(f"  Status: ⚠ Significantly imbalanced - consider balancing techniques")
    
    return unique_labels, counts

def analyze_temporal_characteristics(features, labels):
    """
    Analyze timing/frequency characteristics
    """
    print("\n" + "=" * 80)
    print("TEMPORAL CHARACTERISTICS ANALYSIS")
    print("=" * 80)
    
    durations = []
    mean_intervals = []
    sampling_rates = []
    cvs = []  # Coefficient of variation
    
    for seq in features:
        timestamps = seq[:, 0]
        
        if len(timestamps) < 2:
            continue
        
        # Duration
        duration = timestamps[-1] - timestamps[0]
        durations.append(duration)
        
        # Time intervals
        time_diffs = np.diff(timestamps)
        valid_diffs = time_diffs[time_diffs > 0]
        
        if len(valid_diffs) > 0:
            mean_interval = np.mean(valid_diffs)
            std_interval = np.std(valid_diffs)
            mean_intervals.append(mean_interval)
            
            # Sampling rate
            sampling_rate = 1.0 / mean_interval if mean_interval > 0 else 0
            sampling_rates.append(sampling_rate)
            
            # Coefficient of variation (measure of regularity)
            cv = (std_interval / mean_interval * 100) if mean_interval > 0 else 0
            cvs.append(cv)
    
    print(f"\nRecording Duration:")
    print(f"-" * 80)
    print(f"  Min:     {np.min(durations):8.4f} time units")
    print(f"  Max:     {np.max(durations):8.4f} time units")
    print(f"  Mean:    {np.mean(durations):8.4f} time units")
    print(f"  Median:  {np.median(durations):8.4f} time units")
    print(f"  Std:     {np.std(durations):8.4f} time units")
    
    print(f"\nSampling Rate:")
    print(f"-" * 80)
    print(f"  Min:     {np.min(sampling_rates):8.2f} Hz")
    print(f"  Max:     {np.max(sampling_rates):8.2f} Hz")
    print(f"  Mean:    {np.mean(sampling_rates):8.2f} Hz")
    print(f"  Median:  {np.median(sampling_rates):8.2f} Hz")
    print(f"  Std:     {np.std(sampling_rates):8.2f} Hz")
    
    print(f"\nSampling Interval:")
    print(f"-" * 80)
    print(f"  Min:     {np.min(mean_intervals):8.6f} time units")
    print(f"  Max:     {np.max(mean_intervals):8.6f} time units")
    print(f"  Mean:    {np.mean(mean_intervals):8.6f} time units")
    print(f"  Median:  {np.median(mean_intervals):8.6f} time units")
    
    print(f"\nSampling Regularity (Coefficient of Variation):")
    print(f"-" * 80)
    print(f"  Mean CV: {np.mean(cvs):8.2f}%")
    print(f"  Median CV: {np.median(cvs):8.2f}%")
    
    mean_cv = np.mean(cvs)
    if mean_cv < 10:
        print(f"  Assessment: ✓ UNIFORM sampling")
        print(f"  Recommendation: Simple padding/truncation OK")
    elif mean_cv < 30:
        print(f"  Assessment: ⚠ SLIGHTLY IRREGULAR sampling")
        print(f"  Recommendation: Time-based interpolation recommended")
    else:
        print(f"  Assessment: ⚠ HIGHLY IRREGULAR sampling")
        print(f"  Recommendation: Time-based interpolation REQUIRED")
    
    return {
        'durations': durations,
        'sampling_rates': sampling_rates,
        'mean_intervals': mean_intervals,
        'cvs': cvs
    }

def analyze_per_gesture_timing(features, labels):
    """
    Analyze timing characteristics per gesture type
    """
    print("\n" + "=" * 80)
    print("PER-GESTURE TIMING ANALYSIS")
    print("=" * 80)
    
    unique_labels = sorted(set(labels))
    
    for label in unique_labels:
        gesture_name = GESTURE_MAP.get(label, 'UNKNOWN')
        label_mask = labels == label
        label_features = features[label_mask]
        
        print(f"\n{gesture_name} (Label {label}):")
        print(f"-" * 80)
        
        lengths = [len(seq) for seq in label_features]
        durations = []
        rates = []
        
        for seq in label_features:
            timestamps = seq[:, 0]
            if len(timestamps) > 1:
                duration = timestamps[-1] - timestamps[0]
                durations.append(duration)
                
                time_diffs = np.diff(timestamps)
                valid_diffs = time_diffs[time_diffs > 0]
                if len(valid_diffs) > 0:
                    mean_interval = np.mean(valid_diffs)
                    if mean_interval > 0:
                        rates.append(1.0 / mean_interval)
        
        print(f"  Recordings: {len(label_features)}")
        print(f"  Samples per recording: {np.mean(lengths):.1f} ± {np.std(lengths):.1f}")
        if durations:
            print(f"  Duration: {np.mean(durations):.4f} ± {np.std(durations):.4f} time units")
        if rates:
            print(f"  Sampling rate: {np.mean(rates):.2f} ± {np.std(rates):.2f} Hz")

def analyze_sensor_ranges(features):
    """
    Analyze the range of sensor values
    """
    print("\n" + "=" * 80)
    print("SENSOR VALUE RANGES")
    print("=" * 80)
    
    sensor_names = ['Timestamp', 'Accel_X', 'Accel_Y', 'Accel_Z', 'Gyro_X', 'Gyro_Y', 'Gyro_Z']
    
    # Collect all values for each sensor
    all_values = [[] for _ in range(7)]
    
    for seq in features:
        for i in range(7):
            all_values[i].extend(seq[:, i])
    
    print(f"\nValue ranges across all recordings:")
    print(f"-" * 80)
    
    for i, name in enumerate(sensor_names):
        values = np.array(all_values[i])
        print(f"\n{name}:")
        print(f"  Min:    {np.min(values):10.4f}")
        print(f"  Max:    {np.max(values):10.4f}")
        print(f"  Mean:   {np.mean(values):10.4f}")
        print(f"  Std:    {np.std(values):10.4f}")
        print(f"  Median: {np.median(values):10.4f}")

def visualize_distributions(features, labels, temporal_stats, sequence_lengths):
    """
    Create comprehensive distribution visualizations
    """
    print("\n" + "=" * 80)
    print("GENERATING VISUALIZATIONS")
    print("=" * 80)
    
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Label Distribution (Bar Chart)
    ax1 = plt.subplot(3, 3, 1)
    unique_labels, counts = np.unique(labels, return_counts=True)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    bars = ax1.bar([GESTURE_MAP[l] for l in unique_labels], counts,
                   color=colors[:len(unique_labels)], alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Count', fontsize=12, fontweight='bold')
    ax1.set_title('Gesture Distribution', fontsize=14, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    # 2. Sequence Length Distribution
    ax2 = plt.subplot(3, 3, 2)
    ax2.hist(sequence_lengths, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
    ax2.axvline(np.mean(sequence_lengths), color='red', linestyle='--', linewidth=2,
               label=f'Mean: {np.mean(sequence_lengths):.0f}')
    ax2.axvline(np.median(sequence_lengths), color='green', linestyle='--', linewidth=2,
               label=f'Median: {np.median(sequence_lengths):.0f}')
    ax2.set_xlabel('Samples per Recording', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax2.set_title('Sequence Length Distribution', fontsize=14, fontweight='bold', pad=10)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 3. Duration Distribution
    ax3 = plt.subplot(3, 3, 3)
    durations = temporal_stats['durations']
    ax3.hist(durations, bins=30, color='coral', alpha=0.7, edgecolor='black')
    ax3.axvline(np.mean(durations), color='red', linestyle='--', linewidth=2,
               label=f'Mean: {np.mean(durations):.4f}')
    ax3.set_xlabel('Duration (time units)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax3.set_title('Recording Duration Distribution', fontsize=14, fontweight='bold', pad=10)
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 4. Sampling Rate Distribution
    ax4 = plt.subplot(3, 3, 4)
    sampling_rates = temporal_stats['sampling_rates']
    ax4.hist(sampling_rates, bins=30, color='lightgreen', alpha=0.7, edgecolor='black')
    ax4.axvline(np.mean(sampling_rates), color='red', linestyle='--', linewidth=2,
               label=f'Mean: {np.mean(sampling_rates):.1f} Hz')
    ax4.axvline(np.median(sampling_rates), color='green', linestyle='--', linewidth=2,
               label=f'Median: {np.median(sampling_rates):.1f} Hz')
    ax4.set_xlabel('Sampling Rate (Hz)', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax4.set_title('Sampling Rate Distribution', fontsize=14, fontweight='bold', pad=10)
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # 5. Coefficient of Variation
    ax5 = plt.subplot(3, 3, 5)
    cvs = temporal_stats['cvs']
    ax5.hist(cvs, bins=30, color='mediumpurple', alpha=0.7, edgecolor='black')
    ax5.axvline(10, color='green', linestyle=':', linewidth=2, label='Uniform')
    ax5.axvline(30, color='orange', linestyle=':', linewidth=2, label='Irregular')
    ax5.set_xlabel('Coefficient of Variation (%)', fontsize=11, fontweight='bold')
    ax5.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax5.set_title('Sampling Regularity', fontsize=14, fontweight='bold', pad=10)
    ax5.legend(fontsize=10)
    ax5.grid(True, alpha=0.3)
    
    # 6. Box Plot - Sequence Lengths by Gesture
    ax6 = plt.subplot(3, 3, 6)
    lengths_by_gesture = []
    gesture_labels = []
    for label in unique_labels:
        mask = labels == label
        lengths = [len(seq) for seq in features[mask]]
        lengths_by_gesture.append(lengths)
        gesture_labels.append(GESTURE_MAP[label])
    
    bp = ax6.boxplot(lengths_by_gesture, labels=gesture_labels, patch_artist=True)
    for patch, color in zip(bp['boxes'], colors[:len(unique_labels)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax6.set_ylabel('Samples per Recording', fontsize=11, fontweight='bold')
    ax6.set_title('Sequence Length by Gesture', fontsize=14, fontweight='bold', pad=10)
    ax6.grid(True, alpha=0.3, axis='y')
    plt.setp(ax6.xaxis.get_majorticklabels(), rotation=15, ha='right')
    
    # 7. Cumulative Distribution - Sequence Lengths
    ax7 = plt.subplot(3, 3, 7)
    sorted_lengths = np.sort(sequence_lengths)
    cumulative = np.arange(1, len(sorted_lengths) + 1) / len(sorted_lengths) * 100
    ax7.plot(sorted_lengths, cumulative, linewidth=2.5, color='steelblue')
    ax7.axhline(50, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='50th percentile')
    ax7.axhline(90, color='orange', linestyle='--', linewidth=1.5, alpha=0.7, label='90th percentile')
    ax7.set_xlabel('Number of Samples', fontsize=11, fontweight='bold')
    ax7.set_ylabel('Cumulative Percentage (%)', fontsize=11, fontweight='bold')
    ax7.set_title('Cumulative Distribution', fontsize=14, fontweight='bold', pad=10)
    ax7.legend(fontsize=10)
    ax7.grid(True, alpha=0.3)
    
    # 8. Scatter - Duration vs Samples
    ax8 = plt.subplot(3, 3, 8)
    durations_list = []
    lengths_list = []
    colors_list = []
    for i, seq in enumerate(features):
        if len(seq) > 1:
            timestamps = seq[:, 0]
            duration = timestamps[-1] - timestamps[0]
            durations_list.append(duration)
            lengths_list.append(len(seq))
            colors_list.append(labels[i])
    
    scatter = ax8.scatter(durations_list, lengths_list, c=colors_list, 
                         cmap='Set1', s=30, alpha=0.6, edgecolors='black', linewidth=0.5)
    ax8.set_xlabel('Duration (time units)', fontsize=11, fontweight='bold')
    ax8.set_ylabel('Number of Samples', fontsize=11, fontweight='bold')
    ax8.set_title('Duration vs Samples', fontsize=14, fontweight='bold', pad=10)
    ax8.grid(True, alpha=0.3)
    
    # 9. Sampling Rate by Gesture
    ax9 = plt.subplot(3, 3, 9)
    rates_by_gesture = []
    for label in unique_labels:
        mask = labels == label
        label_features = features[mask]
        rates = []
        for seq in label_features:
            if len(seq) > 1:
                timestamps = seq[:, 0]
                time_diffs = np.diff(timestamps)
                valid_diffs = time_diffs[time_diffs > 0]
                if len(valid_diffs) > 0:
                    mean_interval = np.mean(valid_diffs)
                    if mean_interval > 0:
                        rates.append(1.0 / mean_interval)
        rates_by_gesture.append(rates)
    
    bp2 = ax9.boxplot(rates_by_gesture, labels=gesture_labels, patch_artist=True)
    for patch, color in zip(bp2['boxes'], colors[:len(unique_labels)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax9.set_ylabel('Sampling Rate (Hz)', fontsize=11, fontweight='bold')
    ax9.set_title('Sampling Rate by Gesture', fontsize=14, fontweight='bold', pad=10)
    ax9.grid(True, alpha=0.3, axis='y')
    plt.setp(ax9.xaxis.get_majorticklabels(), rotation=15, ha='right')
    
    plt.tight_layout()
    plt.savefig('visualization/data_exploration_comprehensive.png', dpi=300, bbox_inches='tight')
    
    print("✓ Comprehensive visualization saved as 'data_exploration_comprehensive.png'")

def visualize_sample_sequences(features, labels, n_samples=4):
    """
    Visualize sample sequences from each gesture
    """
    unique_labels = sorted(set(labels))
    
    fig, axes = plt.subplots(len(unique_labels), 2, figsize=(16, 4*len(unique_labels)))
    if len(unique_labels) == 1:
        axes = axes.reshape(1, -1)
    
    fig.suptitle('Sample IMU Sequences (Timestamp + 6 Sensors)', fontsize=16, fontweight='bold')
    
    for idx, label in enumerate(unique_labels):
        # Get one sample for this gesture
        label_mask = labels == label
        label_features = features[label_mask]
        
        if len(label_features) == 0:
            continue
        
        # Pick random sample
        sample_idx = np.random.randint(0, len(label_features))
        seq = label_features[sample_idx]
        
        timestamps = seq[:, 0]
        acc_data = seq[:, 1:4]  # Columns 1, 2, 3: accel x, y, z
        gyro_data = seq[:, 4:7]  # Columns 4, 5, 6: gyro x, y, z
        
        gesture_name = GESTURE_MAP.get(label, 'UNKNOWN')
        
        # Normalize timestamps
        timestamps_norm = timestamps - timestamps[0]
        
        # Plot accelerometer
        ax1 = axes[idx, 0]
        ax1.plot(timestamps_norm, acc_data[:, 0], 'o-', label='X', markersize=3, alpha=0.7, linewidth=1.5)
        ax1.plot(timestamps_norm, acc_data[:, 1], 's-', label='Y', markersize=3, alpha=0.7, linewidth=1.5)
        ax1.plot(timestamps_norm, acc_data[:, 2], '^-', label='Z', markersize=3, alpha=0.7, linewidth=1.5)
        ax1.set_title(f'{gesture_name} - Linear Acceleration\n({len(seq)} samples, duration: {timestamps_norm[-1]:.3f})',
                     fontsize=12, fontweight='bold')
        ax1.set_xlabel('Time (relative)', fontsize=10)
        ax1.set_ylabel('Acceleration (m/s²)', fontsize=10)
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)
        
        # Plot gyroscope
        ax2 = axes[idx, 1]
        ax2.plot(timestamps_norm, gyro_data[:, 0], 'o-', label='X', markersize=3, alpha=0.7, linewidth=1.5)
        ax2.plot(timestamps_norm, gyro_data[:, 1], 's-', label='Y', markersize=3, alpha=0.7, linewidth=1.5)
        ax2.plot(timestamps_norm, gyro_data[:, 2], '^-', label='Z', markersize=3, alpha=0.7, linewidth=1.5)
        ax2.set_title(f'{gesture_name} - Angular Velocity\n({len(seq)} samples, duration: {timestamps_norm[-1]:.3f})',
                     fontsize=12, fontweight='bold')
        ax2.set_xlabel('Time (relative)', fontsize=10)
        ax2.set_ylabel('Angular Velocity (rad/s)', fontsize=10)
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('visualization/sample_sequences_visualization.png', dpi=300, bbox_inches='tight')
    
    print("✓ Sample sequences saved as 'sample_sequences_visualization.png'")

def explore_data(filepath='imu_gesture_data_filtered.npz'):
    """
    Complete data exploration pipeline
    """
    print("\n" + "=" * 80)
    print("IMU DATA EXPLORATION PIPELINE")
    print("=" * 80)
    
    # Load data
    features, labels = load_data(filepath)
    
    # Basic statistics
    sequence_lengths = compute_basic_stats(features, labels)
    
    # Label distribution
    analyze_label_distribution(labels)
    
    # Temporal analysis
    temporal_stats = analyze_temporal_characteristics(features, labels)
    
    # Per-gesture timing
    analyze_per_gesture_timing(features, labels)
    
    # Sensor ranges
    analyze_sensor_ranges(features)
    
    # Visualizations
    visualize_distributions(features, labels, temporal_stats, sequence_lengths)
    visualize_sample_sequences(features, labels)

if __name__ == "__main__":
    
    # Set your data file path
    DATA_FILE = 'data/imu_gesture_data.npz'
    
    # Run exploration
    explore_data(DATA_FILE)
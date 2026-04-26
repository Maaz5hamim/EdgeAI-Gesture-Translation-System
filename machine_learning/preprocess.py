import numpy as np
from scipy.interpolate import interp1d

from sklearn.preprocessing import StandardScaler

import warnings
warnings.filterwarnings('ignore')


class Preprocess:    
    def __init__(self, target_length=100, target_sample_rate=None, 
                 normalize=True, augment=True, augmentation_factor=3):
        self.target_length = target_length
        self.target_sample_rate = target_sample_rate
        self.normalize = normalize
        self.augment = augment
        self.augmentation_factor = augmentation_factor
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.actual_sample_rate = None
        
        # Feature indices (assuming timestamp + 6 sensors)
        self.timestamp_idx = 0
        self.sensor_start_idx = 1
        self.n_sensors = 6
    
    def determine_sample_rate(self, features):
        """
        Determine appropriate sampling rate from data
        
        Args:
            features: Array of sequences (each is [timestamp, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z])
        """
        if self.target_sample_rate is not None:
            self.actual_sample_rate = self.target_sample_rate
            return
        
        # Calculate median sampling rate across all sequences
        all_rates = []
        
        for seq in features:
            timestamps = seq[:, self.timestamp_idx]
            
            if len(timestamps) > 1:
                time_diffs = np.diff(timestamps)
                valid_diffs = time_diffs[time_diffs > 0]
                
                if len(valid_diffs) > 0:
                    mean_interval = np.mean(valid_diffs)
                    if mean_interval > 0:
                        rate = 1.0 / mean_interval
                        all_rates.append(rate)
        
        if all_rates:
            self.actual_sample_rate = np.median(all_rates)
            print(f"\n✓ Auto-detected sampling rate: {self.actual_sample_rate:.2f} Hz")
        else:
            self.actual_sample_rate = 50.0  # Default fallback
            print(f"\n⚠ Using default sampling rate: {self.actual_sample_rate:.2f} Hz")
    
    def resample_sequence(self, sequence):
        """
        Resample a single sequence to uniform time intervals
        
        Args:
            sequence: Array of shape (n_samples, 7) [timestamp + 6 sensors]
        
        Returns:
            Resampled sequence of shape (target_length, 6) [only sensors, no timestamp]
        """
        timestamps = sequence[:, self.timestamp_idx]
        sensor_data = sequence[:, self.sensor_start_idx:self.sensor_start_idx + self.n_sensors]
        
        # Normalize timestamps to start from 0
        timestamps_norm = timestamps - timestamps[0]
        duration = timestamps_norm[-1]
        
        # Handle edge cases
        if duration == 0 or len(timestamps) < 2:
            # Repeat last sample
            return np.repeat(sensor_data[-1:], self.target_length, axis=0)
        
        # Create uniform time grid
        uniform_time = np.linspace(0, duration, self.target_length)
        
        # Interpolate each sensor channel
        resampled = np.zeros((self.target_length, self.n_sensors))
        
        for i in range(self.n_sensors):
            try:
                interpolator = interp1d(
                    timestamps_norm,
                    sensor_data[:, i],
                    kind='linear',
                    fill_value='extrapolate',
                    bounds_error=False
                )
                resampled[:, i] = interpolator(uniform_time)
            except Exception as e:
                # Fallback: repeat last value
                print(f"⚠ Interpolation failed, using fallback")
                resampled[:, i] = sensor_data[-1, i]
        
        return resampled
    
    def pad_or_truncate(self, sequence):
        """
        Simple padding/truncation (alternative to resampling)
        
        Args:
            sequence: Array of shape (n_samples, 7)
        
        Returns:
            Padded/truncated sequence of shape (target_length, 6)
        """
        sensor_data = sequence[:, self.sensor_start_idx:self.sensor_start_idx + self.n_sensors]
        
        current_length = len(sensor_data)
        
        if current_length >= self.target_length:
            # Truncate
            return sensor_data[:self.target_length]
        else:
            # Pad with last value
            padding = np.repeat(sensor_data[-1:], self.target_length - current_length, axis=0)
            return np.vstack([sensor_data, padding])
    
    def augment_sequence(self, sequence):
        """
        Data augmentation techniques
        
        Args:
            sequence: Array of shape (target_length, 6)
        
        Returns:
            List of augmented sequences
        """
        augmented = []
        
        # 1. Original
        augmented.append(sequence.copy())
        
        # 2. Gaussian noise
        noise_level = 0.01
        noise = np.random.normal(0, noise_level, sequence.shape)
        augmented.append(sequence + noise)
        
        # 3. Scaling
        scale_factor = np.random.uniform(0.9, 1.1)
        augmented.append(sequence * scale_factor)
        
        # 4. Time shift (circular)
        shift = np.random.randint(-5, 5)
        augmented.append(np.roll(sequence, shift, axis=0))
        
        # 5. Rotation (accelerometer only - first 3 channels)
        angle = np.random.uniform(-0.1, 0.1)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        rotation_matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])
        seq_aug = sequence.copy()
        seq_aug[:, :3] = seq_aug[:, :3] @ rotation_matrix.T
        augmented.append(seq_aug)
        
        return augmented
    
    def fit(self, features):
        """
        Fit the scaler on training data
        
        Args:
            features: Array of sequences
        """
        # Determine sampling rate
        self.determine_sample_rate(features)
        
        # Resample all sequences
        print(f"\nResampling {len(features)} sequences to {self.target_length} samples...")
        resampled_sequences = []
        
        for seq in features:
            resampled = self.resample_sequence(seq)
            resampled_sequences.append(resampled)
        
        # Fit scaler
        if self.normalize:
            print("Fitting scaler...")
            all_data = np.vstack(resampled_sequences)
            self.scaler.fit(all_data)
            
            print(f"Feature means: {self.scaler.mean_}")
            print(f"Feature stds: {self.scaler.scale_}")
        
        self.is_fitted = True
    
    def transform(self, features, labels):
        """
        Transform sequences with resampling, normalization, and optional augmentation
        
        Args:
            features: Array of sequences
            labels: Array of labels
            augmentation_factor: Number of augmented versions per sample
        
        Returns:
            X: Processed features (n_samples, target_length, n_sensors)
            y: One-hot encoded labels
            y_original: Original label integers
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor must be fitted first! Call fit() before transform()")
        
        processed_sequences = []
        processed_labels = []
        
        # Resample and normalize
        print(f"\nProcessing {len(features)} sequences...")
        for seq, label in zip(features, labels):
            # Resample
            resampled = self.resample_sequence(seq)
            
            # Normalize
            if self.normalize:
                resampled = self.scaler.transform(resampled)
            
            # Augment
            if self.augment:
                augmented = self.augment_sequence(resampled)
                for aug_seq in augmented[:self.augmentation_factor]:
                    processed_sequences.append(aug_seq)
                    processed_labels.append(label)
            else:
                processed_sequences.append(resampled)
                processed_labels.append(label)
        
        # Convert to arrays
        X = np.array(processed_sequences, dtype=np.float32)
        y_original = np.array(processed_labels, dtype=np.int32)
        
        # One-hot encode labels (assuming labels are 1, 2, 3, 4)
        n_classes = len(np.unique(labels))
        y = np.zeros((len(y_original), n_classes), dtype=np.float32)
        for i, label in enumerate(y_original):
            y[i, label - 1] = 1  # Convert 1-4 to 0-3
        
        print(f"  Shape: {X.shape}")
        print(f"  Labels shape: {y.shape}")
        
        return X, y, y_original
    
    def fit_transform(self, features, labels):
        """
        Fit and transform in one step
        """
        self.fit(features)
        return self.transform(features, labels)
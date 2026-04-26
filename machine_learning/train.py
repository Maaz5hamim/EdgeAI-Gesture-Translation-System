import numpy as np
from sklearn.model_selection import train_test_split
import tensorflow as tf
import warnings
from model import DeepConvLSTM
from preprocess import Preprocess
from tensorflow import keras
from sklearn.model_selection import StratifiedKFold
warnings.filterwarnings('ignore')

def load_data(data_file):    
    data = np.load(data_file, allow_pickle=True)
    features = data['features']
    labels = data['labels']
    
    return features, labels

def train(X, y, y_original,
            n_splits=5,
            epochs=100,
            batch_size=32,
            learning_rate=0.001,
            random_state=42):
    
    # Set random seeds
    np.random.seed(random_state)
    tf.random.set_seed(random_state)
    
    n_samples, window_size, n_features = X.shape
    n_classes = y.shape[1]

    model = DeepConvLSTM(
            window_size=window_size,
            n_features=n_features,
            n_classes=n_classes
    )

    model.build_model()
    model.compile_model(learning_rate=learning_rate)
    
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, 
                             random_state=random_state)    
        
    for fold_num, (train_idx, val_idx) in enumerate(skf.split(X, y_original)):
        # Split data
        X_train = X[train_idx]
        y_train = y[train_idx]
        X_val = X[val_idx]
        y_val = y[val_idx]
        
        # Train fold
        model.train(
            X_train, y_train,
            X_val, y_val,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0
        )

        # Evaluate
        val_loss, val_accuracy = model.model.evaluate(X_val, y_val, verbose=0)
        
        print("\n" + "-" * 20 + f'{fold_num} Fold' + "-" * 20)
        print(f"  Validation Loss: {val_loss:.4f}")
        print(f"  Validation Accuracy: {val_accuracy * 100:.2f}%")
        print("-" * 20 + "-" * len(str(fold_num) + " Fold") + "-" * 20)
        
        # Clear session to free memory
        keras.backend.clear_session()
    
    return model

if __name__ == "__main__":
    data_file = 'data/imu_gesture_data.npz'

    # Preprocessing parameters
    target_length = 40
    normalize = True
    augment = False
    augmentation_factor = 3

    # Training Hyperparameters
    n_splits = 2
    epochs = 100
    batch_size = 32
    learning_rate = 0.001
    random_state = 42

    # Train Test split
    test_split = 0.2

    print("\n" + "=" * 70)
    print("LOADING DATA")
    print("=" * 70)

    features, labels = load_data(data_file)

    print("Data loaded successfully.")

    print("\n" + "=" * 70)
    print("PREPROCESSING DATA")
    print("=" * 70)

    preprocessor = Preprocess(
        target_length=target_length,
        normalize=normalize,
        augment=augment,
        augmentation_factor=3
    )
    
    X, y, y_original = preprocessor.fit_transform(features, labels)

    print("\n" + "=" * 70)
    print("PERFORMING TRAIN TEST SPLIT")
    print("=" * 70)

    X_train, X_test, y_train, y_test, y_train_orig, y_test_orig = train_test_split(
        X, y, y_original,
        test_size=test_split,
        stratify=y_original,
        random_state=random_state
    )

    print(f'Training samples: {len(X_train)}')
    print(f'Test samples: {len(X_test)}')

    print("\n" + "=" * 70)
    print("DEEPCONVLSTM TRAINING WITH K-FOLD CROSS VALIDATION")
    print("=" * 70)

    model = train(X_train, y_train, y_train_orig, n_splits, epochs, batch_size, learning_rate, random_state)

    model.plot_training_history()
    
    model.evaluate(X_test, y_test, y_train_orig)
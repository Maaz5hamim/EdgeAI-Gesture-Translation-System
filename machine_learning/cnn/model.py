import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow import keras
from tensorflow.keras import layers, models, callbacks
import warnings
from constant import GESTURE_NAMES
warnings.filterwarnings('ignore')

class DeepConvLSTM:
    """
    DeepConvLSTM architecture from Ordóñez and Roggen (2016)
    
    Architecture:
    - 4 Convolutional layers (64 filters, kernel=5)
    - 2 LSTM layers (128 units each)
    - Dropout for regularization
    - Softmax classification
    """
    
    def __init__(self, window_size=100, n_features=6, n_classes=8,
                 conv_filters=32, conv_kernel=3, lstm_units=32,
                 dropout_rate=0.5, output_dir='best_deepconvlstm_model.h5'):
        """
        Args:
            window_size: Input sequence length
            n_features: Number of sensor channels
            n_classes: Number of gesture classes
            conv_filters: Number of filters in conv layers 
            conv_kernel: Kernel size for conv layers 
            lstm_units: Number of LSTM units 
            dropout_rate: Dropout probability 
        """
        self.window_size = window_size
        self.n_features = n_features
        self.n_classes = n_classes
        self.conv_filters = conv_filters
        self.conv_kernel = conv_kernel
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.output_dir = output_dir
        
        self.model = None
        self.history = None
    
    def build_model(self):
        """
        Build DeepConvLSTM model according to paper specifications
        """
        print("Building DeepConvLSTM model")
        
        model = models.Sequential(name='DeepConvLSTM')
        
        # Input layer
        model.add(layers.Input(shape=(self.window_size, self.n_features), 
                              name='input'))
        
        # # Convolutional layers 
        for i in range(2):
            model.add(layers.Conv1D(
                filters=self.conv_filters,
                kernel_size=self.conv_kernel,
                activation='relu',
                padding='same',
                name=f'conv1d_{i+1}'
            ))
            model.add(layers.BatchNormalization(epsilon=1e-3)) 

        model.add(layers.Conv1D(filters=32, kernel_size=3, padding='same', dilation_rate=4, activation='relu'))
        model.add(layers.BatchNormalization())

        model.add(layers.GlobalMaxPooling1D(name='max_pool'))

        # Output layer
        model.add(layers.Dense(
            units=self.n_classes,
            activation='softmax',
            name='output'
        ))
        
        # # LSTM layers
        # model.add(layers.LSTM(
        #     units=self.lstm_units,
        #     return_sequences=True,
        #     unroll=True,
        #     name='lstm_1'
        # ))

        # model.add(layers.Dropout(self.dropout_rate, name='dropout_1'))
        
        # model.add(layers.GRU(
        #     units=self.lstm_units,
        #     return_sequences=False,
        #     unroll=True,
        #     name='lstm_2'
        # ))
        # model.add(layers.Dropout(self.dropout_rate, name='dropout_2'))
        
        self.model = model
        
        return model
    
    def compile_model(self, learning_rate=0.001):
        """
        Compile model with optimizer and loss
        """
        if self.model is None:
            self.build_model()
        
        optimizer = keras.optimizers.RMSprop(learning_rate=learning_rate)
        
        self.model.compile(
            optimizer=optimizer,
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        print("\nModel compiled successfully!")
        
        return self.model
    
    def get_model_summary(self):
        """Print model architecture"""
        if self.model is None:
            print("Model not built yet!")
            return
        
        print("\n" + "=" * 70)
        print("MODEL ARCHITECTURE SUMMARY")
        print("=" * 70)
        self.model.summary()
        
        # Calculate parameters
        trainable = np.sum([np.prod(v.shape) for v in self.model.trainable_weights])
        non_trainable = np.sum([np.prod(v.shape) for v in self.model.non_trainable_weights])
        
        print(f"\nTotal parameters: {trainable + non_trainable:,}")
        print(f"Trainable parameters: {trainable:,}")
        print(f"Non-trainable parameters: {non_trainable:,}")
    
    def train(self, X_train, y_train, X_val, y_val, 
              epochs=100, batch_size=32, verbose=1):
        """
        Train the model
        """
        if self.model is None:
            print("Building and compiling model...")
            self.compile_model()
        
        # Callbacks
        callback_list = [
            callbacks.EarlyStopping(
                monitor='val_loss',
                patience=20,
                restore_best_weights=True,
                verbose=0
            ),
            callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=10,
                min_lr=1e-7,
                verbose=1
            ),
            callbacks.ModelCheckpoint(
                filepath=self.output_dir,
                monitor='val_accuracy',
                save_best_only=True,
                verbose=0
            )
        ]
        
        # Train
        self.history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callback_list,
            verbose=verbose
        )
        
        return self.history
    
    def plot_training_history(self, save_path='visualization/training_history.png'):
        """Plot training history"""
        if self.history is None:
            print("No training history available!")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        # Accuracy plot
        axes[0].plot(self.history.history['accuracy'], label='Train Accuracy', linewidth=2)
        axes[0].plot(self.history.history['val_accuracy'], label='Val Accuracy', linewidth=2)
        axes[0].set_title('Model Accuracy', fontsize=14, fontweight='bold')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Accuracy')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Loss plot
        axes[1].plot(self.history.history['loss'], label='Train Loss', linewidth=2)
        axes[1].plot(self.history.history['val_loss'], label='Val Loss', linewidth=2)
        axes[1].set_title('Model Loss', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Loss')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        print(f"Training history plot saved as '{save_path}'")
    
    def evaluate(self, X_test, y_test, y_test_labels=None):
        """
        Evaluate model on test set
        """
        print("\n" + "=" * 70)
        print("MODEL EVALUATION")
        print("=" * 70)
        
        # Get predictions
        y_pred_probs = self.model.predict(X_test, verbose=0)
        y_pred = np.argmax(y_pred_probs, axis=1)
        y_true = np.argmax(y_test, axis=1)
        
        # Calculate metrics
        test_loss, test_accuracy = self.model.evaluate(X_test, y_test, verbose=0)
        
        print(f"\nTest Loss: {test_loss:.4f}")
        print(f"Test Accuracy: {test_accuracy * 100:.2f}%")
        
        # Classification report
        print("\n" + "-" * 70)
        print("CLASSIFICATION REPORT")
        print("-" * 70)
        print(classification_report(y_true, y_pred, target_names=GESTURE_NAMES, digits=4))
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=GESTURE_NAMES, yticklabels=GESTURE_NAMES,
                   cbar_kws={'label': 'Count'})
        plt.title('Confusion Matrix', fontsize=14, fontweight='bold', pad=20)
        plt.ylabel('True Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        plt.tight_layout()
        plt.savefig('visualization/confusion_matrix.png', dpi=300, bbox_inches='tight')
        
        print("Confusion matrix saved as 'confusion_matrix.png'")
        
        return test_accuracy, y_pred
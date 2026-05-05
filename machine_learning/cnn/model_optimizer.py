import subprocess
import numpy as np
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow import keras
import os
from pathlib import Path
from machine_learning.cnn.train import load_data
from preprocess import Preprocess
import time

class ModelConverter:
    """
    Convert and optimize Keras model to TensorFlow Lite
    """
    
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.tflite_model = None
        self.quantized_model = None
        
    def load_model(self):
        self.model = keras.models.load_model(self.model_path)
        
        print(f"\n✓ Model loaded from: {self.model_path}")
        self.model.summary()
        
        return self.model

    def convert_to_tflite_float32(self, output_path='model_float32.tflite'):
        """
        Convert to TensorFlow Lite (float32)
        """
        print("\n" + "=" * 70)
        print("CONVERTING TO TENSORFLOW LITE (FLOAT32)")
        print("=" * 70)
        
        if self.model is None:
            self.load_model()
        
        # Create TFLite converter
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        
        # Optimizations
        converter.optimizations = [] #[tf.lite.Optimize.DEFAULT]
        # converter.exclude_conversion_metadata = True
        converter.target_spec.supported_types = [tf.float32]
        # Convert
        self.tflite_model = converter.convert()
        
        # Save
        with open(output_path, 'wb') as f:
            f.write(self.tflite_model)
        
        return self.tflite_model
    
    def convert_to_tflite_int8(self, X_train, output_path='model_quantized_int8.tflite'):
        """
        Convert to TensorFlow Lite with INT8 quantization
        """
        print("\n" + "=" * 70)
        print("CONVERTING TO TENSORFLOW LITE (INT8 QUANTIZED)")
        print("=" * 70)
        
        if self.model is None:
            self.load_model()
        
        # Create converter
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        
        # Enable INT8 quantization
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        # converter.exclude_conversion_metadata = True
        
        # Representative dataset generator for calibration
        def representative_dataset():
            # Use a subset of training data for calibration
            num_calibration_samples = min(100, len(X_train))
            for i in range(num_calibration_samples):
                # Expand dims to add batch dimension
                sample = np.expand_dims(X_train[i], axis=0).astype(np.float32)
                yield [sample]
        
        converter.representative_dataset = representative_dataset
        
        # Set input/output to INT8
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.int8
        converter.inference_output_type = tf.int8
        
        # Convert
        self.quantized_model = converter.convert()
        
        # Save
        with open(output_path, 'wb') as f:
            f.write(self.quantized_model)
        
        return self.quantized_model
    
    def convert_to_tflite_float16(self, output_path='model_float16.tflite'):
        """
        Convert to TensorFlow Lite (Float16)
        """
        print("\n" + "=" * 70)
        print("CONVERTING TO TENSORFLOW LITE (FLOAT16)")
        print("=" * 70)
        
        if self.model is None:
            self.load_model()
        
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        converter.optimizations = [] #[tf.lite.Optimize.DEFAULT]
        # converter.exclude_conversion_metadata = True
        converter.target_spec.supported_types = [tf.float16]
        
        tflite_model_float16 = converter.convert()
        
        with open(output_path, 'wb') as f:
            f.write(tflite_model_float16)
        
        return tflite_model_float16
    
    def benchmark_tflite_model(self, tflite_model_path, X_test, y_test, model_type='float32'):
        interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
        interpreter.allocate_tensors()
        
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        # --- FIX 1: SAFE QUANTIZATION PARAMETER ACCESS ---
        input_quant = input_details[0].get('quantization_parameters', {})
        input_scales = input_quant.get('scales', [])
        input_zero_points = input_quant.get('zero_points', [])
        
        input_scale = input_scales[0] if len(input_scales) > 0 else None
        input_zero_point = input_zero_points[0] if len(input_zero_points) > 0 else 0

        output_quant = output_details[0].get('quantization_parameters', {})
        output_scales = output_quant.get('scales', [])
        output_zero_points = output_quant.get('zero_points', [])
        
        output_scale = output_scales[0] if len(output_scales) > 0 else None
        output_zero_point = output_zero_points[0] if len(output_zero_points) > 0 else 0
        
        predictions = []
        inference_times = []
        
        for i, x in enumerate(X_test):
            # --- FIX 2: ROBUST INPUT PREPARATION ---
            input_data = np.expand_dims(x, axis=0)
            
            if input_details[0]['dtype'] == np.int8 and input_scale is not None:
                # Manual quantization for the benchmark
                input_data = (input_data / input_scale + input_zero_point)
                input_data = np.clip(input_data, -128, 127).astype(np.int8)
            else:
                input_data = input_data.astype(np.float32)
            
            interpreter.set_tensor(input_details[0]['index'], input_data)
            
            start = time.time()
            interpreter.invoke()
            inference_times.append((time.time() - start) * 1000)
            
            output_data = interpreter.get_tensor(output_details[0]['index'])
            
            # --- FIX 3: ROBUST OUTPUT DEQUANTIZATION ---
            if output_details[0]['dtype'] == np.int8 and output_scale is not None:
                output_data = (output_data.astype(np.float32) - output_zero_point) * output_scale
            
            predictions.append(np.argmax(output_data[0]))
        
        # Accuracy calculation (handling both One-Hot and Integer labels)
        if len(y_test.shape) > 1:
            y_true = np.argmax(y_test, axis=1)
        else:
            y_true = y_test
            
        accuracy = np.mean(y_true == np.array(predictions))
        
        return {
            'accuracy': accuracy,
            'mean_inference_time_ms': np.mean(inference_times)
        }
    
    def convert_to_c_array(self, tflite_model_path, output_header='model_data.h', 
                          array_name='gesture_model_data'):
        """
        Convert TFLite model to C header file for embedding
        """
        if not os.path.exists(tflite_model_path):
            print(f"Error: {tflite_model_path} not found.")
            return None

        try:
            # xxd -i generates the C include output
            # We use check_output to capture it
            result = subprocess.check_output(['xxd', '-i', tflite_model_path])
            c_content = result.decode('utf-8')

            # xxd uses the filename as the variable name by default (e.g., model_float32_tflite)
            # We can use replace to match your specific array_name if desired
            default_name = tflite_model_path.replace('.', '_').replace('/', '_').replace('\\', '_')
            c_content = c_content.replace(default_name, array_name)

            # Add the alignment attribute for nRF54 (Cortex-M)
            # We insert it right before the 'const unsigned char'
            alignment_prefix = "#ifdef __GNUC__\n#define ALIGN_ATTRIBUTE __attribute__((aligned(8)))\n#else\n#define ALIGN_ATTRIBUTE alignas(8)\n#endif\n\nALIGN_ATTRIBUTE "
            final_output = f"#ifndef {array_name.upper()}_H\n#define {array_name.upper()}_H\n\n#include <stdint.h>\n\n{alignment_prefix}{c_content}\n#endif"

            with open(output_header, 'w') as f:
                f.write(final_output)

            model_size = os.path.getsize(tflite_model_path)
            print(f"✓ C header generated: {output_header} ({model_size} bytes)")
            
        except subprocess.CalledProcessError as e:
            print(f"Error running xxd: {e}")
        except FileNotFoundError:
            print("Error: 'xxd' command not found. Please ensure it is installed in your system PATH.")

        return output_header
    
    def generate_comparison_report(self, models_info):
        """
        Generate comparison report of different model formats
        """
        print("\n" + "=" * 70)
        print("MODEL COMPARISON REPORT")
        print("=" * 70)
        
        print(f"\n{'Model Type':<25} {'Size (KB)':<15} {'Accuracy (%)':<15} {'Inference (ms)':<15}")
        print("-" * 70)
        
        for model_info in models_info:
            print(f"{model_info['name']:<25} "
                  f"{model_info['size_kb']:<15.2f} "
                  f"{model_info.get('accuracy', 0)*100:<15.2f} "
                  f"{model_info.get('inference_time_ms', 0):<15.2f}")

if __name__ == "__main__":
    DATA_DIR = '/dataset/gesture_dataset_consolidated.npz'
    MODEL_PATH = 'best_model.h5'

    # Preprocessing parameters
    target_length = 100
    normalize = True
    augment = False
    augmentation_factor = 3

    print("\n" + "=" * 70)
    print("LOADING DATA")
    print("=" * 70)

    features, labels = load_data(DATA_DIR)

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
        test_size=0.2,
        stratify=y_original,
        random_state=42
    )

    # X_test = X_test[:, 30:70, :]
    
    print(f'Training samples: {len(X_train)}')
    print(f'Test samples: {len(X_test)}')

    print("\n" + "=" * 70)
    print("OPTIMIZING MODEL")
    print("=" * 70)

    
    
    converter = ModelConverter(MODEL_PATH)
    converter.load_model()
    
    models_info = []
    
    # Original Keras model size
    keras_size = Path(MODEL_PATH).stat().st_size / 1024
    models_info.append({
        'name': 'Original Keras (HDF5)',
        'size_kb': keras_size,
        'path': MODEL_PATH
    })

    conversions = ['float32', 'float16', 'int8']

    for i in range(len(conversions)):
        model_path = os.path.join('models_lite', f'model_{conversions[i]}.tflite')
        func = getattr(converter, f'convert_to_tflite_{conversions[i]}')
        if conversions[i] == 'int8':
            func(X_test, model_path)
        else:
            func(model_path)
        model_size = Path(model_path).stat().st_size / 1024
        benchmark_results = converter.benchmark_tflite_model(model_path, X_test, y_test, 'float32')
        models_info.append({
            'name': f'TFLite ({conversions[i]})',
            'size_kb': model_size,
            'accuracy': benchmark_results['accuracy'],
            'inference_time_ms': benchmark_results['mean_inference_time_ms'],
            'path': model_path
        })
        converter.convert_to_c_array(model_path, os.path.join('models_c_headers', f'model_{conversions[i]}.h'), 'gesture_model_data')
    
    converter.generate_comparison_report(models_info)
/**
 * gesture_inference.c
 * Enhanced implementation with better error handling
 */

#include "gesture_inference.h"
#include "gesture_model.h"

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include <zephyr/logging/log.h>
LOG_MODULE_REGISTER(gesture_inference, LOG_LEVEL_INF);

// TFLite globals
static const tflite::Model* model = nullptr;
static tflite::MicroInterpreter* interpreter = nullptr;
static TfLiteTensor* input_tensor = nullptr;
static TfLiteTensor* output_tensor = nullptr;

// Tensor arena - adjust based on your model's needs
constexpr int kTensorArenaSize = 60 * 1024;  // 60 KB
alignas(16) static uint8_t tensor_arena[kTensorArenaSize];

// Gesture names
static const char* gesture_names[] = {
    "SLIDE_UP",
    "SLIDE_DOWN",
    "SLIDE_LEFT",
    "SLIDE_RIGHT",
    "UNKNOWN"
};

// Input shape expected by model
static int input_window_size = 0;
static int input_features = 0;

/**
 * Initialize gesture recognition system
 */
bool gesture_init(void)
{
    LOG_INF("═════════════════════════════════════════");
    LOG_INF("  Initializing TensorFlow Lite Micro");
    LOG_INF("═════════════════════════════════════════");
    
    // Initialize TFLite runtime
    tflite::InitializeTarget();
    
    // Load model from flash
    model = tflite::GetModel(gesture_model);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        LOG_ERR("❌ Model schema version mismatch!");
        LOG_ERR("   Model version: %d", model->version());
        LOG_ERR("   Expected version: %d", TFLITE_SCHEMA_VERSION);
        return false;
    }
    
    LOG_INF("✓ Model loaded successfully");
    LOG_INF("  Size: %u bytes (%.2f KB)", gesture_model_len, 
           gesture_model_len / 1024.0f);
    
    // Create operation resolver
    static tflite::MicroMutableOpResolver<12> resolver;
    
    // Add operations used by DeepConvGRU model
    resolver.AddConv2D();
    resolver.AddReshape();
    resolver.AddFullyConnected();
    resolver.AddSoftmax();
    resolver.AddQuantize();
    resolver.AddDequantize();
    
    // GRU operations
    resolver.AddUnidirectionalSequenceGRU();
    resolver.AddUnidirectionalSequenceLSTM();  // Sometimes needed
    
    // Additional ops
    resolver.AddMean();
    resolver.AddPad();
    resolver.AddMul();
    resolver.AddAdd();
    
    LOG_INF("✓ Op resolver configured");
    
    // Build interpreter
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;
    
    // Allocate tensors
    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {
        LOG_ERR("❌ AllocateTensors() failed!");
        return false;
    }
    
    LOG_INF("✓ Tensors allocated");
    
    // Get input tensor
    input_tensor = interpreter->input(0);
    if (!input_tensor) {
        LOG_ERR("❌ Failed to get input tensor");
        return false;
    }
    
    // Get output tensor
    output_tensor = interpreter->output(0);
    if (!output_tensor) {
        LOG_ERR("❌ Failed to get output tensor");
        return false;
    }
    
    // Log input tensor details
    LOG_INF("─────────────────────────────────────────");
    LOG_INF("Input Tensor:");
    LOG_INF("  Dimensions: %d", input_tensor->dims->size);
    
    if (input_tensor->dims->size == 3) {
        LOG_INF("  Shape: [%d, %d, %d]",
               input_tensor->dims->data[0],  // batch
               input_tensor->dims->data[1],  // window_size
               input_tensor->dims->data[2]); // features
        
        input_window_size = input_tensor->dims->data[1];
        input_features = input_tensor->dims->data[2];
    }
    
    LOG_INF("  Type: %s", 
           input_tensor->type == kTfLiteFloat32 ? "Float32" :
           input_tensor->type == kTfLiteInt8 ? "Int8" : "Unknown");
    LOG_INF("  Bytes: %d", input_tensor->bytes);
    
    // Log output tensor details
    LOG_INF("─────────────────────────────────────────");
    LOG_INF("Output Tensor:");
    LOG_INF("  Dimensions: %d", output_tensor->dims->size);
    LOG_INF("  Classes: %d", output_tensor->dims->data[1]);
    LOG_INF("  Type: %s",
           output_tensor->type == kTfLiteFloat32 ? "Float32" :
           output_tensor->type == kTfLiteInt8 ? "Int8" : "Unknown");
    
    // Log memory usage
    LOG_INF("─────────────────────────────────────────");
    LOG_INF("Memory Usage:");
    LOG_INF("  Tensor arena size: %d bytes (%.2f KB)",
           kTensorArenaSize, kTensorArenaSize / 1024.0f);
    LOG_INF("  Arena used: %d bytes (%.2f KB)",
           interpreter->arena_used_bytes(),
           interpreter->arena_used_bytes() / 1024.0f);
    LOG_INF("  Arena available: %d bytes (%.2f KB)",
           kTensorArenaSize - interpreter->arena_used_bytes(),
           (kTensorArenaSize - interpreter->arena_used_bytes()) / 1024.0f);
    
    LOG_INF("═════════════════════════════════════════");
    LOG_INF("✓ TensorFlow Lite Micro initialized!");
    LOG_INF("═════════════════════════════════════════");
    
    return true;
}

/**
 * Run inference on windowed IMU data
 */
bool gesture_predict(const float *input_data, gesture_result_t *result)
{
    if (!interpreter || !input_tensor || !output_tensor) {
        LOG_ERR("❌ Interpreter not initialized!");
        return false;
    }
    
    // Calculate input size
    int input_size = input_window_size * input_features;
    
    // Copy input data to tensor
    if (input_tensor->type == kTfLiteFloat32) {
        // Float32 input
        memcpy(input_tensor->data.f, input_data, input_size * sizeof(float));
    } else if (input_tensor->type == kTfLiteInt8) {
        // Int8 quantized input
        float scale = input_tensor->params.scale;
        int32_t zero_point = input_tensor->params.zero_point;
        
        for (int i = 0; i < input_size; i++) {
            int32_t quantized = (int32_t)(input_data[i] / scale + zero_point);
            quantized = MAX(-128, MIN(127, quantized));
            input_tensor->data.int8[i] = (int8_t)quantized;
        }
    }
    
    // Run inference
    TfLiteStatus invoke_status = interpreter->Invoke();
    if (invoke_status != kTfLiteOk) {
        LOG_ERR("❌ Invoke() failed!");
        return false;
    }
    
    // Process output
    float max_prob = 0.0f;
    int max_index = 0;
    
    for (int i = 0; i < 4; i++) {
        if (output_tensor->type == kTfLiteFloat32) {
            result->probabilities[i] = output_tensor->data.f[i];
        } else if (output_tensor->type == kTfLiteInt8) {
            // Dequantize output
            float scale = output_tensor->params.scale;
            int32_t zero_point = output_tensor->params.zero_point;
            result->probabilities[i] = 
                (output_tensor->data.int8[i] - zero_point) * scale;
        }
        
        if (result->probabilities[i] > max_prob) {
            max_prob = result->probabilities[i];
            max_index = i;
        }
    }
    
    // Set result
    result->gesture = (gesture_type_t)max_index;
    result->confidence = max_prob;
    
    return true;
}

/**
 * Get gesture name string
 */
const char* gesture_get_name(gesture_type_t gesture)
{
    if (gesture >= 0 && gesture <= 4) {
        return gesture_names[gesture];
    }
    return "INVALID";
}
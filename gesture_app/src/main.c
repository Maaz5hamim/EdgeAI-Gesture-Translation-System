/**
 * main.c
 * Gesture recognition with windowing and inference
 */

#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "imu.h"
#include "gesture_inference.h"

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

extern struct k_msgq imu_msgq;

// Window configuration (must match training)
#define WINDOW_SIZE 128
#define NUM_FEATURES 6
#define STRIDE 64  // Slide window by 64 samples (50% overlap)

// Sliding window buffer
static float window_buffer[WINDOW_SIZE][NUM_FEATURES];
static int window_index = 0;
static bool window_ready = false;

// Statistics for normalization (calculate from your training data)
// These should match the normalization used during training
#define ACCEL_MEAN_X 0.0f
#define ACCEL_MEAN_Y 0.0f
#define ACCEL_MEAN_Z 1000.0f  // ~1g in mg
#define GYRO_MEAN_X 0.0f
#define GYRO_MEAN_Y 0.0f
#define GYRO_MEAN_Z 0.0f

#define ACCEL_STD_X 500.0f
#define ACCEL_STD_Y 500.0f
#define ACCEL_STD_Z 500.0f
#define GYRO_STD_X 100.0f
#define GYRO_STD_Y 100.0f
#define GYRO_STD_Z 100.0f

/**
 * Normalize sensor data
 */
static inline float normalize(float value, float mean, float std)
{
    return (value - mean) / std;
}

/**
 * Add IMU sample to window buffer
 */
static void add_to_window(struct imu_sample *sample)
{
    // Normalize and add to window
    window_buffer[window_index][0] = normalize(sample->accel_x, ACCEL_MEAN_X, ACCEL_STD_X);
    window_buffer[window_index][1] = normalize(sample->accel_y, ACCEL_MEAN_Y, ACCEL_STD_Y);
    window_buffer[window_index][2] = normalize(sample->accel_z, ACCEL_MEAN_Z, ACCEL_STD_Z);
    window_buffer[window_index][3] = normalize(sample->gyro_x, GYRO_MEAN_X, GYRO_STD_X);
    window_buffer[window_index][4] = normalize(sample->gyro_y, GYRO_MEAN_Y, GYRO_STD_Y);
    window_buffer[window_index][5] = normalize(sample->gyro_z, GYRO_MEAN_Z, GYRO_STD_Z);
    
    window_index++;
    
    // Check if window is full
    if (window_index >= WINDOW_SIZE) {
        window_ready = true;
        window_index = 0;  // Reset for next window
    }
}

/**
 * Prepare flattened input for inference
 */
static void prepare_input(float *input_array)
{
    // Flatten window buffer: [128, 6] -> [768]
    for (int i = 0; i < WINDOW_SIZE; i++) {
        for (int j = 0; j < NUM_FEATURES; j++) {
            input_array[i * NUM_FEATURES + j] = window_buffer[i][j];
        }
    }
}

/**
 * Print gesture result
 */
static void print_result(gesture_result_t *result)
{
    LOG_INF("┌─────────────────────────────────────┐");
    LOG_INF("│ GESTURE: %-25s│", gesture_get_name(result->gesture));
    LOG_INF("│ CONFIDENCE: %.1f%%                  │", result->confidence * 100.0f);
    LOG_INF("├─────────────────────────────────────┤");
    LOG_INF("│ Probabilities:                      │");
    LOG_INF("│   SLIDE_UP:    %.1f%%", result->probabilities[0] * 100.0f);
    LOG_INF("│   SLIDE_DOWN:  %.1f%%", result->probabilities[1] * 100.0f);
    LOG_INF("│   SLIDE_LEFT:  %.1f%%", result->probabilities[2] * 100.0f);
    LOG_INF("│   SLIDE_RIGHT: %.1f%%", result->probabilities[3] * 100.0f);
    LOG_INF("└─────────────────────────────────────┘");
}

/**
 * Main thread
 */
int main(void)
{
    LOG_INF("═════════════════════════════════════════");
    LOG_INF("  Gesture Recognition System - nRF54L15");
    LOG_INF("═════════════════════════════════════════");
    
    // Start IMU
    if (imu_start() != 0) {
        LOG_ERR("Failed to start IMU");
        return -1;
    }
    LOG_INF("✓ IMU started");
    
    // Initialize TensorFlow Lite
    if (!gesture_init()) {
        LOG_ERR("Failed to initialize gesture recognition");
        return -1;
    }
    LOG_INF("✓ TFLite initialized");
    
    LOG_INF("\n🎯 Ready for gesture recognition!");
    LOG_INF("   Window size: %d samples", WINDOW_SIZE);
    LOG_INF("   Collecting data...\n");
    
    struct imu_sample sample;
    gesture_result_t result;
    float input_data[WINDOW_SIZE * NUM_FEATURES];
    
    uint32_t sample_count = 0;
    uint32_t inference_count = 0;
    
    while (1) {
        // Get IMU sample from message queue
        k_msgq_get(&imu_msgq, &sample, K_FOREVER);
        sample_count++;
        
        // Add to window
        add_to_window(&sample);
        
        // Log raw data periodically
        if (sample_count % 104 == 0) {
            LOG_DBG("Sample #%u: accel[%d,%d,%d] gyro[%d,%d,%d]",
                   sample_count,
                   sample.accel_x, sample.accel_y, sample.accel_z,
                   sample.gyro_x, sample.gyro_y, sample.gyro_z);
        }
        
        // Run inference when window is ready
        if (window_ready) {
            LOG_INF("─────────────────────────────────────────");
            LOG_INF("Running inference #%u...", ++inference_count);
            
            // Prepare input
            prepare_input(input_data);
            
            // Run inference
            int64_t start_time = k_uptime_get();
            
            if (gesture_predict(input_data, &result)) {
                int64_t inference_time = k_uptime_delta(&start_time);
                
                // Print result
                print_result(&result);
                LOG_INF("⏱️  Inference time: %lld ms", inference_time);
                
                // Optional: Only show high confidence predictions
                if (result.confidence > 0.7f) {
                    LOG_WRN("🎯 HIGH CONFIDENCE DETECTION!");
                }
            } else {
                LOG_ERR("❌ Inference failed");
            }
            
            window_ready = false;
            
            // Optional: Add delay between inferences
            // k_sleep(K_MSEC(100));
        }
    }
    
    return 0;
}
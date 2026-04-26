/**
 * gesture_inference.h
 * TensorFlow Lite Micro inference for nRF54L15
 */

#ifndef GESTURE_INFERENCE_H
#define GESTURE_INFERENCE_H

#include <stdint.h>
#include <stdbool.h>

// Gesture classes
typedef enum {
    GESTURE_SLIDE_UP = 0,
    GESTURE_SLIDE_DOWN = 1,
    GESTURE_SLIDE_LEFT = 2,
    GESTURE_SLIDE_RIGHT = 3,
    GESTURE_UNKNOWN = 4
} gesture_type_t;

// Gesture result
typedef struct {
    gesture_type_t gesture;
    float confidence;
    float probabilities[4];
} gesture_result_t;

// Initialize TFLite interpreter
bool gesture_init(void);

// Run inference on IMU data
// input_data: float array of shape [window_size, 6] - flattened
// window_size: typically 128
bool gesture_predict(const float *input_data, gesture_result_t *result);

// Get gesture name
const char* gesture_get_name(gesture_type_t gesture);

#endif
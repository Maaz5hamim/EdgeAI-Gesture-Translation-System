#ifndef CONSTANTS_H_
#define CONSTANTS_H_

/* The number of time-steps in one "clip" (the window length) */
constexpr int kWindowSize = 100;

/* The number of sensor features (3 Accel + 3 Gyro) */
constexpr int kFeatureCount = 6;

/* Total length of the flattened input tensor (100 * 6 = 768) */
constexpr int kMaxInputLength = kWindowSize * kFeatureCount;

/* The expected IMU sample frequency in Hz */
const float kTargetHz = 104.0f;

const int kMotionThreshold = 32;
const int kMotionDuration = 1;

/* Gesture classification settings */
constexpr int kGestureCount = 8;
/* What gestures are supported. */
inline const char* kGestureNames[] = {
    "UP", 
    "DOWN", 
    "LEFT", 
    "RIGHT", 
    "TAP", 
    "DOUBLE_TAP", 
    "STATIC", 
    "NONE"
};
constexpr int kSlideUp = 0;
constexpr int kSlideDown = 1;
constexpr int kSlideLeft = 2;
constexpr int kSlideRight = 3;

constexpr float kDetectionThreshold = 0.6f;



#endif /* CONSTANTS_H_ */

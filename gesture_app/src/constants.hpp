#ifndef CONSTANTS_H_
#define CONSTANTS_H_

/** Training data statistics:
Accelerometer: m/s² 
Gyroscope: rad/s 
*/

// Mean values
#define ACCEL_X_MEAN -2.545875f
#define ACCEL_Y_MEAN 6.037923f
#define ACCEL_Z_MEAN 0.781317f
#define GYRO_X_MEAN 0.061443f
#define GYRO_Y_MEAN -0.103846f
#define GYRO_Z_MEAN 0.003154f

// Standard deviation values 
#define ACCEL_X_STD 5.859293f
#define ACCEL_Y_STD 3.801762f
#define ACCEL_Z_STD 4.831740f
#define GYRO_X_STD 0.718018f
#define GYRO_Y_STD 1.324086f
#define GYRO_Z_STD 0.492886f

/* The number of time-steps in one "clip" (the window length) */
constexpr int kWindowSize = 40;

/* The number of sensor features (3 Accel + 3 Gyro) */
constexpr int kFeatureCount = 6;

/* Total length of the flattened input tensor (128 * 6 = 768) */
constexpr int kMaxInputLength = kWindowSize * kFeatureCount;

/* The expected IMU sample frequency in Hz */
const float kTargetHz = 52.0f;

/* Gesture classification settings */
constexpr int kGestureCount = 4;
/* What gestures are supported. */
constexpr int kSlideUp = 0;
constexpr int kSlideDown = 1;
constexpr int kSlideLeft = 2;
constexpr int kSlideRight = 3;

constexpr float kDetectionThreshold = 0.6f;
constexpr int kPredictionHistoryLength = 5;
constexpr int kPredictionSuppressionDuration = 25;



#endif /* CONSTANTS_H_ */

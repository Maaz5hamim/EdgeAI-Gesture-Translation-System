#ifndef IMU_HANDLER_H_
#define IMU_HANDLER_H_

#include <tensorflow/lite/c/c_api_types.h>
#include <tensorflow/lite/micro/micro_log.h>

extern int begin_index;
extern struct k_sem gesture_trigger_sem;

extern void MotionInterruptHandler(const struct device *dev, struct gpio_callback *cb, uint32_t pins);
extern int ConfigureMotionThreshold(uint8_t threshold, uint8_t duration);
extern bool SetupIMU();
extern bool ReadIMU(float *input, int length);
extern void StreamIMUData();
extern void CaptureSample();
extern void PrepareInputTensor(float *input);

#endif /* IMU_HANDLER_H_ */

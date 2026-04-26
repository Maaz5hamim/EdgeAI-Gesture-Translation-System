#ifndef IMU_HANDLER_H_
#define IMU_HANDLER_H_

#include <tensorflow/lite/c/c_api_types.h>
#include <tensorflow/lite/micro/micro_log.h>

extern int begin_index;
extern TfLiteStatus SetupIMU();
extern bool ReadIMU(float *input, int length);

#endif /* IMU_HANDLER_H_ */

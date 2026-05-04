#ifndef MAIN_FUNCTIONS_H_
#define MAIN_FUNCTIONS_H_

#include <tensorflow/lite/micro/micro_interpreter.h>

/*  Expose a C friendly interface for main functions.*/
#ifdef __cplusplus
extern "C" {
#endif

/* Initializes imu and the model. */
TfLiteStatus setup(void);

/* Runs one iteration of data gathering and inference. This should be called repeatedly from the application code. */
void loop(void);

#ifdef __cplusplus
}
#endif

#endif /* MAIN_FUNCTIONS_H_ */

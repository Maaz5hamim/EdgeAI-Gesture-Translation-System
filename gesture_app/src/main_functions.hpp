#ifndef MAIN_FUNCTIONS_H_
#define MAIN_FUNCTIONS_H_

/*  Expose a C friendly interface for main functions.*/
#ifdef __cplusplus
extern "C" {
#endif

/* Prints data in serial terminal for edge-impulse to collect */
void collect_data(float *input_buffer);

/* Initializes all data needed for the example. */
void setup(void);

/* Runs one iteration of data gathering and inference. This should be called repeatedly from the application code. */
void loop(void);

#ifdef __cplusplus
}
#endif

#endif /* MAIN_FUNCTIONS_H_ */

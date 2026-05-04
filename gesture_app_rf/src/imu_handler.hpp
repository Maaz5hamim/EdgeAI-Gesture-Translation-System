#ifndef IMU_HANDLER_H_
#define IMU_HANDLER_H_

extern int begin_index;
extern struct k_sem gesture_trigger_sem;

extern bool SetupIMU();
extern void PrepareModelInput(double *input);
extern void StreamIMUData();

#endif /* IMU_HANDLER_H_ */

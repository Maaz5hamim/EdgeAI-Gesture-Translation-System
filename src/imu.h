#ifndef IMU_H
#define IMU_H

#include <stdint.h>

/* One IMU sample: accel XYZ in mg, gyro XYZ in mdps */
struct imu_sample {
	int16_t accel_x;
	int16_t accel_y;
	int16_t accel_z;
	int16_t gyro_x;
	int16_t gyro_y;
	int16_t gyro_z;
};

int imu_start(void);

#endif /* IMU_H */

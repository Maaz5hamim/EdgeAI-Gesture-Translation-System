#include "imu_handler.hpp"
#include "constants.hpp"
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>
#include <math.h>
#include <zephyr/logging/log.h>
#include <stdio.h>
#include <string.h>


LOG_MODULE_REGISTER(imu_handler, LOG_LEVEL_ERR);

#define GRAVITY_MS2 9.80665f          // Standard gravity (m/s²)
#define DEG_TO_RAD (M_PI / 180.0f)    // Degrees to radians
#define MILLI_TO_UNIT 1000.0f         // Milli prefix conversion
#define BUFLEN 300

int begin_index = 0;
const struct device *const sensor = DEVICE_DT_GET_ONE(st_lsm6ds3);
int current_index = 0;

float buf_accel_x[BUFLEN] = { 0.0f };
float buf_accel_y[BUFLEN] = { 0.0f };
float buf_accel_z[BUFLEN] = { 0.0f };
float buf_gyro_x[BUFLEN] = { 0.0f };
float buf_gyro_y[BUFLEN] = { 0.0f };
float buf_gyro_z[BUFLEN] = { 0.0f };

bool initial = true;

/*Normalize a value using Z-score normalization*/
static inline float normalize_value(float value, float mean, float std) {
    // return (value - mean) / std;
	return value;
}

TfLiteStatus SetupIMU()
{
	struct sensor_value odr;
	odr.val1 = (int32_t)kTargetHz; 
	odr.val2 = 0;

	if (!device_is_ready(sensor)) {
		LOG_ERR("%s: device not ready.\n", sensor->name);
		return kTfLiteApplicationError;
	}

	MicroPrintf("IMU detected, name: %s\n", sensor->name);

	// Set Accelerometer to pulse at TargetHz
	if (sensor_attr_set(sensor, SENSOR_CHAN_ACCEL_XYZ,
						SENSOR_ATTR_SAMPLING_FREQUENCY, &odr) < 0) {
		LOG_ERR("Cannot set accelerometer ODR");
		return kTfLiteApplicationError;
	}

	// Set Gyroscope to pulse at TargetHz
	if (sensor_attr_set(sensor, SENSOR_CHAN_GYRO_XYZ, 
						SENSOR_ATTR_SAMPLING_FREQUENCY, &odr) < 0) {
		LOG_ERR("Cannot set gyroscope ODR");
		return kTfLiteApplicationError;
	}	

	return kTfLiteOk;
}

bool ReadIMU(float *input, int length)
{
	struct sensor_value accel[3];
	struct sensor_value gyro[3];

	if (sensor_sample_fetch(sensor) < 0) {
		MicroPrintf("Fetch failed\n");
		return false;
	}

	// Extract data from the driver
    sensor_channel_get(sensor, SENSOR_CHAN_ACCEL_XYZ, accel);
    sensor_channel_get(sensor, SENSOR_CHAN_GYRO_XYZ, gyro);

	float accel_x = (float)sensor_value_to_double(&accel[0]);  // m/s²
	float accel_y = (float)sensor_value_to_double(&accel[1]);  // m/s²
	float accel_z = (float)sensor_value_to_double(&accel[2]);  // m/s²

	float gyro_x = (float)sensor_value_to_double(&gyro[0]);    // rad/s
	float gyro_y = (float)sensor_value_to_double(&gyro[1]);    // rad/s
	float gyro_z = (float)sensor_value_to_double(&gyro[2]);    // rad/s

	buf_accel_x[begin_index] = normalize_value(accel_x, ACCEL_X_MEAN, ACCEL_X_STD);
	buf_accel_y[begin_index] = normalize_value(accel_y, ACCEL_Y_MEAN, ACCEL_Y_STD);
	buf_accel_z[begin_index] = normalize_value(accel_z, ACCEL_Z_MEAN, ACCEL_Z_STD);

	buf_gyro_x[begin_index] = normalize_value(gyro_x, GYRO_X_MEAN, GYRO_X_STD);
	buf_gyro_y[begin_index] = normalize_value(gyro_y, GYRO_Y_MEAN, GYRO_Y_STD);
	buf_gyro_z[begin_index] = normalize_value(gyro_z, GYRO_Z_MEAN, GYRO_Z_STD);

	begin_index = (begin_index + 1) % BUFLEN;

    if (initial && begin_index >= kWindowSize) initial = false;
    if (initial) return false;

	for (int i = 0; i < kWindowSize; i++) {
			// Calculate the circular index
		int ring_index = (begin_index + i - kWindowSize + BUFLEN) % BUFLEN;
		
		int offset = i * kFeatureCount;
		input[offset + 0] = buf_accel_x[ring_index];
		input[offset + 1] = buf_accel_y[ring_index];
		input[offset + 2] = buf_accel_z[ring_index];
		input[offset + 3] = buf_gyro_x[ring_index];
		input[offset + 4] = buf_gyro_y[ring_index];
		input[offset + 5] = buf_gyro_z[ring_index];
		}
	return true;
}



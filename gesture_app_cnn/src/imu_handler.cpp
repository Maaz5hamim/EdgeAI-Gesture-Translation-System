#include "imu_handler.hpp"
#include "constants.hpp"
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>
#include <math.h>
#include <zephyr/logging/log.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/i2c.h>

LOG_MODULE_REGISTER(imu_handler, LOG_LEVEL_INF);

#define BUFLEN 300

int begin_index = 0;
const struct device *const sensor = DEVICE_DT_GET_ONE(st_lsm6ds3);

float buf_accel_x[BUFLEN] = { 0.0f };
float buf_accel_y[BUFLEN] = { 0.0f };
float buf_accel_z[BUFLEN] = { 0.0f };
float buf_gyro_x[BUFLEN] = { 0.0f };
float buf_gyro_y[BUFLEN] = { 0.0f };
float buf_gyro_z[BUFLEN] = { 0.0f };

K_SEM_DEFINE(gesture_trigger_sem, 0, 1);
const struct i2c_dt_spec i2c_bus = I2C_DT_SPEC_GET(DT_NODELABEL(lsm6ds3));
const struct gpio_dt_spec irq_pin = GPIO_DT_SPEC_GET(DT_NODELABEL(lsm6ds3), irq_gpios);

#define STACKSIZE 1024
#define PRIORITY 7

void capture_sample() {
    struct sensor_value accel[3];
    struct sensor_value gyro[3];

    sensor_sample_fetch(sensor);
    sensor_channel_get(sensor, SENSOR_CHAN_ACCEL_XYZ, accel);
    sensor_channel_get(sensor, SENSOR_CHAN_GYRO_XYZ, gyro);

    buf_accel_x[begin_index] = (float)sensor_value_to_double(&accel[0]);
    buf_accel_y[begin_index] = (float)sensor_value_to_double(&accel[1]);
    buf_accel_z[begin_index] = (float)sensor_value_to_double(&accel[2]);
	buf_gyro_x[begin_index] = (float)sensor_value_to_double(&gyro[0]);    
	buf_gyro_y[begin_index] = (float)sensor_value_to_double(&gyro[1]);    
	buf_gyro_z[begin_index] = (float)sensor_value_to_double(&gyro[2]);   
	
    begin_index = (begin_index + 1) % BUFLEN;
}

void sampling_thread_impl(void *, void *, void *) {
    while (1) {
        capture_sample();
        // 100Hz sampling
        k_msleep(10); 
    }
}

K_THREAD_DEFINE(sampling_tid, STACKSIZE, sampling_thread_impl, NULL, NULL, NULL, PRIORITY, 0, 0);

void motion_interrupt_handler(const struct device *dev, const struct sensor_trigger *trigger) {
	sensor_sample_fetch(dev);
    k_sem_give(&gesture_trigger_sem); 
}

int configure_motion_threshold(uint8_t threshold, uint8_t duration) {
	if (!device_is_ready(i2c_bus.bus)) {
        LOG_ERR("I2C bus not ready");
        return -ENODEV;
    }

    // Enable embedded functions
    uint8_t ctrl10_c[] = {0x19, 0x3C};
    i2c_write_dt(&i2c_bus, ctrl10_c, 2);
    
    // Enable interrupts with HPF
    uint8_t tap_cfg[] = {0x58, 0x90}; 
    if (i2c_write_dt(&i2c_bus, tap_cfg, 2) < 0) {
        LOG_ERR("Failed to write TAP_CFG");
        return -EIO;
    }
    
    // Set wake-up threshold
    uint8_t wu_ths[] = {0x5B, (threshold & 0x3F)};
    if (i2c_write_dt(&i2c_bus, wu_ths, 2) < 0) {
        LOG_ERR("Failed to write WAKE_UP_THS");
        return -EIO;
    }
    
    // Set wake-up duration
    uint8_t dur_val = (duration & 0x03) << 5;
    uint8_t dur_cfg[] = {0x5C, dur_val};
    if (i2c_write_dt(&i2c_bus, dur_cfg, 2) < 0) {
        LOG_ERR("Failed to write WAKE_UP_DUR");
        return -EIO;
    }
    
    // Disable data-ready interrupts on INT1
    // INT1_CTRL (0x0D): Set all bits to 0
    uint8_t int1_ctrl[] = {0x0D, 0x00};
    if (i2c_write_dt(&i2c_bus, int1_ctrl, 2) < 0) {
        LOG_ERR("Failed to write INT1_CTRL");
        return -EIO;
    }
    
    //Route ONLY wake-up interrupt to INT1
    uint8_t md1_cfg[] = {0x5E, 0x20};
    if (i2c_write_dt(&i2c_bus, md1_cfg, 2) < 0) {
        LOG_ERR("Failed to write MD1_CFG");
        return -EIO;
    }
    
    return 0;
}

bool SetupIMU()
{
	LOG_INF("IMU Setup Initialization");

	struct sensor_value odr;
	odr.val1 = (int32_t)kTargetHz; 
	odr.val2 = 0;

	if (!device_is_ready(sensor)) {
		LOG_ERR("%s: device not ready.\n", sensor->name);
		return false;
	}

	LOG_INF("IMU detected, name: %s\n", sensor->name);

	// Set Accelerometer to pulse at TargetHz
	if (sensor_attr_set(sensor, SENSOR_CHAN_ACCEL_XYZ,
						SENSOR_ATTR_SAMPLING_FREQUENCY, &odr) < 0) {
		LOG_ERR("Cannot set accelerometer ODR");
		return false;
	}

	LOG_INF("Accelerometer ODR set to %f Hz", (double)kTargetHz);

	// Set Gyroscope to pulse at TargetHz
	if (sensor_attr_set(sensor, SENSOR_CHAN_GYRO_XYZ, 
						SENSOR_ATTR_SAMPLING_FREQUENCY, &odr) < 0) {
		LOG_ERR("Cannot set gyroscope ODR");
		return false;
	}	

	LOG_INF("Gyroscope ODR set to %f Hz", (double)kTargetHz);

	struct sensor_trigger trig;
    trig.type = SENSOR_TRIG_DELTA;      // Trigger on change (motion)
    trig.chan = SENSOR_CHAN_ACCEL_XYZ; // Monitor the accelerometer

	int err;

    // Set the trigger
	err = sensor_trigger_set(sensor, &trig, motion_interrupt_handler);
    if (err < 0) {
        LOG_ERR("Could not set sensor trigger: %d", err);
		return false;
    }

	LOG_INF("IMU trigger initialized");

	// Set the imu motion threshold
	err = configure_motion_threshold(kMotionThreshold, kMotionDuration);
	if (err) {
		LOG_ERR("I2C Manual Config Failed: %d", err);
		return false;
	}

	LOG_INF("Motion threshold and duration set to %d & %d", kMotionThreshold, kMotionDuration);

	LOG_INF("IMU Setup Successful");

	return true;
}

void PrepareInputTensor(float *input) {
    for (int i = 0; i < kWindowSize; i++) {
        int ring_index = (begin_index - kWindowSize + i + BUFLEN) % BUFLEN;
        int offset = i * kFeatureCount;
        input[offset + 0] = buf_accel_x[ring_index];
		input[offset + 1] = buf_accel_y[ring_index];
		input[offset + 2] = buf_accel_z[ring_index];
		input[offset + 3] = buf_gyro_x[ring_index];
		input[offset + 4] = buf_gyro_y[ring_index];
		input[offset + 5] = buf_gyro_z[ring_index];
    }
}

void StreamIMUData() {
    double input[kWindowSize * kFeatureCount];
	printk("START_WINDOW\n"); 

	PrepareModelInput(input);

	for (int i = 0; i < kWindowSize; i++) {
		int offset = i * 6; // 6 channels (kFeatureCount)
		printk("%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n", 
			input[offset + 0], 
			input[offset + 1], 
			input[offset + 2],
			input[offset + 3], 
			input[offset + 4], 
			input[offset + 5]);

		if (i % 5 == 0) {
        	k_busy_wait(1000);
    	}
	}

	printk("END_WINDOW\n");
}

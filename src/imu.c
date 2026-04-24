#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/logging/log.h>

#include "imu.h"

LOG_MODULE_REGISTER(imu, LOG_LEVEL_INF);

#define IMU_MSGQ_DEPTH 50

static const struct device *imu_dev;

K_MSGQ_DEFINE(imu_msgq, sizeof(struct imu_sample), IMU_MSGQ_DEPTH, 4);

static struct k_work imu_work;

static int16_t sv_to_mg(const struct sensor_value *sv)
{
	/* sensor_value is m/s^2; convert to mg: 1g = 9.80665 m/s^2 */
	int32_t mg = (sv->val1 * 1000 + sv->val2 / 1000) * 1000 / 9807;

	return (int16_t)CLAMP(mg, INT16_MIN, INT16_MAX);
}

static int16_t sv_to_mdps(const struct sensor_value *sv)
{
	/* sensor_value is rad/s (val1 integer, val2 millionths).
	 * 1 rad/s = 57295.78 mdps. Use int64 to avoid overflow on val2 multiply.
	 */
	int64_t mdps = (int64_t)sv->val1 * 57296 +
		       ((int64_t)sv->val2 * 57296) / 1000000;

	return (int16_t)CLAMP(mdps, INT16_MIN, INT16_MAX);
}

static void imu_work_handler(struct k_work *work)
{
	static uint32_t sample_count;
	static int64_t last_log_ms;

	int64_t now = k_uptime_get();

	sample_count++;
	if (now - last_log_ms >= 1000) {
		LOG_INF("sample rate: %u Hz", sample_count);
		sample_count = 0;
		last_log_ms = now;
	}

	struct sensor_value ax, ay, az, gx, gy, gz;

	sensor_sample_fetch_chan(imu_dev, SENSOR_CHAN_ACCEL_XYZ);
	sensor_channel_get(imu_dev, SENSOR_CHAN_ACCEL_X, &ax);
	sensor_channel_get(imu_dev, SENSOR_CHAN_ACCEL_Y, &ay);
	sensor_channel_get(imu_dev, SENSOR_CHAN_ACCEL_Z, &az);

	sensor_sample_fetch_chan(imu_dev, SENSOR_CHAN_GYRO_XYZ);
	sensor_channel_get(imu_dev, SENSOR_CHAN_GYRO_X, &gx);
	sensor_channel_get(imu_dev, SENSOR_CHAN_GYRO_Y, &gy);
	sensor_channel_get(imu_dev, SENSOR_CHAN_GYRO_Z, &gz);

	struct imu_sample s = {
		.accel_x = sv_to_mg(&ax),
		.accel_y = sv_to_mg(&ay),
		.accel_z = sv_to_mg(&az),
		.gyro_x  = sv_to_mdps(&gx),
		.gyro_y  = sv_to_mdps(&gy),
		.gyro_z  = sv_to_mdps(&gz),
	};

	if (k_msgq_put(&imu_msgq, &s, K_NO_WAIT) != 0) {
		LOG_WRN("imu_msgq full, sample dropped");
	}
}

static void imu_trigger_handler(const struct device *dev,
				const struct sensor_trigger *trig)
{
	k_work_submit(&imu_work);
}

int imu_start(void)
{
	imu_dev = DEVICE_DT_GET_ONE(st_lsm6ds3);

	if (!device_is_ready(imu_dev)) {
		LOG_ERR("IMU device not ready");
		return -ENODEV;
	}

	struct sensor_value odr = { .val1 = 104, .val2 = 0 };

	if (sensor_attr_set(imu_dev, SENSOR_CHAN_ACCEL_XYZ,
			    SENSOR_ATTR_SAMPLING_FREQUENCY, &odr) < 0) {
		LOG_ERR("Cannot set accel ODR");
		return -EIO;
	}

	if (sensor_attr_set(imu_dev, SENSOR_CHAN_GYRO_XYZ,
			    SENSOR_ATTR_SAMPLING_FREQUENCY, &odr) < 0) {
		LOG_ERR("Cannot set gyro ODR");
		return -EIO;
	}

	k_work_init(&imu_work, imu_work_handler);

	struct sensor_trigger trig = {
		.type = SENSOR_TRIG_DATA_READY,
		.chan = SENSOR_CHAN_ACCEL_XYZ,
	};

	if (sensor_trigger_set(imu_dev, &trig, imu_trigger_handler) != 0) {
		LOG_ERR("Cannot set sensor trigger");
		return -EIO;
	}

	LOG_INF("IMU started at 104 Hz");
	return 0;
}

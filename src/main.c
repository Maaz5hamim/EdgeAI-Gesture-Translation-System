#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "imu.h"

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

extern struct k_msgq imu_msgq;

int main(void)
{
	if (imu_start() != 0) {
		LOG_ERR("Failed to start IMU");
		return 0;
	}

	struct imu_sample s;
	uint32_t count = 0;

	while (1) {
		k_msgq_get(&imu_msgq, &s, K_FOREVER);
		count++;

		if (count % 104 == 0) {
			LOG_INF("accel x:%d mg y:%d mg z:%d mg | "
				"gyro x:%d mdps y:%d mdps z:%d mdps",
				s.accel_x, s.accel_y, s.accel_z,
				s.gyro_x, s.gyro_y, s.gyro_z);
		}
	}
}

#include "main_functions.hpp"
#include "output_handler.hpp"
#include "constants.hpp"
#include "imu_handler.hpp"
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/gpio.h>
#include "gesture_model.h"
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

static double model_input[kWindowSize * kFeatureCount];
static double model_output[kGestureCount];

int run_inference(){
    PrepareModelInput(model_input);

    score(model_input, model_output);

    float processed_scores[kGestureCount];
    for (int i = 0; i < kGestureCount; i++) {
        processed_scores[i] = (float)model_output[i];
    }

    int gesture_index = 7; // Default to "NONE"
    float max_val = 0.0f;

    for (int i = 0; i < kGestureCount; i++) {
        if ((float)model_output[i] > max_val) {
            max_val = (float)model_output[i];
            gesture_index = i;
        }
    }

    // Apply confidence threshold; if too low, force to "NONE"
    if (max_val < kDetectionThreshold) {
        gesture_index = 7; 
    }

    return gesture_index;
}

bool setup()
{
	LOG_INF("Setup Initialization");

	if (!SetupIMU()) {
		LOG_ERR("Failed to initialize IMU\n");
		return false;
	}

    SetupOutput();

	return true;
}

void loop(void)
{
	k_sem_take(&gesture_trigger_sem, K_FOREVER); 

	k_msleep(480);

    // StreamIMUData(); //for data collection

    int gesture_index = run_inference();

    if (gesture_index != 7){
        HandleOutput(gesture_index);
    }

	k_msleep(500); 
	while (k_sem_take(&gesture_trigger_sem, K_NO_WAIT) == 0);
}
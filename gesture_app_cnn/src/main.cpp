#include "main_functions.hpp"
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(gesture_app, LOG_LEVEL_INF);

int main(int argc, char *argv[])
{
	TfLiteStatus setup_status = setup();
	if (setup_status != kTfLiteOk) {
        LOG_ERR("Setup Failed.\n");
        return -1; 
    }
	while (true) {
		loop();
	}
}
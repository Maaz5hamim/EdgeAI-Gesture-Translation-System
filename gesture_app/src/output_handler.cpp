#include "output_handler.hpp"
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

/* Get LED definitions from DeviceTree */
static const struct gpio_dt_spec leds[] = {
    GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led1), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led2), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led3), gpios),
};

static bool leds_initialized = false;

void HandleOutput(int kind) {
    /* Initialize LEDs once */
    if (!leds_initialized) {
        for (int i = 0; i < 4; i++) {
            if (device_is_ready(leds[i].port)) {
                gpio_pin_configure_dt(&leds[i], GPIO_OUTPUT_INACTIVE);
            }
        }
        leds_initialized = true;
    }

    /* First, turn all LEDs off */
    for (int i = 0; i < 4; i++) {
        gpio_pin_set_dt(&leds[i], 0);
    }

    /* Turn on the specific LED for the detected gesture (0, 1, 2, or 3) */
    if (kind >= 0 && kind <= 3) {
        gpio_pin_set_dt(&leds[kind], 1);
        
        // Optional: Print the name for debugging
        const char* names[] = {"UP", "DOWN", "LEFT", "RIGHT"};
        MicroPrintf("Gesture Detected: %s", names[kind]);
    } 
    // else {
    //     MicroPrintf("Status: STATIC (No LEDs)");
    // }
}
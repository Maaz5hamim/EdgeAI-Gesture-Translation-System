#include "output_handler.hpp"
#include "ble_keyboard.h"
#include "constants.hpp"
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <tensorflow/lite/micro/micro_log.h>

/* Get LED definitions from DeviceTree */
static const struct gpio_dt_spec leds[] = {
    GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led1), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led2), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led3), gpios),
};

static bool leds_initialized = false;

void SetupOutput(void) {
    /* Initialize LEDs once */
    if (!leds_initialized) {
        for (int i = 0; i < 4; i++) {
            if (device_is_ready(leds[i].port)) {
                gpio_pin_configure_dt(&leds[i], GPIO_OUTPUT_INACTIVE);
            }
        }
        leds_initialized = true;
    }

    /* Initialize BLE Keyboard */
    ble_keyboard_init();
    MicroPrintf("Outputs Initialized (LEDs + BLE)");
}

void HandleOutput(int kind) {
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

    // Map ML output to BLE HID Gesture
    gesture_type_t ble_gesture = GESTURE_NONE;
    
    switch(kind) {
        case kSlideUp:    ble_gesture = GESTURE_SWIPE_UP; break;
        case kSlideDown:  ble_gesture = GESTURE_SWIPE_DOWN; break;
        case kSlideLeft:  ble_gesture = GESTURE_SWIPE_LEFT; break;
        case kSlideRight: ble_gesture = GESTURE_SWIPE_RIGHT; break;
        default: return; // Unknown gesture
    }

    // Submit to the BLE queue
    if (gesture_hid_is_ready()) {
        gesture_submit_simple(ble_gesture);
        MicroPrintf("Gesture sent over BLE!");
    } else {
        MicroPrintf("BLE not ready, gesture ignored.");
    }
}
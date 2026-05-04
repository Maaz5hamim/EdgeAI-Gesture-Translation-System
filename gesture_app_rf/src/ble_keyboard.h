#ifndef BLE_KEYBOARD_H
#define BLE_KEYBOARD_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    GESTURE_NONE = 0,
    GESTURE_SWIPE_UP,
    GESTURE_SWIPE_DOWN,
    GESTURE_SWIPE_LEFT,
    GESTURE_SWIPE_RIGHT,
    GESTURE_COUNT
} gesture_type_t;

// Initialization function 
int ble_keyboard_init(void);

// Existing API to submit gestures to BLE queue
int gesture_submit(gesture_type_t type, float confidence);
int gesture_submit_simple(gesture_type_t type);
bool gesture_hid_is_ready(void);

#ifdef __cplusplus
}
#endif

#endif // BLE_KEYBOARD_H
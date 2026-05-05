/**
 * @file ble_keyboard.c
 * @brief BLE HID Keyboard with TinyML Gesture Classification Interface
 * 
 * This code receives gesture classifications from a TinyML model
 * and sends corresponding arrow key inputs over BLE HID.
 */

#include "ble_keyboard.h"
#include <zephyr/types.h>
#include <stddef.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/settings/settings.h>
#include <bluetooth/services/hids.h>

/*===========================================================================*/
/* GESTURE CLASSIFICATION DEFINITIONS                                        */
/*===========================================================================*/

/**
 * @brief Gesture classification result from TinyML model
 */
typedef struct {
    gesture_type_t type;       /**< Classified gesture type */
    float confidence;          /**< Confidence score (0.0 - 1.0) */
    int64_t timestamp;         /**< Timestamp when gesture was detected */
} gesture_result_t;

/**
 * @brief Configuration for gesture processing
 */
typedef struct {
    float confidence_threshold;  /**< Minimum confidence to accept gesture */
    uint32_t debounce_ms;        /**< Minimum time between gestures */
    uint32_t key_hold_ms;        /**< How long to hold key down */
    uint32_t key_gap_ms;         /**< Gap between key repeats */
    uint32_t key_repeat_count;   /**< Number of key press cycles per gesture */
    uint32_t key_repeat_count_vert;   /**< Number of key press cycles for vertical gestures */
    uint32_t key_repeat_count_horiz;  /**< Number of key press cycles for horizontal gestures */
} gesture_config_t;

/*===========================================================================*/
/* CONFIGURATION                                                              */
/*===========================================================================*/

#define OUTPUT_REPORT_MAX_LEN     1
#define INPUT_REPORT_KEYS_MAX_LEN 8

/* Speed tuning */
#define USE_QUEUED_WRITES         1

/* Gesture processing defaults */
#define DEFAULT_CONFIDENCE_THRESHOLD  0.7f
#define DEFAULT_DEBOUNCE_MS          200
#define DEFAULT_KEY_HOLD_MS           50
#define DEFAULT_KEY_GAP_MS            10
#define DEFAULT_KEY_REPEAT_COUNT       10
#define DEFAULT_KEY_REPEAT_COUNT_VERT  7
#define DEFAULT_KEY_REPEAT_COUNT_HORIZ  1

/* Thread configuration */
#define GESTURE_THREAD_STACK_SIZE   2048
#define GESTURE_THREAD_PRIORITY     K_PRIO_COOP(2)
#define KEY_THREAD_STACK_SIZE       1024
#define KEY_THREAD_PRIORITY         K_PRIO_COOP(1)

/* Message queue for gestures */
#define GESTURE_QUEUE_SIZE          8

/* Arrow key HID usage codes */
#define KEY_UP_ARROW    0x52
#define KEY_DOWN_ARROW  0x51
#define KEY_LEFT_ARROW  0x50
#define KEY_RIGHT_ARROW 0x4F

/*===========================================================================*/
/* GLOBAL STATE                                                               */
/*===========================================================================*/

static volatile bool hid_ready = false;

BT_HIDS_DEF(hids_obj,
            OUTPUT_REPORT_MAX_LEN,
            INPUT_REPORT_KEYS_MAX_LEN);

static struct bt_conn *current_conn;
static volatile bool is_secured = false;
static volatile bool input_rep_enabled = false;

/* Pre-allocated report buffers */
static uint8_t press_report[8] __aligned(4);
static uint8_t release_report[8] __aligned(4) = {0};

/* Flow control */
static atomic_t pending_sends = ATOMIC_INIT(0);
#define MAX_PENDING_SENDS 6

/* Gesture processing state */
static gesture_config_t gesture_config = {
    .confidence_threshold = DEFAULT_CONFIDENCE_THRESHOLD,
    .debounce_ms = DEFAULT_DEBOUNCE_MS,
    .key_hold_ms = DEFAULT_KEY_HOLD_MS,
    .key_gap_ms = DEFAULT_KEY_GAP_MS,
    .key_repeat_count_vert = DEFAULT_KEY_REPEAT_COUNT_VERT,
    .key_repeat_count_horiz = DEFAULT_KEY_REPEAT_COUNT_HORIZ,
};

static int64_t last_gesture_time = 0;

/* Message queue for gesture results */
K_MSGQ_DEFINE(gesture_msgq, sizeof(gesture_result_t), GESTURE_QUEUE_SIZE, 4);

/* Thread stacks */
static K_THREAD_STACK_DEFINE(key_stack, KEY_THREAD_STACK_SIZE);
static struct k_thread key_thread;

static K_THREAD_STACK_DEFINE(gesture_stack, GESTURE_THREAD_STACK_SIZE);
static struct k_thread gesture_thread;

/* Semaphore for key sending */
static volatile uint8_t pending_keycode = 0;
static K_SEM_DEFINE(key_sem, 0, 1);

/*===========================================================================*/
/* GESTURE TO KEYCODE MAPPING                                                 */
/*===========================================================================*/

/**
 * @brief Map gesture type to HID keycode
 * @param gesture The gesture type
 * @return HID keycode, or 0 if no mapping exists
 */
static uint8_t gesture_to_keycode(gesture_type_t gesture)
{
    switch (gesture) {
    case GESTURE_SWIPE_UP:
        return KEY_DOWN_ARROW;
    case GESTURE_SWIPE_DOWN:
        return KEY_UP_ARROW;
    case GESTURE_SWIPE_LEFT:
        return KEY_LEFT_ARROW;
    case GESTURE_SWIPE_RIGHT:
        return KEY_RIGHT_ARROW;
    default:
        return 0;
    }
}

/**
 * @brief Get human-readable name for gesture type
 */
static const char *gesture_name(gesture_type_t gesture)
{
    static const char *names[] = {
        [GESTURE_NONE] = "NONE",
        [GESTURE_SWIPE_UP] = "SWIPE_UP",
        [GESTURE_SWIPE_DOWN] = "SWIPE_DOWN",
        [GESTURE_SWIPE_LEFT] = "SWIPE_LEFT",
        [GESTURE_SWIPE_RIGHT] = "SWIPE_RIGHT",
    };
    
    if (gesture < GESTURE_COUNT) {
        return names[gesture];
    }
    return "UNKNOWN";
}

/*===========================================================================*/
/* PUBLIC API - Call these from your TinyML code                             */
/*===========================================================================*/

/**
 * @brief Submit a gesture classification result
 * 
 * Call this function from your TinyML inference code when a gesture
 * is classified. The gesture will be queued and processed by the
 * gesture handler thread.
 * 
 * @param type The classified gesture type
 * @param confidence Confidence score (0.0 to 1.0)
 * @return 0 on success, negative error code on failure
 * 
 * @example
 *   // In your TinyML inference callback:
 *   if (inference_result.class == CLASS_SWIPE_UP) {
 *       gesture_submit(GESTURE_SWIPE_UP, inference_result.confidence);
 *   }
 */
int gesture_submit(gesture_type_t type, float confidence)
{
    gesture_result_t result = {
        .type = type,
        .confidence = confidence,
        .timestamp = k_uptime_get(),
    };
    
    int err = k_msgq_put(&gesture_msgq, &result, K_NO_WAIT);
    if (err) {
        printk("Gesture queue full, dropping gesture\n");
    }
    return err;
}

/**
 * @brief Submit a gesture with default confidence
 * 
 * Convenience function when confidence is not available or always high.
 * 
 * @param type The classified gesture type
 * @return 0 on success, negative error code on failure
 */
int gesture_submit_simple(gesture_type_t type)
{
    return gesture_submit(type, 1.0f);
}

/**
 * @brief Check if HID is ready to send keypresses
 * @return true if connected and ready, false otherwise
 */
bool gesture_hid_is_ready(void)
{
    return hid_ready;
}

/**
 * @brief Update gesture processing configuration
 * @param config New configuration to apply
 */
void gesture_set_config(const gesture_config_t *config)
{
    if (config) {
        gesture_config = *config;
        printk("Gesture config updated: thresh=%.2f, debounce=%dms\n",
               (double)gesture_config.confidence_threshold,
               gesture_config.debounce_ms);
    }
}

/**
 * @brief Get current gesture configuration
 * @param config Output parameter for current configuration
 */
void gesture_get_config(gesture_config_t *config)
{
    if (config) {
        *config = gesture_config;
    }
}

/*===========================================================================*/
/* BLE HID INTERNALS                                                         */
/*===========================================================================*/

static void report_sent_cb(struct bt_conn *conn, void *user_data)
{
    ARG_UNUSED(conn);
    ARG_UNUSED(user_data);
    atomic_dec(&pending_sends);
}

static void boot_kb_notif_handler(enum bt_hids_notify_evt evt)
{
    printk("Boot KB notifications: %s\n",
           evt == BT_HIDS_CCCD_EVT_NOTIFY_ENABLED ? "ON" : "OFF");
}

static void input_rep_notif_handler(enum bt_hids_notify_evt evt)
{
    input_rep_enabled = (evt == BT_HIDS_CCCD_EVT_NOTIFY_ENABLED);
    printk("Input report notifications: %s\n", input_rep_enabled ? "ON" : "OFF");
    
    if (input_rep_enabled && is_secured) {
        hid_ready = true;
        printk("*** HID READY - Gestures will now send keypresses ***\n");
    } else {
        hid_ready = false;
    }
}

static void hids_pm_evt_handler(enum bt_hids_pm_evt evt, struct bt_conn *conn)
{
    ARG_UNUSED(conn);
    printk("Protocol mode: %s\n",
           evt == BT_HIDS_PM_EVT_BOOT_MODE_ENTERED ? "BOOT" : "REPORT");
}

static void pairing_complete(struct bt_conn *conn, bool bonded)
{
    ARG_UNUSED(conn);
    printk("Pairing complete (bonded=%d)\n", bonded);
}

static void pairing_failed(struct bt_conn *conn, enum bt_security_err reason)
{
    ARG_UNUSED(conn);
    printk("Pairing failed (reason=%d)\n", reason);
}

static struct bt_conn_auth_info_cb auth_info_cb = {
    .pairing_complete = pairing_complete,
    .pairing_failed = pairing_failed,
};

static void auth_passkey_confirm(struct bt_conn *conn, unsigned int passkey)
{
    printk("Passkey: %06u - Auto confirming\n", passkey);
    bt_conn_auth_passkey_confirm(conn);
}

static struct bt_conn_auth_cb auth_cb = {
    .passkey_confirm = auth_passkey_confirm,
};

static void request_fast_conn_params(struct bt_conn *conn)
{
    const struct bt_le_conn_param fast_params = {
        .interval_min = 12,
        .interval_max = 24,
        .latency = 0,
        .timeout = 400,
    };

    int err = bt_conn_le_param_update(conn, &fast_params);
    printk("Connection param update request: %d\n", err);
}

static void connected(struct bt_conn *conn, uint8_t err)
{
    char addr[BT_ADDR_LE_STR_LEN];

    bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

    if (err) {
        printk("Connection failed (err %u)\n", err);
        return;
    }

    printk("Connected: %s\n", addr);

    current_conn = bt_conn_ref(conn);
    is_secured = false;
    input_rep_enabled = false;
    atomic_set(&pending_sends, 0);

    bt_hids_connected(&hids_obj, conn);
    bt_conn_set_security(conn, BT_SECURITY_L2);
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
    ARG_UNUSED(conn);
    printk("Disconnected (reason=0x%02x)\n", reason);

    bt_hids_disconnected(&hids_obj, conn);
    
    if (current_conn) {
        bt_conn_unref(current_conn);
        current_conn = NULL;
    }
    
    is_secured = false;
    hid_ready = false;
    atomic_set(&pending_sends, 0);
    
    /* Clear any pending gestures */
    k_msgq_purge(&gesture_msgq);
}

static void security_changed(struct bt_conn *conn, bt_security_t level,
                             enum bt_security_err err)
{
    printk("Security level: %d (err=%d)\n", level, err);
    
    if (!err && level >= BT_SECURITY_L2) {
        is_secured = true;
        if (input_rep_enabled) {
            hid_ready = true;
            printk("*** HID READY - Gestures will now send keypresses ***\n");
        }
        request_fast_conn_params(conn);
    }
}

static void conn_param_updated(struct bt_conn *conn, uint16_t interval,
                               uint16_t latency, uint16_t timeout)
{
    ARG_UNUSED(conn);
    printk("Conn params: interval=%d (%.2fms), latency=%d, timeout=%d\n",
           interval, interval * 1.25, latency, timeout);
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected = connected,
    .disconnected = disconnected,
    .security_changed = security_changed,
    .le_param_updated = conn_param_updated,
};

/*===========================================================================*/
/* KEY SENDING                                                               */
/*===========================================================================*/

static inline int send_report_fast(const uint8_t *data)
{
    if (!current_conn || atomic_get(&pending_sends) >= MAX_PENDING_SENDS) {
        return -EAGAIN;
    }

    atomic_inc(&pending_sends);

#if USE_QUEUED_WRITES
    return bt_hids_inp_rep_send(&hids_obj, current_conn, 0,
                                data, 8, report_sent_cb);
#else
    int err = bt_hids_inp_rep_send(&hids_obj, current_conn, 0,
                                   data, 8, NULL);
    if (err) {
        atomic_dec(&pending_sends);
    }
    return err;
#endif
}

static void key_sender_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);

    while (1) {
        k_sem_take(&key_sem, K_FOREVER);

        uint8_t keycode = pending_keycode;

        if (!hid_ready || !current_conn || keycode == 0) {
            continue;
        }

        /* Pick repeat count based on axis */
        bool is_horizontal = (keycode == KEY_LEFT_ARROW || keycode == KEY_RIGHT_ARROW);
        uint32_t repeat_count = is_horizontal
            ? gesture_config.key_repeat_count_horiz
            : gesture_config.key_repeat_count_vert;

        memset(press_report, 0, sizeof(press_report));
        press_report[2] = keycode;

        int64_t start = k_uptime_get();
        uint32_t sent = 0;

        for (uint32_t i = 0; i < repeat_count && hid_ready; i++) {
            /* Wait for queue space */
            int timeout = 50;
            while (atomic_get(&pending_sends) >= MAX_PENDING_SENDS && timeout-- > 0) {
                k_sleep(K_MSEC(1));
            }
            if (!hid_ready) break;

            /* PRESS */
            if (send_report_fast(press_report) < 0) continue;

            /* HOLD */
            k_sleep(K_MSEC(gesture_config.key_hold_ms));

            /* RELEASE */
            while (atomic_get(&pending_sends) >= MAX_PENDING_SENDS && hid_ready) {
                k_sleep(K_MSEC(1));
            }
            send_report_fast(release_report);

            sent++;

            /* GAP before next cycle */
            if (gesture_config.key_gap_ms > 0) {
                k_sleep(K_MSEC(gesture_config.key_gap_ms));
            }
        }

        printk("Sent %d keypresses in %lld ms\n", sent, k_uptime_get() - start);
    }
}

static void send_keycode(uint8_t keycode)
{
    pending_keycode = keycode;
    k_sem_give(&key_sem);
}

/*===========================================================================*/
/* GESTURE PROCESSING THREAD                                                 */
/*===========================================================================*/

static void gesture_handler_thread(void *a, void *b, void *c)
{
    ARG_UNUSED(a);
    ARG_UNUSED(b);
    ARG_UNUSED(c);

    gesture_result_t result;

    printk("Gesture handler thread started\n");

    while (1) {
        /* Wait for gesture from TinyML */
        int err = k_msgq_get(&gesture_msgq, &result, K_FOREVER);
        if (err) {
            continue;
        }

        /* Log received gesture */
        printk("Gesture: %s (conf=%.2f)\n",
               gesture_name(result.type), (double)result.confidence);

        /* Filter: Ignore NONE gestures */
        if (result.type == GESTURE_NONE) {
            continue;
        }

        /* Filter: Check confidence threshold */
        if (result.confidence < gesture_config.confidence_threshold) {
            printk("  -> Rejected: confidence %.2f < threshold %.2f\n",
                   (double)result.confidence, (double)gesture_config.confidence_threshold);
            continue;
        }

        /* Filter: Debounce - ignore rapid repeated gestures */
        int64_t now = k_uptime_get();
        if ((now - last_gesture_time) < gesture_config.debounce_ms) {
            printk("  -> Rejected: debounce (%lld ms since last)\n",
                   now - last_gesture_time);
            continue;
        }
        last_gesture_time = now;

        /* Check if HID is ready */
        if (!hid_ready) {
            printk("  -> Rejected: HID not ready\n");
            continue;
        }

        /* Map gesture to keycode */
        uint8_t keycode = gesture_to_keycode(result.type);
        if (keycode == 0) {
            printk("  -> Rejected: no keycode mapping\n");
            continue;
        }

        /* Send the keypress */
        printk("  -> Sending keycode 0x%02X\n", keycode);
        send_keycode(keycode);
    }
}

/*===========================================================================*/
/* HID SERVICE INITIALIZATION                                                */
/*===========================================================================*/

static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA_BYTES(BT_DATA_UUID16_ALL,
                  BT_UUID_16_ENCODE(BT_UUID_HIDS_VAL),
                  BT_UUID_16_ENCODE(BT_UUID_BAS_VAL)),
    BT_DATA_BYTES(BT_DATA_GAP_APPEARANCE, 0xC1, 0x03),
};

static const struct bt_data sd[] = {
    BT_DATA(BT_DATA_NAME_COMPLETE, CONFIG_BT_DEVICE_NAME,
            sizeof(CONFIG_BT_DEVICE_NAME) - 1),
};

static const uint8_t hid_report_map[] = {
    0x05, 0x01,        /* Usage Page (Generic Desktop) */
    0x09, 0x06,        /* Usage (Keyboard) */
    0xA1, 0x01,        /* Collection (Application) */
    0x05, 0x07,        /*   Usage Page (Key Codes) */
    0x19, 0xE0,        /*   Usage Minimum (224) */
    0x29, 0xE7,        /*   Usage Maximum (231) */
    0x15, 0x00,        /*   Logical Minimum (0) */
    0x25, 0x01,        /*   Logical Maximum (1) */
    0x75, 0x01,        /*   Report Size (1) */
    0x95, 0x08,        /*   Report Count (8) */
    0x81, 0x02,        /*   Input (Data, Variable, Absolute) - Modifier byte */
    0x95, 0x01,        /*   Report Count (1) */
    0x75, 0x08,        /*   Report Size (8) */
    0x81, 0x01,        /*   Input (Constant) - Reserved byte */
    0x95, 0x06,        /*   Report Count (6) */
    0x75, 0x08,        /*   Report Size (8) */
    0x15, 0x00,        /*   Logical Minimum (0) */
    0x25, 0x65,        /*   Logical Maximum (101) */
    0x05, 0x07,        /*   Usage Page (Key Codes) */
    0x19, 0x00,        /*   Usage Minimum (0) */
    0x29, 0x65,        /*   Usage Maximum (101) */
    0x81, 0x00,        /*   Input (Data, Array) - Key arrays (6 keys) */
    0x95, 0x05,        /*   Report Count (5) */
    0x75, 0x01,        /*   Report Size (1) */
    0x05, 0x08,        /*   Usage Page (LEDs) */
    0x19, 0x01,        /*   Usage Minimum (1) */
    0x29, 0x05,        /*   Usage Maximum (5) */
    0x91, 0x02,        /*   Output (Data, Variable, Absolute) - LED report */
    0x95, 0x01,        /*   Report Count (1) */
    0x75, 0x03,        /*   Report Size (3) */
    0x91, 0x01,        /*   Output (Constant) - LED padding */
    0xC0               /* End Collection */
};

static void hids_outp_rep_handler(struct bt_hids_rep *rep,
                                  struct bt_conn *conn, bool write)
{
    ARG_UNUSED(rep);
    ARG_UNUSED(conn);
    ARG_UNUSED(write);
}

static void hids_boot_kb_outp_rep_handler(struct bt_hids_rep *rep,
                                          struct bt_conn *conn, bool write)
{
    ARG_UNUSED(rep);
    ARG_UNUSED(conn);
    ARG_UNUSED(write);
}

static void hid_init(void)
{
    int err;
    struct bt_hids_init_param hids_init = {0};
    struct bt_hids_inp_rep *inp_rep;
    struct bt_hids_outp_feat_rep *outp_rep;

    hids_init.rep_map.data = hid_report_map;
    hids_init.rep_map.size = sizeof(hid_report_map);

    hids_init.info.bcd_hid = 0x0111;
    hids_init.info.b_country_code = 0x00;
    hids_init.info.flags = BT_HIDS_REMOTE_WAKE | BT_HIDS_NORMALLY_CONNECTABLE;

    hids_init.is_kb = true;
    hids_init.pm_evt_handler = hids_pm_evt_handler;
    hids_init.boot_kb_notif_handler = boot_kb_notif_handler;
    hids_init.boot_kb_outp_rep_handler = hids_boot_kb_outp_rep_handler;

    inp_rep = &hids_init.inp_rep_group_init.reports[0];
    inp_rep->size = INPUT_REPORT_KEYS_MAX_LEN;
    inp_rep->id = 0;
    inp_rep->handler = input_rep_notif_handler;
    hids_init.inp_rep_group_init.cnt = 1;

    outp_rep = &hids_init.outp_rep_group_init.reports[0];
    outp_rep->size = OUTPUT_REPORT_MAX_LEN;
    outp_rep->id = 0;
    outp_rep->handler = hids_outp_rep_handler;
    hids_init.outp_rep_group_init.cnt = 1;

    err = bt_hids_init(&hids_obj, &hids_init);
    printk("bt_hids_init: %d\n", err);
}

/*===========================================================================*/
/* MAIN                                                                       */
/*===========================================================================*/

int ble_keyboard_init(void)
{
    int err;
    
    // Initialize Bluetooth
    err = bt_enable(NULL);
    if (err) {
        printk("Bluetooth init failed: %d\n", err);
        return err;
    }

    if (IS_ENABLED(CONFIG_BT_SETTINGS)) {
        settings_load();
    }

    bt_conn_auth_cb_register(&auth_cb);
    bt_conn_auth_info_cb_register(&auth_info_cb);

    hid_init();

    k_thread_create(&key_thread, key_stack, KEY_THREAD_STACK_SIZE,
                    key_sender_thread, NULL, NULL, NULL,
                    KEY_THREAD_PRIORITY, 0, K_NO_WAIT);

    k_thread_create(&gesture_thread, gesture_stack, GESTURE_THREAD_STACK_SIZE,
                    gesture_handler_thread, NULL, NULL, NULL,
                    GESTURE_THREAD_PRIORITY, 0, K_NO_WAIT);

    err = bt_le_adv_start(BT_LE_ADV_CONN_FAST_1, ad, ARRAY_SIZE(ad),
                          sd, ARRAY_SIZE(sd));
    if (err) {
        printk("Advertising failed to start: %d\n", err);
        return err;
    }

    return 0;
}
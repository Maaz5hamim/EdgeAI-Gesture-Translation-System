#include "main_functions.hpp"
#include "output_handler.hpp"
#include "constants.hpp"
#include "gesture_model.hpp"
#include "imu_handler.hpp"
#include <tensorflow/lite/micro/micro_log.h>
#include <tensorflow/lite/micro/micro_interpreter.h>
#include <tensorflow/lite/micro/micro_mutable_op_resolver.h>
#include <tensorflow/lite/schema/schema_generated.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

namespace {
	const tflite::Model *model = nullptr;
	tflite::MicroInterpreter *interpreter = nullptr;
	TfLiteTensor *model_input = nullptr;
	int input_length;

	/* Create an area of memory to use for input, output, and intermediate arrays.
	* The size of this will depend on the model.
	*/
	constexpr int kTensorArenaSize = 100 * 1024;
	static uint8_t tensor_arena[kTensorArenaSize];
} /* namespace */

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

TfLiteStatus setup()
{
	LOG_INF("Setup Initialization");

	/* Map the model into a usable data structure. */
	model = tflite::GetModel(gesture_model_data);
	if (model->version() != TFLITE_SCHEMA_VERSION) {
		MicroPrintf("Model provided is schema version %d not equal "
				    "to supported version %d.",
				    model->version(), TFLITE_SCHEMA_VERSION);
		return kTfLiteApplicationError;
	}

	LOG_INF("Model loaded");

	/* Pull in only the operation implementations we need.
	 * This relies on a complete list of all the ops needed by this graph.
	 * An easier approach is to just use the AllOpsResolver, but this will
	 * incur some penalty in code space for op implementations that are not
	 * needed by this graph.
	 */
	static tflite::MicroMutableOpResolver < 13 > micro_op_resolver; /* NOLINT */
	micro_op_resolver.AddConv2D();
	micro_op_resolver.AddDepthwiseConv2D();
	micro_op_resolver.AddFullyConnected();
	micro_op_resolver.AddMaxPool2D();
	micro_op_resolver.AddSoftmax();
	micro_op_resolver.AddExpandDims();
	micro_op_resolver.AddReshape();
	micro_op_resolver.AddMean();
	micro_op_resolver.AddMul();
	micro_op_resolver.AddAdd();
	micro_op_resolver.AddSpaceToBatchNd();
	micro_op_resolver.AddBatchToSpaceNd();
	micro_op_resolver.AddReduceMax();

	/* Build an interpreter to run the model with. */
	static tflite::MicroInterpreter static_interpreter(model, micro_op_resolver, tensor_arena, kTensorArenaSize);
	interpreter = &static_interpreter;

	/* Allocate memory from the tensor_arena for the model's tensors. */
	TfLiteStatus allocate_status = interpreter->AllocateTensors();

    if (allocate_status != kTfLiteOk) {
        MicroPrintf("Failed to allocate tensors. Arena is likely too small.\n");
        return kTfLiteApplicationError; 
    }

	LOG_INF("Tensors allocated");

	model_input = interpreter->input(0);
	if (model_input->dims->data[1] != kWindowSize || 
    model_input->dims->data[2] != kFeatureCount) {
    	MicroPrintf("Dimension mismatch! Model expects %dx%d", 
            model_input->dims->data[1], 
			model_input->dims->data[2]);
        return kTfLiteApplicationError;
	}

	LOG_INF("Model validated");

	input_length = model_input->bytes / sizeof(float);

	if (!SetupIMU()) {
		LOG_ERR("Failed to initialize IMU\n");
		return kTfLiteApplicationError;
	}

	return kTfLiteOk;
}

void loop(void)
{
	k_sem_take(&gesture_trigger_sem, K_FOREVER); 

	k_msleep(480);

	int gesture_index = run_inference();

    HandleOutput(gesture_index);

	k_msleep(500); 
	while (k_sem_take(&gesture_trigger_sem, K_NO_WAIT) == 0);

}
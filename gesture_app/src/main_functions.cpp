#include "main_functions.hpp"
#include "output_handler.hpp"
#include "gesture_predictor.hpp"
#include "constants.hpp"
#include "gesture_model.hpp"
#include "imu_handler.hpp"
#include <tensorflow/lite/micro/micro_log.h>
#include <tensorflow/lite/micro/micro_interpreter.h>
#include <tensorflow/lite/micro/micro_mutable_op_resolver.h>
#include <tensorflow/lite/schema/schema_generated.h>
#include <zephyr/sys/printk.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(gesture_app, LOG_LEVEL_INF);

namespace {
	const tflite::Model *model = nullptr;
	tflite::MicroInterpreter *interpreter = nullptr;
	TfLiteTensor *model_input = nullptr;
	int input_length;

	/* Create an area of memory to use for input, output, and intermediate arrays.
	* The size of this will depend on the model.
	*/
	constexpr int kTensorArenaSize = 80 * 1024;
	static uint8_t tensor_arena[kTensorArenaSize];
} /* namespace */

void collect_data(float *input_buffer)
{
	for (int i = 0; i < 40; i++) {
		int off = i * 6;
		
		printk("%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n", 
				(double)input_buffer[off+0], (double)input_buffer[off+1], 
				(double)input_buffer[off+2], (double)input_buffer[off+3], 
				(double)input_buffer[off+4], (double)input_buffer[off+5]);
		
		// 10ms delay = 100Hz. This prevents "messages dropped"
		k_msleep(10); 
	}
}

void setup(void)
{
	/* Map the model into a usable data structure. */
	model = tflite::GetModel(gesture_model_data);
	if (model->version() != TFLITE_SCHEMA_VERSION) {
		MicroPrintf("Model provided is schema version %d not equal "
				    "to supported version %d.",
				    model->version(), TFLITE_SCHEMA_VERSION);
		return;
	}

	/* Pull in only the operation implementations we need.
	 * This relies on a complete list of all the ops needed by this graph.
	 * An easier approach is to just use the AllOpsResolver, but this will
	 * incur some penalty in code space for op implementations that are not
	 * needed by this graph.
	 */
	static tflite::MicroMutableOpResolver < 8 > micro_op_resolver; /* NOLINT */
	micro_op_resolver.AddConv2D();
	micro_op_resolver.AddDepthwiseConv2D();
	micro_op_resolver.AddFullyConnected();
	micro_op_resolver.AddMaxPool2D();
	micro_op_resolver.AddSoftmax();
	micro_op_resolver.AddExpandDims();
	micro_op_resolver.AddReshape();
	micro_op_resolver.AddMean();

	/* Build an interpreter to run the model with. */
	static tflite::MicroInterpreter static_interpreter(model, micro_op_resolver, tensor_arena, kTensorArenaSize);
	interpreter = &static_interpreter;

	/* Allocate memory from the tensor_arena for the model's tensors. */
	TfLiteStatus allocate_status = interpreter->AllocateTensors();

    if (allocate_status != kTfLiteOk) {
        MicroPrintf("Failed to allocate tensors. Arena is likely too small.\n");
        return; 
    }

	model_input = interpreter->input(0);
	if (model_input->dims->data[1] != kWindowSize || 
    model_input->dims->data[2] != kFeatureCount) {
    	MicroPrintf("Dimension mismatch! Model expects %dx%d", 
            model_input->dims->data[1], 
			model_input->dims->data[2]);
        return;
	}

	input_length = model_input->bytes / sizeof(float);

	TfLiteStatus setup_status = SetupIMU();
	if (setup_status != kTfLiteOk) {
		MicroPrintf("IMU set up failed\n");
	}
}

void loop(void)
{
	/* Attempt to read new data from the accelerometer. */
	bool read_data = ReadIMU(model_input->data.f, input_length);

	/* If there was no new data, wait until next time. */
	if (!read_data) {
		return;
	}

	/* Run inference, and report any error */
	TfLiteStatus invoke_status = interpreter->Invoke();
	if (invoke_status != kTfLiteOk) {
		MicroPrintf("Invoke failed on index: %d\n", begin_index);
		return;
	}
	/* Analyze the results to obtain a prediction */
	int gesture_index = PredictGesture(interpreter->output(0)->data.f);

	// float* output_data = interpreter->output(0)->data.f;

	// int gesture_index = 0;
	// float max_prob = output_data[0];

	// for (int i = 1; i < kGestureCount; i++) {
	// 	if (output_data[i] > max_prob) {
	// 		max_prob = output_data[i];
	// 		gesture_index = i;
	// 	}
	// }

	// printk("Probabilities: UP=%.2f DOWN=%.2f LEFT=%.2f RIGHT=%.2f\n",
    //    (double)output_data[0], 
    //    (double)output_data[1], 
    //    (double)output_data[2], 
    //    (double)output_data[3]);

	/* Produce an output */
	HandleOutput(gesture_index); 
}

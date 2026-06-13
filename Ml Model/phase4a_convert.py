
import numpy as np
import tensorflow as tf
import os

print("=" * 55)
print("PHASE 4a — TFLite Conversion")
print("=" * 55)

# ── Load trained Keras model ──────────────────
model = tf.keras.models.load_model("dc_model.keras")
print(f"\nKeras model loaded.")
print(f"Input shape : {model.input_shape}")
print(f"Output shape: {model.output_shape}")

# ── Representative dataset for int8 calibration ──
# TFLite needs sample inputs to calibrate quantization ranges
X_train = np.load("datacenter_X_train.npy").astype(np.float32)

def representative_dataset():
    for i in range(0, min(200, len(X_train))):
        sample = X_train[i:i+1]
        yield [sample]

# ── Convert: float32 baseline ─────────────────
converter_f32 = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_f32    = converter_f32.convert()

with open("model_float32.tflite", "wb") as f:
    f.write(tflite_f32)

size_f32 = os.path.getsize("model_float32.tflite") / 1024
print(f"\nFloat32 model saved  : model_float32.tflite  ({size_f32:.1f} KB)")

# ── Convert: int8 quantized ───────────────────
converter_int8 = tf.lite.TFLiteConverter.from_keras_model(model)
converter_int8.optimizations                    = [tf.lite.Optimize.DEFAULT]
converter_int8.representative_dataset           = representative_dataset
converter_int8.target_spec.supported_ops        = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter_int8.inference_input_type             = tf.float32   # keep float input for simplicity
converter_int8.inference_output_type            = tf.float32   # keep float output

tflite_int8 = converter_int8.convert()

with open("model.tflite", "wb") as f:
    f.write(tflite_int8)

size_int8 = os.path.getsize("model.tflite") / 1024
print(f"Int8 model saved     : model.tflite          ({size_int8:.1f} KB)")
print(f"Size reduction       : {size_f32/size_int8:.1f}x smaller after quantization")

# ── Quick accuracy check on TFLite model ──────
print("\nVerifying TFLite accuracy on 50 test samples...")

interpreter = tf.lite.Interpreter(model_path="model.tflite")
interpreter.allocate_tensors()

input_idx  = interpreter.get_input_details()[0]["index"]
output_idx = interpreter.get_output_details()[0]["index"]

X_test = np.load("datacenter_X_test.npy").astype(np.float32)
y_test = np.load("datacenter_y_test.npy")

correct = 0
n_check = 50
for i in range(n_check):
    interpreter.set_tensor(input_idx, X_test[i:i+1])
    interpreter.invoke()
    pred = np.argmax(interpreter.get_tensor(output_idx))
    if pred == y_test[i]:
        correct += 1

tflite_acc = correct / n_check * 100
print(f"TFLite accuracy (sample): {tflite_acc:.1f}%")

print("\n" + "=" * 55)
print("Files ready for RPi deployment:")
print("  model.tflite        ← main model file")
print("  scaler.pkl          ← from Phase 2")
print("  label_encoder.pkl   ← from Phase 2")
print("=" * 55)

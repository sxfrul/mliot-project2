

import numpy as np
import time
import os
import psutil

try:
    import tflite_runtime.interpreter as tflite
    Interpreter = tflite.Interpreter
    print("Using tflite_runtime (RPi optimized)")
except ImportError:
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter
    print("Using tensorflow.lite (laptop fallback)")

print("=" * 55)
print("PHASE 4b — RPi Benchmark")
print("=" * 55)

# ── Load model ────────────────────────────────
interpreter = Interpreter(model_path="model.tflite")
interpreter.allocate_tensors()

input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_idx      = input_details[0]["index"]
output_idx     = output_details[0]["index"]

print(f"\nModel input  : {input_details[0]['shape']}  dtype={input_details[0]['dtype']}")
print(f"Model output : {output_details[0]['shape']} dtype={output_details[0]['dtype']}")

# ── File size ─────────────────────────────────
size_tflite = os.path.getsize("model.tflite") / 1024
size_f32    = os.path.getsize("model_float32.tflite") / 1024 \
              if os.path.exists("model_float32.tflite") else None

print(f"\nModel size (int8)   : {size_tflite:.1f} KB")
if size_f32:
    print(f"Model size (float32): {size_f32:.1f} KB")
    print(f"Compression ratio   : {size_f32/size_tflite:.2f}x")

# ── Latency benchmark ─────────────────────────
N_RUNS  = 200
N_FEATURES = input_details[0]["shape"][1]
dummy_input = np.random.rand(1, N_FEATURES).astype(np.float32)

# Warm-up
for _ in range(10):
    interpreter.set_tensor(input_idx, dummy_input)
    interpreter.invoke()

# Timed runs
latencies = []
for _ in range(N_RUNS):
    t0 = time.perf_counter()
    interpreter.set_tensor(input_idx, dummy_input)
    interpreter.invoke()
    _ = interpreter.get_tensor(output_idx)
    latencies.append((time.perf_counter() - t0) * 1000)  # ms

latencies = np.array(latencies)
print(f"\nLatency over {N_RUNS} runs:")
print(f"  Mean    : {latencies.mean():.3f} ms")
print(f"  Median  : {np.median(latencies):.3f} ms")
print(f"  Min     : {latencies.min():.3f} ms")
print(f"  Max     : {latencies.max():.3f} ms")
print(f"  Std dev : {latencies.std():.3f} ms")
print(f"  Throughput : {1000/latencies.mean():.0f} predictions/sec")

# ── Memory usage ──────────────────────────────
process = psutil.Process(os.getpid())
mem_mb  = process.memory_info().rss / (1024 * 1024)
print(f"\nProcess RAM usage   : {mem_mb:.1f} MB")
print(f"Available RAM on RPi: {psutil.virtual_memory().available / (1024*1024):.0f} MB")

# ── Suitability verdict ───────────────────────
print("\n" + "─" * 55)
print("SUITABILITY FOR REAL-TIME DEPLOYMENT")
print("─" * 55)

mean_ms = latencies.mean()
if mean_ms < 5:
    verdict = "EXCELLENT — suitable for 100Hz+ sensing loops"
elif mean_ms < 20:
    verdict = "GOOD — suitable for 1–10 second sensing intervals"
elif mean_ms < 100:
    verdict = "ACCEPTABLE — suitable for 30-second intervals"
else:
    verdict = "SLOW — consider further optimization"

print(f"  Inference time : {mean_ms:.2f} ms  → {verdict}")
print(f"\nReport these numbers in your project documentation.")
print("=" * 55)

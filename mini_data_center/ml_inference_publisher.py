import os
import sys
import select
import termios
import tty
import json
import time
import math
import pickle
from collections import deque

import warnings
import numpy as np
import serial
import paho.mqtt.client as mqtt

warnings.filterwarnings("ignore", category=UserWarning)

try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:
    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        import tensorflow as tf
        Interpreter = tf.lite.Interpreter

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE   = 9600

MODEL_DIR     = os.path.join(os.path.dirname(__file__), "..", "Ml Model")
TFLITE_PATH   = os.path.join(MODEL_DIR, "model.tflite")
SCALER_PATH   = os.path.join(MODEL_DIR, "scaler.pkl")
LABELS_PATH   = os.path.join(MODEL_DIR, "label_encoder.pkl")
PUE_PATH      = os.path.join(MODEL_DIR, "rf_pue_model.pkl")
WUE_PATH      = os.path.join(MODEL_DIR, "rf_wue_model.pkl")

MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "MLIOT/datacenter"
MQTT_USERNAME = None
MQTT_PASSWORD = None

PUBLISH_INTERVAL = 5

SEND_COMMANDS = True
ENABLE_SMOKE_SIM_KEYS = True
SMOKE_FORCES_EMERGENCY = True
ACTUATOR_CMD = {
    "air":            b"A",
    "evaporative":    b"E",
    "emergency":      b"M",
    "humidity_warn":  b"H",
    "security_alert": b"S",
}

SENSOR_COLS = ["temperature_C", "humidity_pct", "power_kW",
               "airflow_cfm", "water_flow_L", "smoke_ppm"]

FEATURE_ORDER = (
    SENSOR_COLS
    + ["water_leak", "motion_detected", "door_open"]
    + [c + "_delta"   for c in SENSOR_COLS]
    + [c + "_rollstd" for c in SENSOR_COLS]
    + ["hour_sin", "hour_cos"]
    + ["flag_temp_high", "flag_smoke_warn", "flag_smoke_crit",
       "flag_humidity_low", "flag_humidity_high", "flag_power_high",
       "flag_airflow_low", "flag_night_motion"]
)
assert len(FEATURE_ORDER) == 31, f"expected 31 features, got {len(FEATURE_ORDER)}"

HOST, PORT, TOPIC = MQTT_HOST, MQTT_PORT, MQTT_TOPIC
USERNAME, PASSWORD = MQTT_USERNAME, MQTT_PASSWORD


def simulate_missing_channels(temp_c, smoke_alert):
    power_kW   = 60.0 + (temp_c - 25.0) * 3.0
    airflow    = 400.0
    water_flow = 8.0
    smoke_ppm  = 400.0 if smoke_alert else 40.0
    water_leak = 0
    motion     = 0
    door_open  = 0
    return power_kW, airflow, water_flow, smoke_ppm, water_leak, motion, door_open


class FeatureBuilder:

    def __init__(self, scaler):
        self.scaler = scaler
        self.prev_scaled = None
        self.window = deque(maxlen=5)

    def build(self, raw_sensors, water_leak, motion, door_open):
        scaled = self.scaler.transform([raw_sensors])[0]

        if self.prev_scaled is None:
            delta = np.zeros(6)
        else:
            delta = np.round(scaled - self.prev_scaled, 4)
        self.prev_scaled = scaled

        self.window.append(scaled)
        arr = np.array(self.window)
        rollstd = np.std(arr, axis=0, ddof=1) if len(arr) >= 2 else np.zeros(6)
        rollstd = np.round(np.nan_to_num(rollstd), 4)

        hour = time.localtime().tm_hour
        hour_sin = round(math.sin(2 * math.pi * hour / 24), 4)
        hour_cos = round(math.cos(2 * math.pi * hour / 24), 4)

        t, h, p, a, w, s = scaled
        flags = [
            int(t > 0.70),
            int(s > 0.40),
            int(s > 0.75),
            int(h < 0.25),
            int(h > 0.80),
            int(p > 0.75),
            int(a < 0.15),
            int(motion == 1 and (hour < 6 or hour >= 22)),
        ]

        vec = (
            list(scaled)
            + [water_leak, motion, door_open]
            + list(delta)
            + list(rollstd)
            + [hour_sin, hour_cos]
            + flags
        )
        return np.array(vec, dtype=np.float32).reshape(1, -1)


def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def parse_line(line):
    parts = line.split(",")
    if len(parts) != 5:
        return None
    try:
        return {
            "temperature": float(parts[0]),
            "humidity":    float(parts[1]),
            "fan":         int(parts[2]),
            "cooling_led": int(parts[3]),
            "smoke":       int(parts[4]),
        }
    except ValueError:
        return None


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[MQTT] Connected to {HOST}:{PORT}"
          if reason_code == 0 else f"[MQTT] Connect failed ({reason_code})")


def main():
    print("[ML] Loading model files...")
    scaler = load_pickle(SCALER_PATH)
    le     = load_pickle(LABELS_PATH)
    class_names = list(le.classes_)

    interpreter = Interpreter(model_path=TFLITE_PATH)
    interpreter.allocate_tensors()
    in_idx  = interpreter.get_input_details()[0]["index"]
    out_idx = interpreter.get_output_details()[0]["index"]

    try:
        rf_pue = load_pickle(PUE_PATH)
        rf_wue = load_pickle(WUE_PATH)
        have_reg = True
    except Exception as e:
        print(f"[ML] PUE/WUE regressors unavailable ({e}). Continuing without them.")
        rf_pue = rf_wue = None
        have_reg = False

    print(f"[ML] Classes: {class_names}")
    builder = FeatureBuilder(scaler)

    print(f"[Serial] Opening {SERIAL_PORT} @ {BAUD_RATE} ...")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
    time.sleep(2)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD)
    client.connect(HOST, PORT, keepalive=60)
    client.loop_start()
    print(f"[MQTT] Publishing to topic: {TOPIC}")
    if ENABLE_SMOKE_SIM_KEYS:
        print("Press 's' to simulate smoke, 'c' to clear (no Enter needed).")
    print("Press Ctrl+C to stop.\n")

    old_term = None
    if ENABLE_SMOKE_SIM_KEYS and sys.stdin.isatty():
        old_term = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    last = 0
    try:
        while True:
            if old_term is not None and select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1).lower()
                if ch == "s":
                    ser.write(b"1")
                    print("[SIM] smoke ON")
                elif ch == "c":
                    ser.write(b"0")
                    print("[SIM] smoke OFF")

            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            reading = parse_line(line)
            if reading is None:
                print(f"[Serial] skip: {line}")
                continue

            now = time.time()
            if now - last < PUBLISH_INTERVAL:
                continue
            last = now

            (power_kW, airflow, water_flow, smoke_ppm,
             water_leak, motion, door_open) = simulate_missing_channels(
                reading["temperature"], reading["smoke"])

            raw_sensors = [
                reading["temperature"], reading["humidity"], power_kW,
                airflow, water_flow, smoke_ppm,
            ]

            x = builder.build(raw_sensors, water_leak, motion, door_open)
            interpreter.set_tensor(in_idx, x)
            interpreter.invoke()
            probs = interpreter.get_tensor(out_idx)[0]
            cooling_mode = class_names[int(np.argmax(probs))]
            confidence   = float(np.max(probs))

            if SMOKE_FORCES_EMERGENCY and reading["smoke"]:
                cooling_mode = "emergency"
                confidence   = 1.0

            if SEND_COMMANDS:
                ser.write(ACTUATOR_CMD.get(cooling_mode, b"A"))

            pue = float(rf_pue.predict(x)[0]) if have_reg else None
            wue = float(rf_wue.predict(x)[0]) if have_reg else None

            payload_data = {
                "temperature": reading["temperature"],
                "humidity":    reading["humidity"],
                "smoke_alert": reading["smoke"],
                "cooling_mode": cooling_mode,
                "confidence":   round(confidence, 3),
            }
            if have_reg:
                payload_data["predicted_PUE"] = round(pue, 3)
                payload_data["predicted_WUE"] = round(wue, 3)

            payload = json.dumps(payload_data)

            res = client.publish(TOPIC, payload)
            tag = "OK" if res.rc == 0 else f"ERR {res.rc}"
            pue_str = f"{pue:.3f}" if pue is not None else "n/a"
            wue_str = f"{wue:.3f}" if wue is not None else "n/a"
            print(
                f"[PUB {tag}] "
                f"Temp:{reading['temperature']:.1f}C  "
                f"Hum:{reading['humidity']:.1f}%  "
                f"Smoke:{'DETECTED' if reading['smoke'] else 'clear'}  "
                f"Fan:{'ON' if reading['fan'] else 'OFF'}  "
                f"CoolLED:{'ON' if reading['cooling_led'] else 'OFF'}  "
                f"|  Mode:{cooling_mode} ({confidence:.2f})  "
                f"PUE:{pue_str}  WUE:{wue_str}"
            )

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if old_term is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term)
        client.loop_stop()
        client.disconnect()
        ser.close()
        print("Closed serial and MQTT connections.")


if __name__ == "__main__":
    main()

import json
import time
import serial
import paho.mqtt.client as mqtt

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE   = 9600

MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "MLIOT/datacenter"
MQTT_USERNAME = None
MQTT_PASSWORD = None

PUBLISH_INTERVAL = 5

HOST, PORT, TOPIC = MQTT_HOST, MQTT_PORT, MQTT_TOPIC
USERNAME, PASSWORD = MQTT_USERNAME, MQTT_PASSWORD


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


def build_payload(reading):
    return json.dumps(reading)


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[MQTT] Connected to {HOST}:{PORT}")
    else:
        print(f"[MQTT] Connection failed ({reason_code})")


def main():
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
    print("Press Ctrl+C to stop.\n")

    last_publish = 0
    try:
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue

            reading = parse_line(line)
            if reading is None:
                print(f"[Serial] skip: {line}")
                continue

            now = time.time()
            if now - last_publish < PUBLISH_INTERVAL:
                continue
            last_publish = now

            payload = build_payload(reading)
            result = client.publish(TOPIC, payload)
            status = "OK" if result.rc == 0 else f"ERR {result.rc}"
            print(f"[PUB {status}] {payload}")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        client.loop_stop()
        client.disconnect()
        ser.close()
        print("Closed serial and MQTT connections.")


if __name__ == "__main__":
    main()

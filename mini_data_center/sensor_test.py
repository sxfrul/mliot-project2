import serial
import time

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE   = 9600


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


def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
    time.sleep(2)
    print("Reading sensors. Press Ctrl+C to stop.\n")
    try:
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            r = parse_line(line)
            if r is None:
                print(f"(info) {line}")
                continue
            print(
                f"Temp: {r['temperature']:.1f}C | "
                f"Humidity: {r['humidity']:.1f}% | "
                f"Smoke: {'DETECTED' if r['smoke'] else 'clear'} | "
                f"Fan: {'ON' if r['fan'] else 'OFF'} | "
                f"CoolLED: {'ON' if r['cooling_led'] else 'OFF'}"
            )
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ser.close()


if __name__ == "__main__":
    main()

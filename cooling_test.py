import sys
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO

# ==================================================
# Hardware Configuration
# ==================================================
DHT_PIN = board.D4

RELAY_PIN = 17      # DC Fan Relay
LED_PIN = 27        # Water Cooling Indicator LED

READ_INTERVAL = 3.0

# Temperature Thresholds (°C)
FAN_THRESHOLD = 30.0
WATER_THRESHOLD = 36.0

# ==================================================
# Initialize Sensor
# ==================================================
dht_device = adafruit_dht.DHT11(
    DHT_PIN
)

# ==================================================
# GPIO Setup
# ==================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)

# Ensure outputs start OFF
GPIO.output(RELAY_PIN, GPIO.LOW)
GPIO.output(LED_PIN, GPIO.LOW)

print("=" * 60)
print(" MINI DATA CENTER COOLING SYSTEM")
print("=" * 60)
print(f"Fan Threshold          : {FAN_THRESHOLD}°C")
print(f"Water Cooling Threshold: {WATER_THRESHOLD}°C")
print("Press Ctrl+C to stop.")
print("=" * 60)

try:
    while True:
        time.sleep(READ_INTERVAL)

        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity

            if temperature is None or humidity is None:
                print("Sensor returned invalid data.")
                continue

            print(
                f"\nTemperature: {temperature:.1f}°C | "
                f"Humidity: {humidity:.1f}%"
            )

            # ==========================================
            # Cooling Decision Logic
            # ==========================================

            # Stage 3: Water Cooling Activated
            if temperature >= WATER_THRESHOLD:

                GPIO.output(RELAY_PIN, GPIO.HIGH)
                GPIO.output(LED_PIN, GPIO.HIGH)

                print("STATUS : CRITICAL")
                print("ACTION : Fan ON")
                print("ACTION : Water Cooling ACTIVATED (LED ON)")

            # Stage 2: Air Cooling
            elif temperature > FAN_THRESHOLD:

                GPIO.output(RELAY_PIN, GPIO.HIGH)
                GPIO.output(LED_PIN, GPIO.LOW)

                print("STATUS : WARNING")
                print("ACTION : Fan ON")
                print("ACTION : Water Cooling OFF")

            # Stage 1: Normal
            else:

                GPIO.output(RELAY_PIN, GPIO.LOW)
                GPIO.output(LED_PIN, GPIO.LOW)

                print("STATUS : NORMAL")
                print("ACTION : All Cooling Systems OFF")

        except RuntimeError as error:
            print(f"Reading error (retrying): {error}")
            continue

        except Exception as error:
            print(f"Fatal Error: {error}")
            break

except KeyboardInterrupt:
    print("\nProgram stopped by user.")

finally:
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.output(LED_PIN, GPIO.LOW)

    dht_device.exit()
    GPIO.cleanup()

    print("GPIO cleaned up successfully.")
    sys.exit()

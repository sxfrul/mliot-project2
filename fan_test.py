import time
import RPi.GPIO as GPIO

RELAY_PIN = 17
LED_PIN = 27

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)

print("Testing outputs...")

try:
    while True:
        print("ON")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(3)

        print("OFF")
        GPIO.output(RELAY_PIN, GPIO.LOW)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(3)

except KeyboardInterrupt:
    GPIO.cleanup()

import serial
import time

# change ttyUSB0 to ttyACM0 if not found
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
time.sleep(2)  # wait Arduino reset

print("Listening to Arduino...")

while True:
    line = ser.readline().decode('utf-8').strip()

    if not line:
        continue

    # skip boot messages
    if not line[0].isdigit():
        print(f"Arduino says: {line}")
        continue

    try:
        temp, hum, smoke, relay, led = line.split(',')

        temp  = float(temp)
        hum   = float(hum)
        smoke = int(smoke)
        relay = int(relay)
        led   = int(led)

        print(f"Temp:{temp}C  Hum:{hum}%  Smoke:{'ALERT' if smoke else 'clear'}  Fan:{'ON' if relay else 'OFF'}  CoolLED:{'ON' if led else 'OFF'}")

    except ValueError:
        print(f"Bad data: {line}")

    time.sleep(2)
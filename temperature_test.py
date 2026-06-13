import sys
import time
import board
import adafruit_dht

# Initialize the DHT11 sensor on GPIO 4 (Physical Pin 7)
# The adafruit_dht library uses the board module for pin mapping
dht_device = adafruit_dht.DHT11(board.D4)
dly = 2.0  # Set delay to 2 seconds

print("Starting DHT11 Temperature and Humidity Example...")
print("-" * 50)

try:
    while True:
        time.sleep(dly)

        try:
            # Read from sensor
            temperature_c = dht_device.temperature
            humidity = dht_device.humidity

            # Check if data from sensor read is valid
            if humidity is not None and temperature_c is not None:
                
                print("Temperature: {:.1f}°C Humidity: {:.1f}%".format(
                    temperature_c, humidity))
            else:
                print("Cannot read from device")

        except RuntimeError as error:
            print("Reading error (retrying): {}".format(error.args[0]))
            continue
            
        except Exception as error:
            dht_device.exit()
            raise error

except KeyboardInterrupt:
    print("\nExiting program.")
    dht_device.exit()
    sys.exit()

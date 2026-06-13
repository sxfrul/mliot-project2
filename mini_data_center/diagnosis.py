import time
import board
import adafruit_dht

dht = adafruit_dht.DHT11(board.D4, use_pulseio=False)

while True:
    try:
        print(dht.temperature, dht.humidity)
    except Exception as e:
        print("Error:", e)
    time.sleep(2)

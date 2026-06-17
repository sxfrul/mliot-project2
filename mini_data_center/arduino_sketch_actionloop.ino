#include <DHT.h>
#define DHTPIN      2
#define DHTTYPE     DHT11
#define SMOKE_PIN   3
#define LED_COOL    5
#define SMOKE_LED   6
#define BUZZER_PIN  7
#define RELAY_PIN   8
DHT dht(DHTPIN, DHTTYPE);

char command = 'A';
bool smokeSim = false;

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(SMOKE_PIN,  INPUT);
  pinMode(LED_COOL,   OUTPUT);
  pinMode(SMOKE_LED,  OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RELAY_PIN,  OUTPUT);
  digitalWrite(LED_COOL,   LOW);
  digitalWrite(SMOKE_LED,  LOW);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(RELAY_PIN,  LOW);
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'A' || c == 'E' || c == 'M' || c == 'H' || c == 'S') {
      command = c;
    } else if (c == '1') {
      smokeSim = true;
    } else if (c == '0') {
      smokeSim = false;
    }
  }

  delay(2000);

  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    Serial.println("ERROR,0,0,0");
    return;
  }

  int relayState = 0;
  int ledCool    = 0;
  if (command == 'A') {
    relayState = 1; ledCool = 0;
  } else if (command == 'E' || command == 'M') {
    relayState = 1; ledCool = 1;
  } else {
    relayState = 0; ledCool = 0;
  }
  digitalWrite(RELAY_PIN, relayState ? HIGH : LOW);
  digitalWrite(LED_COOL,  ledCool ? HIGH : LOW);

  int realSmoke  = (digitalRead(SMOKE_PIN) == LOW) ? 1 : 0;
  int smokeAlert = smokeSim ? 1 : realSmoke;
  if (smokeAlert) {
    digitalWrite(SMOKE_LED,  HIGH);
    digitalWrite(BUZZER_PIN, LOW);
  } else {
    digitalWrite(SMOKE_LED,  LOW);
    digitalWrite(BUZZER_PIN, HIGH);
  }

  Serial.print(temp);       Serial.print(",");
  Serial.print(hum);        Serial.print(",");
  Serial.print(relayState); Serial.print(",");
  Serial.print(ledCool);    Serial.print(",");
  Serial.println(smokeAlert);
}

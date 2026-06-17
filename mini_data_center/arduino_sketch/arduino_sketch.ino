#include <DHT.h>
#define DHTPIN      2
#define DHTTYPE     DHT11
#define SMOKE_PIN   3
#define LED_COOL    5
#define SMOKE_LED   6
#define BUZZER_PIN  7
#define RELAY_PIN   8
DHT dht(DHTPIN, DHTTYPE);
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
  delay(2000);
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  int smoke  = digitalRead(SMOKE_PIN);
  // ── DEBUG: print raw smoke value ──
  Serial.print("RAW SMOKE PIN: ");
  Serial.println(smoke); // should be 1=clear, 0=smoke
  if (isnan(temp) || isnan(hum)) {
    Serial.println("ERROR,0,0,0");
    return;
  }
  // ── Cooling logic ──
  int relayState = 0;
  int ledCool    = 0;
  if (temp >= 33) {
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(LED_COOL,  HIGH);
    relayState = 1; ledCool = 1;
  } else if (temp >= 32) {
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(LED_COOL,  LOW);
    relayState = 1; ledCool = 0;
  } else {
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(LED_COOL,  LOW);
  }
  // ── Smoke logic — fixed to HIGH = smoke ──
  int smokeAlert = 0;
  if (smoke == HIGH) {        // ← changed LOW to HIGH
    digitalWrite(SMOKE_LED,  HIGH);
    digitalWrite(BUZZER_PIN, LOW);
    smokeAlert = 1;
  } else {
    digitalWrite(SMOKE_LED,  LOW);
    digitalWrite(BUZZER_PIN, HIGH);
  }
  // ── CSV output ──
  Serial.print(temp);       Serial.print(",");
  Serial.print(hum);        Serial.print(",");
  Serial.print(relayState); Serial.print(",");
  Serial.print(ledCool);    Serial.print(",");
  Serial.println(smokeAlert);
}

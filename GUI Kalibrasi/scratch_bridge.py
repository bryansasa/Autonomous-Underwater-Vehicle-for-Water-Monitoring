import os

code = """#include <Arduino.h>

HardwareSerial ecSerial(1);

// Pin 4 (RX) dan Pin 5 (TX)
const int RX_PIN = 4;
const int TX_PIN = 5;

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  ecSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(200);
  
  Serial.println("TRANSPARENT_BRIDGE_READY: Pin 4 (RX) & Pin 5 (TX) at 9600 baud.");
}

void loop() {
  // Langsung teruskan dari EZO ke USB
  while (ecSerial.available()) {
    int b = ecSerial.read();
    Serial.write((uint8_t)b);
  }

  // Langsung teruskan dari USB ke EZO
  while (Serial.available()) {
    int b = Serial.read();
    ecSerial.write((uint8_t)b);
  }
}
"""

with open(r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp", "w", encoding="utf-8") as f:
    f.write(code.strip())
print("BRIDGE_FIRMWARE_WRITTEN")

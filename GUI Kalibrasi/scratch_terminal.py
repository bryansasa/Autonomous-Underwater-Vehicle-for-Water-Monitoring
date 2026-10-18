import os

code = r"""#include <Arduino.h>

HardwareSerial ecSerial(1);

const int RX_PIN = 16;
const int TX_PIN = 17;

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  ecSerial.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(200);

  Serial.println("UART_READY_ON_16_17");
}

void loop() {
  // Dari EZO ke Laptop
  while (ecSerial.available()) {
    char c = (char)ecSerial.read();
    Serial.write(c);
  }

  // Dari Laptop ke EZO
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      ecSerial.write('\r');
    } else {
      ecSerial.write(c);
    }
  }
}
"""

with open(r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp", "w", encoding="utf-8") as f:
    f.write(code.strip())
print("TERMINAL_PASSTHROUGH_WRITTEN")

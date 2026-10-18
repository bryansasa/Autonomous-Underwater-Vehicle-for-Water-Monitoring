import os

code = """#include <Arduino.h>

HardwareSerial ecSerial(1);

void test_pin_pair(int rx, int tx, const char* desc) {
  ecSerial.end();
  delay(50);
  ecSerial.begin(9600, SERIAL_8N1, rx, tx);
  delay(100);
  while (ecSerial.available()) ecSerial.read();

  // Kirim perintah info
  ecSerial.print("i\\r");
  delay(200);

  String resp = "";
  uint32_t t0 = millis();
  while (millis() - t0 < 300) {
    if (ecSerial.available()) {
      char c = (char)ecSerial.read();
      if (c == '\\r' || c == '\\n') {
        resp.trim();
        if (resp.length() > 0) break;
      } else {
        resp += c;
      }
    }
  }

  if (resp.length() > 0) {
    Serial.printf(">>> MATCH_FOUND! %s -> Respon: [%s]\\n", desc, resp.c_str());
  } else {
    Serial.printf("--- NO_REPLY: %s\\n", desc);
  }
}

void run_all_tests() {
  Serial.println("\\n=== MEMULAI TEST PIN UART EZO ===");
  test_pin_pair(16, 17, "RX=16, TX=17");
  test_pin_pair(17, 16, "RX=17, TX=16");
  test_pin_pair(4, 5,   "RX=4,  TX=5");
  test_pin_pair(5, 4,   "RX=5,  TX=4");
  test_pin_pair(44, 43, "RX=44, TX=43 (Header RX/TX)");
  test_pin_pair(43, 44, "RX=43, TX=44 (Header TX/RX)");
  Serial.println("=== SELESAI TEST PIN UART ===\\n");
}

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  run_all_tests();
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("test") || cmd.equalsIgnoreCase("scan")) {
      run_all_tests();
    }
  }
  delay(100);
}
"""

with open(r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp", "w", encoding="utf-8") as f:
    f.write(code.strip())
print("PIN_TESTER_FIRMWARE_WRITTEN")

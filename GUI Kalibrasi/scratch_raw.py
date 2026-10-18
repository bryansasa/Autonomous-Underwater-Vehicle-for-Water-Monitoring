import os

code = """#include <Arduino.h>

HardwareSerial ecSerial(1);

const int RX_PIN = 4;
const int TX_PIN = 5;
const long BAUD_RATE = 9600;

float last_ec_val = 0.0;
unsigned long last_req_time = 0;
unsigned long last_telemetry_time = 0;
String ec_rx_buffer = "";

void setup() {
  Serial.begin(115200);
  
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  ecSerial.begin(BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(300);

  // Pastikan output parameter EC aktif: O,EC,1
  ecSerial.print("O,EC,1\\r");
  delay(200);

  // Matikan response code *OK jika mengganggu: *OK,0 atau biarkan aktif
  // ecSerial.print("*OK,0\\r");
  // delay(100);

  ecSerial.print("i\\r");
  delay(200);

  Serial.println("SYS_READY: ESP32-S3 EZO-EC Diagnostic Mode Active.");
}

void loop() {
  uint32_t now = millis();

  // 1. Tangkap SEMUA respon dari EZO tanpa filter
  while (ecSerial.available()) {
    char c = (char)ecSerial.read();
    if (c == '\\r' || c == '\\n') {
      ec_rx_buffer.trim();
      if (ec_rx_buffer.length() > 0) {
        Serial.println("RAW_EZO: [" + ec_rx_buffer + "]");

        // Forward response status ke GUI
        if (ec_rx_buffer.startsWith("?") || ec_rx_buffer.startsWith("*")) {
          Serial.println("CAL_RESP,EC," + ec_rx_buffer);
        } else {
          // Angka pembacaan EC
          int comma = ec_rx_buffer.indexOf(',');
          String rawVal = (comma >= 0) ? ec_rx_buffer.substring(0, comma) : ec_rx_buffer;
          rawVal.trim();
          float val = rawVal.toFloat();
          last_ec_val = val;
        }
        ec_rx_buffer = "";
      }
    } else {
      ec_rx_buffer += c;
    }
  }

  // 2. Request 'R' tiap 1.5 detik (beri waktu sensor menyelesaikan kalkulasi)
  if (now - last_req_time >= 1500) {
    last_req_time = now;
    ecSerial.print("R\\r");
  }

  // 3. Kirim paket CAL_RT tiap 1 detik
  if (now - last_telemetry_time >= 1000) {
    last_telemetry_time = now;
    Serial.printf("CAL_RT,%lu,0.00,%.1f,0.00,0.00,0.0,0.0,0.0,0.00,1013.25\\n",
                  now, last_ec_val);
  }

  // 4. Perintah dari host
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\\n');
    cmd.trim();
    if (cmd.length() > 0) {
      Serial.println("FORWARD_TO_EZO: " + cmd);
      ecSerial.print(cmd + "\\r");
    }
  }
}
"""

with open(r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp", "w", encoding="utf-8") as f:
    f.write(code.strip())
print("RAW_DEBUG_FIRMWARE_WRITTEN")

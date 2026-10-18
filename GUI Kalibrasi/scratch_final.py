import os

code = r"""#include <Arduino.h>

HardwareSerial ecSerial(1);

// Pin UART ESP32-S3 ke Atlas Scientific EZO-EC
// ESP32 GPIO 16 (RX) <--- TX sensor EZO-EC
// ESP32 GPIO 17 (TX) ---> RX sensor EZO-EC
const int RX_PIN = 16;
const int TX_PIN = 17;
const long SENSOR_BAUD = 9600;

float last_ec_val = 0.0;
unsigned long last_req_time = 0;
unsigned long last_telemetry_time = 0;
String ec_rx_buf = "";

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  ecSerial.begin(SENSOR_BAUD, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(300);

  // Pastikan continuous mode mati agar tidak tabrakan
  ecSerial.print("C,0\r");
  delay(150);

  Serial.println("SYS_READY: Bridge ESP32-S3 EZO-EC Aktif di Pin 16 (RX) & Pin 17 (TX).");
}

void loop() {
  uint32_t now = millis();

  // 1. Baca balasan dari EZO-EC
  while (ecSerial.available()) {
    char c = (char)ecSerial.read();
    if (c == '\r' || c == '\n') {
      ec_rx_buf.trim();
      if (ec_rx_buf.length() > 0) {
        // Balasan status kalibrasi / query
        if (ec_rx_buf.startsWith("?") || ec_rx_buf.startsWith("*")) {
          Serial.println("CAL_RESP,EC," + ec_rx_buf);
        } else {
          // Nilai pembacaan EC
          int comma = ec_rx_buf.indexOf(',');
          String raw = (comma >= 0) ? ec_rx_buf.substring(0, comma) : ec_rx_buf;
          raw.trim();
          float val = raw.toFloat();
          last_ec_val = val;
        }
        ec_rx_buf = "";
      }
    } else {
      ec_rx_buf += c;
    }
  }

  // 2. Minta bacaan 'R' ke sensor tiap 1 detik
  if (now - last_req_time >= 1000) {
    last_req_time = now;
    ecSerial.print("R\r");
  }

  // 3. Kirim paket telemetri CAL_RT ke GUI tiap 1 detik
  if (now - last_telemetry_time >= 1000) {
    last_telemetry_time = now;
    Serial.printf("CAL_RT,%lu,0.00,%.1f,0.00,0.00,0.0,0.0,0.0,0.00,1013.25\n",
                  now, last_ec_val);
  }

  // 4. Terima perintah dari GUI / Serial Monitor
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      if (cmd.equalsIgnoreCase("CAL_EC,dry") || cmd.equalsIgnoreCase("dry")) {
        ecSerial.print("Cal,dry\r");
      } else if (cmd.startsWith("CAL_EC,one,") || cmd.startsWith("cal,") || cmd.startsWith("CAL,")) {
        String valStr = "1413";
        int commaIdx = cmd.lastIndexOf(',');
        if (commaIdx >= 0) {
          valStr = cmd.substring(commaIdx + 1);
          valStr.trim();
        }
        ecSerial.print("Cal," + valStr + "\r");
      } else if (cmd.startsWith("CAL_EC,low,")) {
        String valStr = cmd.substring(cmd.lastIndexOf(',') + 1);
        valStr.trim();
        ecSerial.print("Cal,low," + valStr + "\r");
      } else if (cmd.startsWith("CAL_EC,high,")) {
        String valStr = cmd.substring(cmd.lastIndexOf(',') + 1);
        valStr.trim();
        ecSerial.print("Cal,high," + valStr + "\r");
      } else if (cmd.equalsIgnoreCase("CAL_EC,?") || cmd.equalsIgnoreCase("Cal,?") || cmd.equalsIgnoreCase("status")) {
        ecSerial.print("Cal,?\r");
      } else if (cmd.equalsIgnoreCase("CAL_EC,clear") || cmd.equalsIgnoreCase("clear")) {
        ecSerial.print("Cal,clear\r");
      } else {
        ecSerial.print(cmd + "\r");
      }
    }
  }
}
"""

with open(r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp", "w", encoding="utf-8") as f:
    f.write(code.strip())
print("FINAL_MAIN_CPP_WRITTEN")

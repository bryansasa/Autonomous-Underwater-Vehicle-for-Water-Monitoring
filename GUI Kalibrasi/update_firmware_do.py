import os

code = r"""#include <Arduino.h>

// Gunakan HardwareSerial 1 untuk komunikasi UART ke Atlas Scientific EZO-DO
HardwareSerial doSerial(1);

// Pin UART ESP32 ke EZO-DO:
// ESP32 GPIO 16 (RX) <--- TX sensor EZO-DO
// ESP32 GPIO 17 (TX) ---> RX sensor EZO-DO
const int RX_PIN = 16;
const int TX_PIN = 17;
const long SENSOR_BAUD = 9600;

float last_do_val = 0.0;
unsigned long last_req_time = 0;
unsigned long last_telemetry_time = 0;
String do_rx_buf = "";

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  doSerial.begin(SENSOR_BAUD, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(300);

  // Matikan continuous reading internal EZO agar sinkron dengan request kita
  doSerial.print("C,0\r");
  delay(150);

  // Pastikan output parameter mg/L aktif
  doSerial.print("O,mg,1\r");
  delay(150);

  Serial.println("SYS_READY: Bridge ESP32 EZO-DO Aktif di Pin 16 (RX) & Pin 17 (TX).");
}

void loop() {
  uint32_t now = millis();

  // 1. Baca respon data dari sensor EZO-DO
  while (doSerial.available()) {
    char c = (char)doSerial.read();
    if (c == '\r' || c == '\n') {
      do_rx_buf.trim();
      if (do_rx_buf.length() > 0) {
        // Jika respon berupa konfirmasi (*OK, *ER) atau query (?CAL, ?I)
        if (do_rx_buf.startsWith("?") || do_rx_buf.startsWith("*")) {
          Serial.println("CAL_RESP,DO," + do_rx_buf);
        } else {
          // Parsing nilai numerik DO (mg/L)
          int comma = do_rx_buf.indexOf(',');
          String raw = (comma >= 0) ? do_rx_buf.substring(0, comma) : do_rx_buf;
          raw.trim();
          float val = raw.toFloat();
          if (val >= 0.0f && val <= 100.0f) {
            last_do_val = val;
          }
        }
        do_rx_buf = "";
      }
    } else {
      do_rx_buf += c;
    }
  }

  // 2. Minta bacaan tunggal 'R' ke sensor EZO-DO tiap 1 detik
  if (now - last_req_time >= 1000) {
    last_req_time = now;
    doSerial.print("R\r");
  }

  // 3. Kirim paket telemetri CAL_RT ke GUI Kalibrasi tiap 1 detik
  // Format: CAL_RT,timestamp,ph,ec,do,temp,roll,pitch,yaw,depth,press
  if (now - last_telemetry_time >= 1000) {
    last_telemetry_time = now;
    Serial.printf("CAL_RT,%lu,7.00,0.0,%.2f,25.00,0.0,0.0,0.0,0.00,1013.25\n",
                  now, last_do_val);
  }

  // 4. Menerima Perintah Kalibrasi dari GUI Kalibrasi atau Serial Monitor
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      if (cmd.equalsIgnoreCase("CAL_DO,zero") || cmd.equalsIgnoreCase("zero") || cmd.equalsIgnoreCase("cal,0")) {
        Serial.println(">>> Mengirim: Cal,0 (Kalibrasi Titik Nol)...");
        doSerial.print("Cal,0\r");
      } 
      else if (cmd.equalsIgnoreCase("CAL_DO,sat,100") || cmd.equalsIgnoreCase("sat") || cmd.equalsIgnoreCase("cal")) {
        Serial.println(">>> Mengirim: Cal (Kalibrasi Udara 100% Saturation)...");
        doSerial.print("Cal\r");
      } 
      else if (cmd.equalsIgnoreCase("CAL_DO,?") || cmd.equalsIgnoreCase("status") || cmd.equalsIgnoreCase("cal,?")) {
        Serial.println(">>> Cek Status Kalibrasi...");
        doSerial.print("Cal,?\r");
      } 
      else if (cmd.equalsIgnoreCase("CAL_DO,clear") || cmd.equalsIgnoreCase("clear") || cmd.equalsIgnoreCase("cal,clear")) {
        Serial.println(">>> Reset Kalibrasi EZO-DO...");
        doSerial.print("Cal,clear\r");
      } 
      else {
        // Passthrough perintah kustom langsung ke sensor
        doSerial.print(cmd + "\r");
      }
    }
  }
}
"""

target_path = r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp"
try:
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(code.strip())
    print(f"SUCCESS: Firmware EZO-DO berhasil ditulis ke {target_path}")
except Exception as e:
    print(f"ERROR: {e}")

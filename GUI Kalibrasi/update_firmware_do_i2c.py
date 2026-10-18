import os

code = r"""#include <Arduino.h>
#include <Wire.h>

// ============================================================================
// Firmware Bridge ESP32-S3: Atlas Scientific EZO-DO via I2C (LED Biru)
// ============================================================================
// Alamat I2C default EZO-DO adalah 0x61 (desimal 97)
#define EZO_DO_ADDR 0x61

// Konfigurasi Pin I2C ESP32-S3:
// Sesuaikan dengan pin fisik yang Anda sambungkan ke modul EZO-DO:
// EZO-DO SDA ---> ESP32-S3 GPIO 8 (atau pin SDA Anda)
// EZO-DO SCL ---> ESP32-S3 GPIO 9 (atau pin SCL Anda)
const int I2C_SDA = 8;
const int I2C_SCL = 9;

float last_do_val = 0.0f;
unsigned long last_req_time = 0;
unsigned long last_telemetry_time = 0;
bool req_pending = false;

// Helper: Kirim string perintah ke modul EZO-DO via I2C
void sendI2CCommand(const char* cmd) {
  Wire.beginTransmission(EZO_DO_ADDR);
  Wire.write(cmd);
  Wire.endTransmission();
}

// Helper: Baca string respon dan kode status dari modul EZO-DO
// Response Code: 1 = Success, 2 = Syntax Error, 254 = Pending, 255 = No Data
String readI2CResponse(byte &statusCode) {
  Wire.requestFrom(EZO_DO_ADDR, 20);
  if (!Wire.available()) {
    statusCode = 255;
    return "";
  }
  statusCode = Wire.read();
  String resp = "";
  while (Wire.available()) {
    char c = Wire.read();
    if (c == 0) break; // null-terminated
    resp += c;
  }
  resp.trim();
  return resp;
}

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  // Inisialisasi bus I2C
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000); // 100 kHz Standard Mode
  delay(300);

  Serial.println("SYS_READY: Bridge I2C EZO-DO Aktif di ESP32-S3 (SDA=" + String(I2C_SDA) + ", SCL=" + String(I2C_SCL) + ")");
  Serial.println("INFO: Modul EZO-DO berada di mode I2C (LED Biru, Alamat 0x61)");
}

void loop() {
  uint32_t now = millis();

  // 1. Kirim request baca 'R' tiap 1 detik (State Machine non-blocking)
  if (!req_pending && (now - last_req_time >= 1000)) {
    last_req_time = now;
    sendI2CCommand("R");
    req_pending = true;
  }

  // 2. Ambil hasil bacaan setelah 650 ms (waktu konversi EZO-DO ~600ms)
  if (req_pending && (now - last_req_time >= 650)) {
    byte code = 0;
    String resp = readI2CResponse(code);
    req_pending = false;

    if (code == 1 && resp.length() > 0) {
      // Ambil angka pertama jika output mengandung format CSV
      int comma = resp.indexOf(',');
      String raw = (comma >= 0) ? resp.substring(0, comma) : resp;
      raw.trim();
      float val = raw.toFloat();
      if (val >= 0.0f && val <= 100.0f) {
        last_do_val = val;
      }
    }
  }

  // 3. Kirim paket telemetri CAL_RT ke GUI Kalibrasi tiap 1 detik
  // Format: CAL_RT,timestamp,ph,ec,do,temp,roll,pitch,yaw,depth,press
  if (now - last_telemetry_time >= 1000) {
    last_telemetry_time = now;
    Serial.printf("CAL_RT,%lu,7.00,0.0,%.2f,25.00,0.0,0.0,0.0,0.00,1013.25\n",
                  now, last_do_val);
  }

  // 4. Menerima Perintah Kalibrasi dari GUI Kalibrasi
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      // Kalibrasi Titik Nol (0% DO)
      if (cmd.equalsIgnoreCase("CAL_DO,zero") || cmd.equalsIgnoreCase("zero") || cmd.equalsIgnoreCase("cal,0")) {
        Serial.println(">>> Mengirim via I2C: Cal,0 (Kalibrasi Titik Nol)...");
        sendI2CCommand("Cal,0");
        delay(900); // Waktu proses kalibrasi ~600-900ms
        byte code;
        String resp = readI2CResponse(code);
        if (code == 1) {
          Serial.println("CAL_RESP,DO,*OK,Zero Point Calibrated (0.00 mg/L)");
        } else {
          Serial.printf("CAL_RESP,DO,*ER,Code=%d: %s\n", code, resp.c_str());
        }
      } 
      // Kalibrasi Udara 100% Saturation
      else if (cmd.equalsIgnoreCase("CAL_DO,sat,100") || cmd.equalsIgnoreCase("sat") || cmd.equalsIgnoreCase("cal")) {
        Serial.println(">>> Mengirim via I2C: Cal (Kalibrasi Udara 100% Saturation)...");
        sendI2CCommand("Cal");
        delay(900);
        byte code;
        String resp = readI2CResponse(code);
        if (code == 1) {
          Serial.println("CAL_RESP,DO,*OK,100% Air Saturation Calibrated");
        } else {
          Serial.printf("CAL_RESP,DO,*ER,Code=%d: %s\n", code, resp.c_str());
        }
      } 
      // Cek Status Kalibrasi
      else if (cmd.equalsIgnoreCase("CAL_DO,?") || cmd.equalsIgnoreCase("status") || cmd.equalsIgnoreCase("cal,?")) {
        sendI2CCommand("Cal,?");
        delay(300);
        byte code;
        String resp = readI2CResponse(code);
        Serial.println("CAL_RESP,DO," + resp);
      } 
      // Reset Kalibrasi
      else if (cmd.equalsIgnoreCase("CAL_DO,clear") || cmd.equalsIgnoreCase("clear") || cmd.equalsIgnoreCase("cal,clear")) {
        sendI2CCommand("Cal,clear");
        delay(300);
        byte code;
        String resp = readI2CResponse(code);
        if (code == 1) {
          Serial.println("CAL_RESP,DO,*OK,Calibration Cleared");
        } else {
          Serial.printf("CAL_RESP,DO,*ER,Code=%d: %s\n", code, resp.c_str());
        }
      }
      // Perintah Khusus: Balikkan EZO ke mode UART (LED Cyan/Hijau)
      else if (cmd.equalsIgnoreCase("to_uart") || cmd.equalsIgnoreCase("uart")) {
        sendI2CCommand("Baud,9600");
        Serial.println("CAL_RESP,DO,*OK,Berhasil diubah ke mode UART 9600! LED EZO akan berubah jadi Hijau/Cyan.");
      }
      else {
        // Passthrough perintah kustom via I2C
        sendI2CCommand(cmd.c_str());
        delay(400);
        byte code;
        String resp = readI2CResponse(code);
        Serial.printf("CAL_RESP,DO,Code=%d,Resp=%s\n", code, resp.c_str());
      }
    }
  }
}
"""

target_path = r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp"
try:
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(code.strip())
    print(f"SUCCESS: Firmware I2C EZO-DO berhasil ditulis ke {target_path}")
except Exception as e:
    print(f"ERROR: {e}")

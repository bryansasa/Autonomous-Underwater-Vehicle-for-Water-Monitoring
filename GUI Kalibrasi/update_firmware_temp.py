import os

code = r"""#include <Arduino.h>
#include <Preferences.h>

// ============================================================================
// Firmware Bridge ESP32-S3: Atlas Scientific Surveyor™ RTD Meter V3.1 + PT-1000
// ============================================================================
// Koneksi Pin ESP32-S3:
//   Surveyor (-)  ---> ESP32-S3 GND
//   Surveyor (+)  ---> ESP32-S3 3.3V (atau 5V)
//   Surveyor (A)  ---> ESP32-S3 GPIO 4 (ADC1_CH3)
//   Probe SMA     ---> Gen 2 Standard PT-1000 Temperature Probe
// ============================================================================

const int TEMP_PIN = 4; // Pin ADC ESP32-S3 (ADC1_CH3)

Preferences prefs;

// Parameter Kalibrasi Sesuai Datasheet Atlas Scientific Surveyor™ RTD
// Rumus: Temp (°C) = (V - V0) / Slope
// Nilai Default langsung dikunci pada hasil kalibrasi ice bath (1.008 V)
const float cal_slope = 0.009f;
float cal_v0 = 1.008f;
bool is_calibrated = true;

float last_temp_val = 21.0f;
float last_voltage_val = 1.197f;
unsigned long last_read_time = 0;
unsigned long last_telemetry_time = 0;

// Fungsi membaca tegangan analog yang di-filter (oversampling 32x)
float read_sensor_voltage() {
  long sum_raw = 0;
  const int SAMPLES = 32;
  for (int i = 0; i < SAMPLES; i++) {
    sum_raw += analogRead(TEMP_PIN);
    delayMicroseconds(250);
  }
  float avg_raw = (float)sum_raw / SAMPLES;

  // Konversi ADC 12-bit (0-4095) ke Tegangan (3.3V)
  float voltage = (avg_raw / 4095.0f) * 3.3f;
  return voltage;
}

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500);

  // Konfigurasi ADC ESP32-S3
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db); // Full range ~3.1V

  // Baca parameter kalibrasi dari Memori Flash (NVS) agar PERMANEN
  prefs.begin("cal_temp", false);
  cal_v0 = prefs.getFloat("v0", 1.008f);
  is_calibrated = prefs.getBool("is_cal", true);

  Serial.println("SYS_READY: Bridge Atlas Scientific Surveyor™ RTD Aktif di ESP32-S3 GPIO 4.");
  Serial.printf("LOADED_CAL: V0=%.3f V (0.0°C), Slope=%.3f V/°C, Calibrated=%d\n",
                cal_v0, cal_slope, is_calibrated ? 1 : 0);
}

void loop() {
  uint32_t now = millis();

  // 1. Baca sensor dan hitung suhu tiap 200 ms
  if (now - last_read_time >= 200) {
    last_read_time = now;
    last_voltage_val = read_sensor_voltage();

    // Hitung suhu berdasar rumus datasheet: °C = (V - V0) / 0.009
    last_temp_val = (last_voltage_val - cal_v0) / cal_slope;
  }

  // 2. Kirim paket telemetri CAL_RT ke GUI Kalibrasi tiap 1 detik
  if (now - last_telemetry_time >= 1000) {
    last_telemetry_time = now;
    Serial.printf("CAL_RT,%lu,7.00,0.0,0.00,%.2f,0.0,0.0,0.0,0.00,1013.25\n",
                  now, last_temp_val);
  }

  // 3. Menerima Perintah Kalibrasi dari GUI Kalibrasi atau Serial Monitor
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      // Kalibrasi Ice Bath (0.0 °C)
      if (cmd.indexOf("ice") >= 0 || cmd.indexOf("ICE") >= 0 || cmd.equalsIgnoreCase("cal,0")) {
        float current_v = read_sensor_voltage();
        cal_v0 = current_v;
        is_calibrated = true;

        // Simpan permanen ke Flash ESP32
        prefs.putFloat("v0", cal_v0);
        prefs.putBool("is_cal", true);

        Serial.printf("CAL_RESP,TEMP,*OK,Ice Bath 0.0C Offset Saved Permanently: %.1f mV (V0=%.3fV)\n",
                      cal_v0 * 1000.0f, cal_v0);
      }
      // Kalibrasi Titik Acuan Sembarang (misal: CAL_TEMP,cal,25.0)
      else if (cmd.startsWith("CAL_TEMP,cal,") || cmd.startsWith("cal,")) {
        String valStr = cmd.substring(cmd.lastIndexOf(',') + 1);
        valStr.trim();
        float target_t = valStr.toFloat();
        float current_v = read_sensor_voltage();
        cal_v0 = current_v - (cal_slope * target_t);
        is_calibrated = true;

        // Simpan permanen ke Flash ESP32
        prefs.putFloat("v0", cal_v0);
        prefs.putBool("is_cal", true);

        Serial.printf("CAL_RESP,TEMP,*OK,Calibrated at %.2f C (Measured: %.3fV, V0=%.3fV)\n",
                      target_t, current_v, cal_v0);
      }
      // Cek Status Kalibrasi
      else if (cmd.indexOf("?") >= 0 || cmd.equalsIgnoreCase("status")) {
        Serial.printf("CAL_RESP,TEMP,?CAL,%d (V0=%.3fV, Slope=%.3fV/C, Current=%.2fC, V=%.3fV)\n",
                      is_calibrated ? 1 : 0, cal_v0, cal_slope, last_temp_val, last_voltage_val);
      }
      // Reset Kalibrasi ke Default Pabrik (Datasheet: V0 = 1.058V)
      else if (cmd.indexOf("clear") >= 0 || cmd.equalsIgnoreCase("reset")) {
        cal_v0 = 1.058f;
        is_calibrated = false;

        prefs.putFloat("v0", 1.058f);
        prefs.putBool("is_cal", false);

        Serial.println("CAL_RESP,TEMP,*OK,Surveyor RTD Factory Defaults Restored (V0=1.058V, Slope=0.009V/C)");
      }
      else {
        Serial.println("CAL_RESP,TEMP,ERROR,Perintah tidak dikenal: " + cmd);
      }
    }
  }
}
"""

target_path = r"C:\PlatformIO\Projects\Kalibrasi_Sensor_TA\src\main.cpp"
try:
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(code.strip())
    print(f"SUCCESS: Firmware Atlas Surveyor RTD (Permanent Flash NVS) berhasil ditulis ke {target_path}")
except Exception as e:
    print(f"ERROR: {e}")

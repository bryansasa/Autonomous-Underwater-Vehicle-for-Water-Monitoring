# DOKUMEN INTEGRASI MICRO-ROS (ESP32-S3), EA-DSRA & GCS TYRANT-AQ

**Proyek:** Wahana Submersible Otonom Pemantau Kualitas Air Waduk Saguling (Tyrant-AQ)  
**Pengembang:** Bryan Gabriel Izaac Sasabone (101022300195) & Charisto Brilliant R.P (101022330187)  
**Status Integrasi:** Selesai Diadaptasi & Siap Diuji (v2.0)

---

## 1. Analisis Kodingan Charisto (`esp.zip` / Downloads)

Charisto telah mengembangkan firmware mikrokontroler **ESP32-S3** menggunakan PlatformIO dan framework **micro-ROS Humble** yang difokuskan pada subsistem **Payload Kualitas Air & Manajemen Daya Adaptif (EA-DSRA)**:

1. **Sensor Kualitas Air & Power Gating MOSFET:**
   - EZO-pH (I2C `0x63`, MOSFET GPIO 5)
   - EZO-EC (I2C `0x64`, MOSFET GPIO 4)
   - EZO-DO (I2C `0x61`, MOSFET GPIO 15)
   - Analog Suhu Air (ADC1 GPIO 7, MOSFET GPIO 6)
2. **Monitoring Arus & Tegangan Ganda (INA226):**
   - Bus Thruster & Baterai 6S LiPo (Shunt 200 A / 75 mV = 0.000375 Ω, rentang 19.8 V s/d 25.2 V)
   - Rel Sensor (Shunt R100 = 0.1 Ω)
3. **Algoritma EA-DSRA On-Chip (`ea_dsra.cpp`):**
   - Menghitung gradien fluktuasi air per kanal ($S_{max}$).
   - Memodulasi interval pengambilan sampel $T_{BM}$ dari 1.0 detik hingga 5.0 detik.
   - Menerapkan penalti energi $W_{EA} = \frac{30.0}{\max(1.0, SoC)}$ jika kapasitas baterai $SoC \le 30.0\%$.
   - **Safety Override:** Memaksa interval sampling 1.0 detik seketika jika DO kritis terdeteksi ($DO \le 2.0\ \text{mg/L}$).
4. **Topik ROS 2 di Namespace `/tyrant/payload`:**
   - `water_quality` (`PayloadWaterQuality`)
   - `power/thruster` & `power/sensors` (`PayloadPower`)
   - `health` (`PayloadHealth`)
   - `communication/diagnostics` (`PayloadCommunicationDiagnostics`)
   - `sensor_power/status` (`SensorPowerStatus`)
   - `heartbeat` (`std_msgs/UInt32`)
   - `host_heartbeat` (`std_msgs/UInt32`) — **Wajib dikirim host pada 10 Hz** (timeout 1000 ms).
   - `sensor_power/request` (`SensorPowerRequest`) — Perintah saklar MOSFET.

---

## 2. Status Kompatibilitas & Penyesuaian Bridge GCS

### Masalah Sebelum Penyesuaian
- `gcs_ros2_bridge.py` sebelumnya hanya berlangganan topik umum `/auv/water_quality` bertipe `Float32MultiArray` dan `/auv/power` bertipe `BatteryState`.
- ESP32 micro-ROS Charisto **memerlukan Host Heartbeat 10 Hz**. Jika tidak ada, ESP32 menganggap host mati dan **menolak perintah daya ON** untuk sensor.
- Parameter EA-DSRA pada jembatan sebelumnya di-hardcode (tetap 3.0, 5.0, 2.0, 4.0 detik), belum merefleksikan nilai dinamis real-time.

### Solusi & Pembaruan yang Telah Dilakukan
1. **Pembaruan Menyeluruh `gcs_ros2_bridge.py`:**
   - Berlangganan langsung ke seluruh topik `/tyrant/payload/*` dan `/tyrant/payload_sim/*`.
   - Mengaktifkan pengiriman otomatis `host_heartbeat` 10 Hz (`std_msgs/UInt32`) ke ESP32.
   - Mengimplementasikan Filter Kalman 1D dan tracking interval EA-DSRA secara real-time.
   - Menjembatani perintah kontrol daya sensor MOSFET (`SensorPowerRequest`).
   - Meneruskan telemetri 32-field extended ASCII ke GCS GUI via TCP Port 9000.
   - Tetap kompatibel penuh dengan Teensy 4.1 (`/auv/imu`, `/auv/depth`, `/auv/thrusters`, `/cmd_vel`).
2. **Penyimpanan Paket Schema ROS 2:**
   - Paket `tyrant_payload_interfaces` diekstrak ke `ros2_ws/src/tyrant_payload_interfaces` lengkap dengan `CMakeLists.txt`, `package.xml`, dan 6 berkas `.msg`.
3. **Penyelarasan Skrip Shell:**
   - Skrip `run_ros2_bridge.sh` dan `run_ros2_bridge.bat` diperbarui untuk auto-sourcing workspace.

---

## 3. Berkas Eksekusi Standalone (.exe) untuk Charisto

Untuk memudahkan Charisto menjalankan GCS di Windows tanpa harus menginstal Python, PyQt5, OpenGL, atau dependensi lainnya, telah dibuild:

- **Lokasi Bundle Executable:**  
  `GCS-Submersible/dist/Tyrant-AQ_GCS/Tyrant-AQ_GCS.exe`
- **File Zip Siap Kirim:**  
  `GCS-Submersible/dist/Tyrant-AQ_GCS_v2.0_Windows.zip` (Ukuran ~144 MB)
- **Launcher 1-Klik:**  
  `Jalankan_GCS.bat` di dalam folder bundle.

---

## 4. Cara Menjalankan Integrasi Lengkap (HIL / Uji Lapangan)

### Di Laptop Linux / Jetson (Tempat Charisto Menjalankan ROS 2):
```bash
# 1. Jalankan micro-ROS Agent untuk ESP32 (misal di /dev/ttyACM0)
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyACM0 -b 115200

# 2. Build interfaces jika belum:
cd ros2_ws
colcon build --packages-select tyrant_payload_interfaces
source install/setup.bash

# 3. Jalankan bridge GCS:
cd GCS-Submersible
./run_ros2_bridge.sh
```

### Di Laptop Windows (Bryan / Charisto):
1. Ekstrak `Tyrant-AQ_GCS_v2.0_Windows.zip`.
2. Klik dua kali `Tyrant-AQ_GCS.exe` (atau `Jalankan_GCS.bat`).
3. Pada Quick Action Bar atas, pilih mode **REAL**, masukkan IP target (IP Linux/Jetson port `9000`), lalu klik **KONEK**.
4. Seluruh telemetri 6-DOF, 3D visual, pembacaan 4 sensor kualitas air, grafik PWM 6 thruster, monitoring baterai Kalman 1D, dan modulasi adaptif EA-DSRA akan langsung tampil aktif dan tercatat otomatis ke CSV log.

# Simulasi payload ESP32-S3 tanpa sensor

Profil `esp32-s3-sim` menghasilkan data buatan di `/tyrant/payload_sim`.
Firmware tidak membuka I2C, membaca ADC, atau mengubah GPIO MOSFET dalam profil ini.
Status daya menunjukkan keadaan logis perintah. Semua nilai, status sensor dan status
bus pada namespace ini adalah simulasi, termasuk suhu yang valid tanpa kalibrasi fisik.
Profil hardware tetap `esp32-s3-devkitm-1` dengan namespace `/tyrant/payload`.
Teensy dan workspace ROS utama tidak diubah.

## 1. Upload dari terminal laptop

Hentikan agent ESP yang sedang berjalan sebelum upload. Periksa alias ESP:

```bash
readlink -f /dev/tyrant-esp
udevadm info --query=property --name=/dev/tyrant-esp | grep '^ID_SERIAL_SHORT='
```

Serial yang diharapkan: `28:84:85:8B:BD:38`.

```bash
cd /home/charisto/tyrant-simple/firmware/esp
bash scripts/build.sh esp32-s3-sim
export PLATFORMIO_CORE_DIR="$PWD/.pio-core"
export PLATFORMIO_CACHE_DIR="$PLATFORMIO_CORE_DIR/.cache"
export PIP_CACHE_DIR="$PLATFORMIO_CORE_DIR/pip-cache"
.pio-core/penv/bin/python -m platformio run -e esp32-s3-sim --target upload --upload-port /dev/tyrant-esp
```

## 2. Persiapan setiap terminal ROS

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
```

Terminal A: agent, memakai port yang sama dengan firmware hardware:

```bash
source /home/charisto/microros_ws/install/setup.bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/tyrant-esp -b 115200 -v4
```

Terminal B: heartbeat host. Hentikan publisher heartbeat lama dan gunakan namespace simulasi:

```bash
ros2 topic pub --rate 10 /tyrant/payload_sim/host_heartbeat std_msgs/msg/UInt32 '{data: 1}'
```

Terminal C: periksa diagnostik, lalu biarkan monitor ACK berjalan:

```bash
ros2 topic echo /tyrant/payload_sim/communication/diagnostics --once
ros2 topic echo /tyrant/payload_sim/sensor_power/status
```

Harapan: `agent_connected=true`, `host_heartbeat_healthy=true`.
Node: `/tyrant/payload_sim/tyrant_payload_esp32_sim`.

## 3. Aktifkan empat kanal logis

Terminal D, setelah heartbeat sehat dan monitor ACK aktif:

```bash
for sensor_id in 1 2 3 4; do
  ros2 topic pub --once /tyrant/payload_sim/sensor_power/request tyrant_payload_interfaces/msg/SensorPowerRequest "{request_id: $((1000 + sensor_id)), sensor_id: $sensor_id, enable: true}"
done
ros2 topic echo /tyrant/payload_sim/water_quality
```

ID: 1 EC, 2 pH, 3 suhu, 4 DO. ACK harus accepted=true, reason=1.
Kanal OFF invalid; setelah ON ada warm-up 1,5 detik dan jadwal sampling sebelum
nilai valid muncul. Siklus skenario dimulai ketika kanal pertama ON teramati.
Interval sampling adaptif 1–5 detik tampak pada pesan water quality.

## 4. Skenario berulang selama 180 detik

| Waktu sejak ON pertama | Data buatan / harapan |
| --- | --- |
| 0–45 detik | EC 1200 µS/cm, pH 7,2, suhu 26 °C, DO 7,5 mg/L, baterai 25,2 V; sampling stabil menuju 5 detik. |
| 45–90 detik | Nilai kualitas air berosilasi; gradien memengaruhi interval adaptif. |
| 90–120 detik | DO 1,5 mg/L; prioritas DO kritis memberi interval 1 detik setelah sampel diterima. |
| 120–123 detik | Tegangan baterai invalid; fallback sampling 1 detik dan reset filter energi. |
| 123–150 detik | Tegangan 20,3 V; penalti energi aktif untuk kondisi baterai rendah. |
| 150–165 detik | EC invalid/ERROR; kanal lain tetap bekerja. Umur sampel EC terus bertambah. |
| 165–180 detik | Monitor daya thruster invalid/ERROR; fallback sampling 1 detik. |
| Setelah 180 detik | Siklus berulang; kanal dan monitor yang gagal pulih. |

Perubahan water quality terlihat saat sampling berikutnya, bukan persis pada batas detik.
Monitor daya sensor buatan tetap 12 V, 0,35 A, 4,2 W; arus thruster buatan 2,5 A.
Untuk memulai siklus dari awal, reboot ESP. OFF/ON kanal tidak me-reset siklus bersama.

Di terminal lain yang sudah di-source:

```bash
ros2 topic echo /tyrant/payload_sim/power/thruster
ros2 topic echo /tyrant/payload_sim/health
```

Ulangi pengujian penghentian heartbeat dan agent seperti profil hardware, tetapi
gunakan prefix `/tyrant/payload_sim`. ON ditolak ketika heartbeat tidak sehat;
OFF tetap diterima. Heartbeat timeout tidak otomatis mematikan kanal yang sudah ON.

## 5. Rekam data buatan

Jalankan sebelum mengaktifkan kanal bila ingin merekam siklus lengkap:

```bash
mkdir -p /home/charisto/tyrant-simple/firmware/esp/host_ws/bags
ros2 bag record -o "/home/charisto/tyrant-simple/firmware/esp/host_ws/bags/payload_sim_$(date +%Y%m%d_%H%M%S)" \
  /tyrant/payload_sim/water_quality \
  /tyrant/payload_sim/power/sensors \
  /tyrant/payload_sim/power/thruster \
  /tyrant/payload_sim/health \
  /tyrant/payload_sim/communication/diagnostics \
  /tyrant/payload_sim/sensor_power/status
```

Hentikan dengan Ctrl+C setelah satu siklus. Periksa direktori hasil memakai
`ros2 bag info <direktori_bag>`. Rekaman ini hanya payload buatan: belum ada pengaitan
kedalaman atau titik misi Teensy, sehingga belum memvalidasi logging misi multi kedalaman.

## 6. Kembali ke firmware hardware

Hentikan agent dan heartbeat simulasi, lalu:

```bash
cd /home/charisto/tyrant-simple/firmware/esp
bash scripts/build.sh esp32-s3-devkitm-1
export PLATFORMIO_CORE_DIR="$PWD/.pio-core"
export PLATFORMIO_CACHE_DIR="$PLATFORMIO_CORE_DIR/.cache"
.pio-core/penv/bin/python -m platformio run -e esp32-s3-devkitm-1 --target upload --upload-port /dev/tyrant-esp
```

Gunakan kembali `/tyrant/payload/host_heartbeat` dan topic hardware. Tanpa sensor
fisik, data harus invalid seperti pada panduan uji board tanpa sensor.

## Verifikasi lokal

```bash
cd /home/charisto/tyrant-simple/firmware/esp
ASAN_OPTIONS=detect_leaks=0 python3 scripts/run_native_tests.py --simulation
```

Lima kelompok uji meliputi isolasi namespace dan IO, warm-up, skenario adaptif,
gangguan/recovery, serta kebijakan heartbeat dan perintah daya. Uji native memakai
IO palsu; hasil upload, USB dan penerimaan ROS profil simulasi perlu diuji pada board.

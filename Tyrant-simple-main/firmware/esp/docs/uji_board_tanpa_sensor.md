# Uji ESP32-S3 tanpa sensor — laptop

Tahap ini menguji koneksi, heartbeat dan logika GPIO/ACK pada ESP fisik.
Sensor dan saklar MOSFET fisik belum terpasang: accepted/actual_enabled hanya
menunjukkan keadaan perintah GPIO. Data INA/EZO yang belum terpasang harus invalid.
Teensy dan workspace ROS utama tidak diubah. Interface host dibangun di `esp/host_ws`.

## Persiapan interface host (sudah PASS pada sesi 2026-10-08)

```bash
cd /home/charisto/tyrant-simple/firmware/esp
bash scripts/build_host_interfaces.sh
```

Pada setiap terminal ROS untuk pengujian:

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
```

## Terminal 1: agent ESP

```bash
source /home/charisto/microros_ws/install/setup.bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/tyrant-esp -b 115200 -v4
```

Node `/tyrant/payload/tyrant_payload_esp32` serta heartbeat ESP otomatis 1 Hz
sudah dilaporkan berhasil oleh pengguna. Gunakan alias, bukan nomor ttyACM.

## Terminal 2: heartbeat host (biarkan aktif)

```bash
ros2 topic pub --rate 10 /tyrant/payload/host_heartbeat std_msgs/msg/UInt32 '{data: 1}'
```

## Terminal 3: diagnostik dan monitor ACK

```bash
ros2 topic echo /tyrant/payload/communication/diagnostics --once
ros2 topic echo /tyrant/payload/sensor_power/status
```

Diagnostik: connection_state=2, agent_connected=true, host_heartbeat_healthy=true,
host_heartbeat_age_ms biasanya <1000. Counter ping/create/disconnect bisa mencerminkan
kejadian sebelum pengujian, jadi gunakan selisih sebelum/sesudah, bukan wajib nol.
Jalankan monitor status SEBELUM mengirim request di terminal 4 agar ACK tidak terlewat.

## Terminal 4: perintah daya

```bash
ros2 topic pub --once /tyrant/payload/sensor_power/request tyrant_payload_interfaces/msg/SensorPowerRequest '{request_id: 101, sensor_id: 1, enable: true}'
```

ACK di terminal 3: request_id=101, accepted=true, reason=1, actual_enabled=true.
ID: 1 EC, 2 pH, 3 suhu analog, 4 DO. Ulangi memakai ID lain dan request_id unik jika
hendak memeriksa semua kanal, lalu matikan kembali setiap kanal.

## Uji host heartbeat timeout

Tekan Ctrl+C hanya pada terminal 2, tunggu >1 detik. Di terminal 4:

```bash
ros2 topic echo /tyrant/payload/communication/diagnostics --once
ros2 topic pub --once /tyrant/payload/sensor_power/request tyrant_payload_interfaces/msg/SensorPowerRequest '{request_id: 102, sensor_id: 1, enable: true}'
ros2 topic pub --once /tyrant/payload/sensor_power/request tyrant_payload_interfaces/msg/SensorPowerRequest '{request_id: 103, sensor_id: 1, enable: false}'
```

Harapan:

- Diagnostik host_heartbeat_healthy=false; age >1000, timeout counter bertambah.
- ACK 102: accepted=false, reason=5. Jika kanal telah ON, actual_enabled tetap true:
  timeout tidak mematikan kanal yang telah ON.
- ACK 103: accepted=true, reason=1, actual_enabled=false.

Setelah selesai, jalankan lagi heartbeat di terminal 2.

## Data tanpa sensor

Hentikan monitor ACK terminal 3 dengan Ctrl+C, lalu:

```bash
ros2 topic echo /tyrant/payload/water_quality --once
ros2 topic echo /tyrant/payload/power/sensors --once
ros2 topic echo /tyrant/payload/power/thruster --once
```

Water quality: validitas kanal false; kanal OFF NOT_INITIALIZED, kanal ON dengan
EZO tidak terpasang akhirnya ERROR. Suhu belum dikalibrasi tidak dinyatakan valid.
INA tidak terpasang: valid=false dan ERROR; nilai NaN dapat muncul.

## Uji pemulihan agent/USB

Dengan ESP tetap terpasang, hentikan agent terminal 1 (Ctrl+C), tunggu 2 detik,
lalu jalankan agent lagi. Heartbeat ESP harus kembali. Diagnostik koneksi/reconnect
counter bertambah bila proses ESP tidak reboot. Host heartbeat harus diterima baru.

Uji berikutnya cabut/pasang USB. Board dapat reboot: uptime, sequence, dan counter
koneksi kembali dari awal merupakan hal yang wajar. Alias `/dev/tyrant-esp` harus
kembali menunjuk serial `28:84:85:8B:BD:38`. Jalankan ulang agent jika ia berhenti
setelah cabut USB; pemulihan agent otomatis di laptop belum dikonfigurasi.

Status sesi 2026-10-08: package interface host build/import PASS. Pengguna melaporkan
upload, heartbeat, ACK, timeout heartbeat, serta penghentian/pemulihan agent berhasil.
Pada cuplikan 30 detik setelah pembaruan transport: connection_count=1,
disconnect_count=0, ping_failures naik 11→12 dan publish_failures naik 1→2.
Koneksi bertahan; kegagalan transport sesekali masih tercatat. Ini laporan operator,
bukan pengujian hardware yang dijalankan otomatis oleh asisten.

Lanjut pengujian data buatan: [simulasi payload](uji_simulasi_payload.md).

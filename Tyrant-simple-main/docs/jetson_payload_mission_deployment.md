# Deploy host misi dan payload ke Jetson — 10 Oktober 2026

Status: deployment ARM64 dan misi normal HIL berhasil pada 10 Oktober 2026.
SSH: `nvidia@10.42.0.246`. Container `tyrant-mission-dev` menggunakan workspace
lama read-only. Hasil verifikasi tersedia di bagian 7.

Lanjutan sesi: container aktif kini `tyrant-mission` dengan autostart dua
agent/heartbeat dan HIL. NTP serta reboot berhasil diverifikasi; gunakan
[panduan autostart](jetson_autostart.md) untuk operasi saat ini.

Kualifikasi laptop sudah mencakup misi normal, penghentian plant HIL saat misi,
dan putus/sambung agent ESP. Pemeriksaan runtime Jetson tercatat di bagian 7.
Source disalin dan dibangun di ARM64; build/install x86 laptop tidak disalin.
Agent micro-ROS ARM64 yang sudah dibangun digunakan kembali.

Jam Jetson sempat tertinggal sekitar dua hari dan telah disesuaikan dengan
jam UTC laptop. `timedatectl` menunjukkan RTC tahun 2000 dan sinkronisasi
NTP belum tercapai. Periksa jam setiap boot sebelum merekam misi; koreksi
sekali ini belum membuktikan waktu akan tetap benar setelah reboot.

Container baru `tyrant-mission-dev` memakai image lama `tyrant-companion:bench`.
Workspace lama dipasang read-only di `/ws`, workspace baru di `/mission_ws`.
Container ini belum otomatis menjalankan misi, agent, atau heartbeat saat boot.
Launch host menghidupkan dua agent dan dua heartbeat saat dijalankan.

## 1. Salin dari laptop

Ganti alamat SSH jika berubah. Bundle berisi lima paket source ROS, dua aturan
port USB, launcher container, dan panduan ini; tidak berisi cache/build/bag.

```bash
scp /home/charisto/tyrant-simple/companion/jetson/dist/tyrant-mission-source.tar.gz nvidia@10.42.0.246:~/
```

## 2. Siapkan pada HOST Jetson (terminal SSH nvidia)

Hentikan launch/agent/plant/heartbeat Tyrant pada laptop terlebih dahulu.
Jangan ada dua agent membuka port yang sama atau dua plant pada domain ROS 0.

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
mkdir -p ~/tyrant-mission-stage ~/ros2_docker/mission_ws/src
tar -xzf ~/tyrant-mission-source.tar.gz -C ~/tyrant-mission-stage
cp -a ~/tyrant-mission-stage/ros2_ws/src/. ~/ros2_docker/mission_ws/src/
sudo install -m 644 ~/tyrant-mission-stage/firmware/esp/deployment/99-tyrant-esp.rules /etc/udev/rules.d/
sudo install -m 644 ~/tyrant-mission-stage/firmware/esp/deployment/99-tyrant-teensy.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty
ls -l /dev/tyrant-esp /dev/tyrant-teensy
```

Hubungkan kedua board ke Jetson. ESP harus memakai firmware `esp32-s3-sim`
dan Teensy profil HIL untuk uji berikut. Aturan alias tidak mengubah firmware.
Verifikasi serial ESP `28:84:85:8B:BD:38`, Teensy `13843280`:

```bash
for port in /dev/tyrant-esp /dev/tyrant-teensy; do
  echo "$port"
  udevadm info --query=property --name="$port" | grep '^ID_SERIAL_SHORT='
done
```

Hentikan container lama yang terlihat aktif di daftar tadi (lewati yang sudah
berhenti). Container dan hasil build lama tetap disimpan:

```bash
docker stop -t 30 tyrant-companion
# Jika ros2 masih berjalan: docker stop -t 30 ros2
bash ~/tyrant-mission-stage/companion/jetson/start_mission_container.sh
docker exec -it tyrant-mission-dev bash
```

## 3. Build di DALAM container (prompt root)

```bash
source /opt/ros/humble/setup.bash
cd /mission_ws
python3 -c 'import rclpy, yaml, rosbag2_py'
CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 colcon build \
  --executor sequential --symlink-install \
  --packages-select tyrant_interfaces tyrant_payload_interfaces tyrant_sim tyrant_teleop tyrant_mission_host \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source /ws/install/setup.bash
source /mission_ws/install/setup.bash
ros2 pkg prefix micro_ros_agent
ros2 interface show tyrant_payload_interfaces/msg/PayloadWaterQuality
ls -l /host-dev/tyrant-esp /host-dev/tyrant-teensy
```

Import pertama harus berhasil. Jika gagal, catat modul yang hilang sebelum
memasang dependensi. Jika agent tidak ditemukan, periksa lokasi install agent
ARM64 lama; jangan membangun ulang atau menyalin binary laptop secara otomatis.

## 4. Jalankan HIL — dua terminal SSH

Di tiap terminal HOST Jetson masuk dengan:

```bash
docker exec -it tyrant-mission-dev bash
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
source /mission_ws/install/setup.bash
```

Terminal A, di dalam container:

```bash
ros2 launch tyrant_sim hil_plant.launch.py
```

Terminal B, di dalam container:

```bash
ros2 launch tyrant_mission_host mission_host.launch.py \
  start_agents:=true \
  teensy_port:=/host-dev/tyrant-teensy esp_port:=/host-dev/tyrant-esp \
  payload_namespace:=/tyrant/payload_sim teensy_simulated:=true \
  plan:=/mission_ws/src/tyrant_mission_host/config/two_depth_hil_sampling_020m.yaml \
  output_dir:=/mission_ws/bags/missions
```

Port memakai `/host-dev` karena mount container ini. Heartbeat host otomatis;
tidak perlu publisher manual. Firmware ESP simulasi memakai namespace
`/tyrant/payload_sim`. Jangan memakai namespace produksi untuk uji ini.

## 5. Periksa dari terminal C

Masuk dan source tiga setup seperti di atas, kemudian:

```bash
ros2 node list
ros2 topic echo /tyrant/system/health --once
ros2 topic echo /tyrant/simple_state --once
ros2 topic echo /tyrant/payload_sim/communication/diagnostics --once
ros2 topic echo /tyrant/host/mission/status --once
```

Sebelum start, harapkan komunikasi dan estimator sehat, state valid, heartbeat
ESP sehat, host IDLE. Bandingkan diagnostik setelah 30 detik: tidak ada
disconnect/reconnect berulang. Counter kegagalan sesaat bukan bukti putus jika
counter koneksi tetap dan telemetry berjalan.

Setelah pemeriksaan lolos, untuk bench HIL yang aktuator fisiknya tidak aktif:

```bash
ros2 service call /tyrant/host/mission/start std_srvs/srv/Trigger '{}'
ros2 topic echo /tyrant/host/mission/status
```

Harapkan `COMPLETE` dan `all_sampling_points_complete: true`; tiap titik
minimal tiga sampel valid tiap sensor. Sesudah selesai tunggu lebih dari dua
detik agar recorder menutup sesi. Jika titik incomplete, lihat timeout, validity,
fase simulasi ESP, dan depth sebelum menganggap deployment berhasil.

Bag, CSV, plan, dan events berada pada HOST di
`/home/nvidia/ros2_docker/mission_ws/bags/missions/`.

## 6. Stop dan kembali ke setup lama

Di terminal C, jika misi masih aktif:

```bash
ros2 service call /tyrant/host/mission/stop std_srvs/srv/Trigger '{}'
```

Tunggu recorder menutup, lalu Ctrl+C launch terminal B dan plant terminal A.
Di HOST Jetson:

```bash
docker stop -t 30 tyrant-mission-dev
docker start tyrant-companion
```

Build lama tidak berubah. Otomatisasi startup dual-agent/host dibahas setelah
tahap ini, karena supervisor lama hanya menangani agent Teensy dan recorder.

## 7. Hasil deployment aktual — 10 Oktober 2026 WIB

- Lima paket ARM64 berhasil dibangun dalam 8 menit 56 detik. Agent lama
  ditemukan pada `/ws/install/micro_ros_agent`; tidak dibangun ulang.
- 37 tes logika lulus. Plugin `anyio` bawaan tidak kompatibel dengan pytest
  container, sehingga tes dijalankan dengan `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.
  Tidak ada perubahan dependensi container untuk mengatasi konflik ini.
- Tes runtime ROS dengan endpoint board tiruan pada domain 141 lulus:
  heartbeat, ACK, sampling, pencatatan manual, finalisasi bag/CSV, serta sensor
  gagal. State invalid menghentikan misi dalam 0,055 detik; state stale dalam
  0,510 detik. Ini hasil endpoint tiruan, bukan pengukuran latensi board fisik.
- Kedua alias di host dan `/host-dev` container cocok dengan serial board.
  Teensy HIL memakai backend 1 dan `physical_output_enabled: false`.
- Misi board HIL `20261009T183003Z_e22db023` berlangsung sekitar 81 detik;
  semua lima langkah selesai dan `all_sampling_points_complete: true`.
  Tiap titik depth 1 dan 3 memperoleh tiga sampel valid per sensor.
- Bag SQLite dapat dibaca: 15.786 pesan. CSV berisi 76 baris, termasuk 24
  sampel titik yang memenuhi syarat. Seluruh 404 pesan SimpleState valid;
  tidak ada pesan actuator dengan output fisik aktif.
- Diagnostik kedua board tetap connection 1, disconnect 0, reconnect 0,
  publish failure 0 sepanjang bag. Counter ping ESP 1285 tetap, bukan
  kegagalan baru selama uji. Semua empat ACK ON dan empat ACK OFF diterima.
- Setelah misi, mode SAFE (4), propulsion tidak diizinkan, dan sensor simulasi
  OFF. Nilai NaN saat OFF adalah kondisi normal.

Saat shutdown pertama, wrapper `ros2 run` ditutup tetapi proses agent anak
tertinggal. Launch diperbaiki untuk menjalankan executable agent langsung,
menggunakan prefix package yang ditemukan dari overlay. Paket host dibangun
ulang (berhasil), kedua agent tersambung kembali, lalu SIGINT menghentikan
host dan kedua agent tanpa proses agent tertinggal. Exit agent `-2` pada log
ini merupakan penghentian oleh SIGINT.

Kondisi akhir: `tyrant-mission-dev` tetap berjalan dengan proses idle dan
daemon ROS CLI; plant, host misi, agent, dan heartbeat pengujian sudah berhenti.
Container lama `tyrant-companion` dan `ros2` tetap berhenti. Untuk mengulang,
gunakan terminal A/B/C pada bagian 4–5; tidak perlu build ulang.

Bukti lokal: [laporan bag](validation/jetson_mission_2026-10-10/hil-report.json),
[log build](validation/jetson_mission_2026-10-10/build-jetson.log),
[tes logika](validation/jetson_mission_2026-10-10/tests-jetson.log),
[tes runtime](validation/jetson_mission_2026-10-10/ros-smoke-jetson.log), serta
[log shutdown setelah perbaikan](validation/jetson_mission_2026-10-10/run/host-shutdown-fix.log).
Salinan sesi juga tersimpan di folder validation tersebut.

Uji putus plant dan putus ESP pada board fisik sebelumnya dilakukan di laptop;
belum diulang sebagai fault injection board fisik pada Jetson. Autostart host
dua board, kestabilan setelah reboot, NTP, sensor riil, dan output thruster riil
belum dikualifikasi oleh deployment ini.

Autostart dan reboot kemudian diuji pada sesi lanjutan di
[panduan autostart](jetson_autostart.md). Bag dan hasil di bagian ini tetap
merupakan pengujian deployment manual sebelum tahap tersebut.

# Integrasi payload dan misi host — 2026-10-08

## Keputusan dan batas tahap ini

Dua paket pesan tetap terpisah: `tyrant_interfaces` untuk Teensy dan
`tyrant_payload_interfaces` untuk ESP. Firmware ESP sekarang ada di `firmware/esp`.
Schema ESP hanya ada di `ros2_ws/src/tyrant_payload_interfaces`, dirujuk lewat
symlink relatif dari `firmware/esp/extra_packages`. Salin repository secara lengkap
agar symlink tetap memiliki target, termasuk ketika menyiapkan build ESP.

`tyrant_mission_host` menjalankan koordinasi dan rekaman di laptop dahulu, kemudian
bisa dijalankan di container Jetson. Firmware Teensy tidak diubah; LMPC dan GUI
belum dibuat. Interface Teensy di firmware/host masih salinan yang sudah ada;
perubahan cara penyimpanan schema Teensy ditunda, dan kesamaan `.msg` diperiksa.

Kebijakan yang disepakati:

- Toleransi depth per titik dapat diatur, bukan ditetapkan ±1 m.
- Manual: daya sensor dikendalikan operator; rekaman dapat dimulai/dihentikan manual.
- Auto: sensor ON sepanjang misi (`throughout`) atau ON saat titik pengukuran (`at_point`).
- Pengumpulan memerlukan depth valid/fresh, dalam toleransi dan stabil; menghitung
  target sampel baru/valid per sensor, dengan batas waktu per titik.
- Sensor payload gagal: titik dapat tidak lengkap, lalu misi lanjut. State Teensy
  invalid/stale atau estimator tidak siap saat misi aktif langsung menyebabkan
  misi gagal, STOP dan request SAFE, termasuk selama gerak berbasis durasi.
- Planned XY hanya diisi bila tersedia dalam rencana; tidak dihitung dari effort/durasi.
- Rosbag dan CSV merekam sepanjang sesi, termasuk data invalid dan fase perjalanan.
- Konfigurasi misi serta tanda simulasi ikut tersimpan. Reset uptime/sequence payload
  dideteksi sebagai pergantian sesi perangkat yang diperkirakan, bukan boot-ID pasti.

## Cara koordinasi tanpa perubahan Teensy

Host mengirim **satu segmen gerak** melalui antrean misi Teensy. Untuk titik sampling,
segmen berisi langkah depth + WAIT dengan batas durasi. Ketika Teensy masuk WAIT,
host memeriksa stabilitas depth dan menghitung sampel. Setelah selesai/timeout,
host mengirim STOP, menunggu ACK, kemudian mengonfigurasi segmen berikutnya melalui
SAFE → IDLE → AUTO. Mission ID/step ID host tetap sama sepanjang sesi; indeks langkah
Teensy lokal segmen (0 gerak, 1 WAIT) disimpan juga dalam rosbag.

WAIT memakai depth/heading hold controller Teensy yang ada. Referensinya belum
secara eksplisit dikunci ke target depth oleh host: HIL perlu membuktikan hasilnya
cukup stabil dalam toleransi. Ini bukan LMPC, pause/resume misi firmware, atau kendali
posisi XY. Semua request penting menunggu ACK dengan request ID dan jenis perintah
cocok; timeout/reject menghentikan koordinasi. Pengelola misi lain/teleop tidak boleh
mengirim perubahan mode atau misi bersamaan dengan sesi host.

## Build laptop

```bash
cd /home/charisto/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tyrant_interfaces tyrant_payload_interfaces tyrant_sim tyrant_mission_host --symlink-install
source install/setup.bash
python3 /home/charisto/tyrant-simple/firmware/esp/scripts/check_host_interfaces.py
```

Jika CMake mengeluhkan cache path dari laptop/arsitektur lain, jangan salin build/install
ke mesin baru; salin source dan build di mesin tujuan. Folder ESP `host_ws/build` dan
`install` lama telah dipertahankan sebagai `*.before-relocation`, karena mengandung
path absolut lokasi lama. Overlay yang aktif sekarang adalah `ros2_ws/install`.

## Uji dua board fisik menggunakan data simulasi

Pastikan Teensy memakai **teensy41-hil**, ESP memakai **esp32-s3-sim**. Profil produksi
Teensy tetap tidak mengaktifkan AUTO tanpa konfigurasi thruster nyata.

Upload ESP dari terminal laptop, setelah menghentikan agent yang memegang port:

```bash
cd /home/charisto/tyrant-simple/firmware/esp
bash scripts/build.sh esp32-s3-sim
export PLATFORMIO_CORE_DIR="$PWD/.pio-core"
export PLATFORMIO_CACHE_DIR="$PLATFORMIO_CORE_DIR/.cache"
.pio-core/penv/bin/python -m platformio run -e esp32-s3-sim --target upload --upload-port /dev/tyrant-esp
```

Upload Teensy bila belum memakai HIL:

```bash
cd /home/charisto/tyrant-simple/firmware/teensy
pio run -e teensy41-hil --target upload --upload-port /dev/tyrant-teensy
```

Hentikan agent dan publisher heartbeat lama agar setiap board hanya punya satu agent
serta satu pemilik heartbeat. Jangan jalankan teleop pada pengujian misi host ini.
Di setiap terminal ROS:

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/microros_ws/install/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
```

Terminal A: plant HIL yang mengirim keadaan simulasi ke Teensy:

```bash
ros2 launch tyrant_sim hil_plant.launch.py
```

Terminal B: dua agent dan pengelola misi (belum memulai gerak):

```bash
ros2 launch tyrant_mission_host mission_host.launch.py \
  start_agents:=true \
  output_dir:=/home/charisto/tyrant-simple/ros2_ws/bags/missions
```

Node host otomatis mengirim heartbeat Teensy dan ESP 10 Hz. Perintah daya dan gerak
baru dikirim setelah service start. Jika agent sudah dijalankan sendiri, gunakan
`start_agents:=false` (default), bukan membuka port dua kali.

Terminal C: periksa kondisi sebelum start:

```bash
ros2 topic echo /tyrant/system/health --once
ros2 topic echo /tyrant/simple_state --once
ros2 topic echo /tyrant/payload_sim/communication/diagnostics --once
```

Host start memerlukan mode IDLE/SAFE serta telemetry Teensy fresh,
communication_healthy dan estimator_ready. Jika Teensy masih MANUAL, kembalikan
ke SAFE lewat perintah mode yang biasa sebelum memulai. `autonomy_ready` dapat
false sebelum host mengisi antrean; Teensy tetap memeriksa readiness saat request AUTO.

```bash
ros2 service call /tyrant/host/mission/start std_srvs/srv/Trigger '{}'
ros2 topic echo /tyrant/host/mission/status
```

Service start mengembalikan lokasi sesi. Contoh YAML bawaan menjalankan depth 1 m,
sampling, surge 10 detik, sway 5 detik, heading absolut -90°, depth 3 m dan sampling.
Heading adalah radian absolut, bukan perintah rotasi relatif terhadap heading awal.
Profil ESP simulasi dimulai ketika sensor pertama ON; skenario waktu 180 detiknya
belum dipicu oleh depth. Gangguan yang kebetulan terjadi saat sampling harus menghasilkan
status titik tidak lengkap sesuai kebijakan timeout.

Hentikan melalui service, bukan hanya menutup terminal:

```bash
ros2 service call /tyrant/host/mission/stop std_srvs/srv/Trigger '{}'
```

Host meminta STOP dan SAFE; konfirmasi kondisi board melalui telemetry. Jika proses
host hilang, heartbeat hilang dan mekanisme keselamatan Teensy tetap berlaku. SAFE
menghentikan propulsion normal; SAFE tidak menjamin kendaraan mempertahankan depth.
GUI belum ada. Misi host yang aktif tidak bergantung pada sesi GUI, tetapi tetap
bergantung pada proses host dan komunikasi Teensy.

## Parameter misi yang dapat diubah

Salin YAML contoh dari `ros2_ws/src/tyrant_mission_host/config/two_depth_hil.yaml`
ke file rencana sendiri. Berikan `plan:=/path/absolut/misi.yaml` saat launch.

- `tolerance`: rentang ±meter untuk depth, ±radian untuk heading, per langkah.
- `stable_s` dan `stable_span_m`: waktu depth bertahan dalam toleransi dan batas
  rentang perubahan depth selama stabilisasi. Dapat dioverride lewat `sampling` per langkah.
- `target_samples`: jumlah pembacaan baru/valid untuk setiap sensor terpilih.
- `sampling.timeout_s`: mencakup stabilisasi, kesiapan sensor, dan pengumpulan.
- `timeout_s` per langkah: batas waktu gerak menuju target.
- `sensor_policy`: `throughout` atau `at_point`; `sensors`: ID sensor terpilih.
- `planned_x/planned_y`: koordinat rencana opsional. Tidak ada field posisi aktual XY.

Nilai default (toleransi depth 0,1 m, stabilisasi 3 s, rentang perubahan 0,05 m,
3 sampel/sensor dan timeout sampling 40 s) hanya contoh pengujian yang dapat diatur,
bukan hasil tuning kendaraan. Daya ON menunggu validitas sensor; warm-up fisik EZO
belum diverifikasi. Pada akhir/stop misi, host meminta OFF untuk sensor yang dipilih.

## Rekaman manual dan keluaran

Saat tidak ada misi aktif:

```bash
ros2 service call /tyrant/host/recording/start std_srvs/srv/Trigger '{}'
ros2 service call /tyrant/host/recording/stop std_srvs/srv/Trigger '{}'
```

Rekaman manual tidak mengubah daya sensor atau mode Teensy. Host tetap mengirim
heartbeat selama hidup. Gunakan `publish_heartbeats:=false` hanya bila ada pemilik
heartbeat lain yang jelas.

Setiap sesi berisi:

- `session.json`: konfigurasi lengkap, session ID, jenis sesi, tanda simulasi dan hasil.
- `events.jsonl`: ACK daya, transisi fase, timeout, hasil titik dan indikasi reboot ESP.
- `samples.csv`: satu baris per kanal pada snapshot water quality, validitas, umur,
  depth saat diterima, estimasi depth terkait akuisisi, step dan kualifikasi titik.
- `bag/`: pesan asli kedua board, request gerak/daya, heartbeat dan status host.
  Monitoring daya dan seluruh telemetry yang didaftarkan disimpan dalam bag.

`COMPLETE` berarti urutan eksekusi selesai; bukan jaminan semua titik memiliki
data lengkap. `step_results` dan `all_sampling_points_complete` membedakan hasil
sampling lengkap dari titik yang diteruskan setelah timeout.

```bash
ros2 bag info /path/sesi/bag
```

Tidak ada penyamaan clock ESP dan Teensy. Perkiraan waktu akuisisi adalah waktu
penerimaan host dikurangi umur kanal; depth dicari pada history penerimaan host.
Latensi serial tidak dikoreksi, sehingga ini korelasi awal dengan batas freshness,
bukan sinkronisasi presisi. Nilai invalid tetap dicatat (CSV kosong untuk NaN), dan
hasil pengukuran berulang tidak dihitung ulang sebagai sampel baru. Power tiap sensor
masih berupa status logis MOSFET; INA mengukur total rel sensor.

## Jetson setelah pengujian laptop

Paket host yang sama dapat dibangun di workspace container `/ws`; gunakan build
sequential sesuai batas RAM Jetson. Dockerfile companion telah mencakup dua paket
baru, tetapi image/container Jetson belum dibangun ulang atau diubah dalam tahap ini.

```bash
# Di dalam container Jetson, setelah source /opt/ros/humble/setup.bash
cd /ws
CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 colcon build \
  --packages-select tyrant_payload_interfaces tyrant_mission_host \
  --executor sequential --symlink-install
source /ws/install/setup.bash
```

Interface Teensy dan micro_ros_agent harus sudah tersedia seperti deployment sebelumnya.
Pasang aturan udev kedua board pada **host Jetson**, bukan container. Pastikan alias
terlihat di container. Jangan menjalankan agent Teensy lama bersama agent baru pada
port yang sama. Gunakan launch dengan `start_agents:=false` bila supervisor lama masih
menjalankan agent Teensy, lalu jalankan agent ESP terpisah. Untuk uji penuh dua agent
melalui launch, gunakan lingkungan development tanpa supervisor lama yang memegang port.

Prefix hardware ESP nantinya `payload_namespace:=/tyrant/payload`; set
`teensy_simulated:=false` hanya ketika Teensy benar-benar menggunakan sensor fisik.
Label simulasi pada metadata bersumber dari pilihan deployment ini.

Webcam, GUI, LMPC, timestamp tersinkron, dan handshake firmware sampling belum
termasuk implementasi ini. Menghilangkan pergantian SAFE antarsegmen atau menambahkan
hold target depth yang eksplisit memerlukan perubahan Teensy yang dibahas dahulu.

## Hasil verifikasi

Update 10 Oktober: host diperbaiki setelah uji plant dihentikan di tengah surge.
Kini state/health diperiksa pada callback, timer, ACK, status selesai dan payload.
Tidak ada perubahan firmware. [Catatan gangguan dan perbaikan](dokumentasi%20dan%20PRD/Uji_Plant_HIL_Berhenti_dan_Perbaikan_Host_2026-10-10.md).

Log build, uji dan fingerprint source disimpan di
[validation/mission_host_2026-10-08](validation/mission_host_2026-10-08/result.json).

- Build dua paket host dan import keenam message payload/typesupport: PASS.
- Uji logika host dan regresi teleop/sim: PASS (28 test).
- ROS lokal dengan endpoint tiruan: PASS; start service, heartbeat kedua board,
  ACK daya bergantian, sampling tiap sensor, dua langkah host, bag/CSV terbaca,
  serta rekaman manual. Uji ini tidak mengakses USB dan tidak memodelkan dinamika kendaraan.
- Kebijakan daya per titik dan sensor gagal: PASS dengan endpoint tiruan; titik
  ditandai tidak lengkap setelah timeout, lalu langkah gerak berikutnya tetap selesai.
- Build ESP hardware/simulasi setelah pemindahan: PASS; native ESP dua profil PASS.
- Update 9 Oktober: dua board diuji bersama memakai state/sensor simulasi. Rosbag
  berhasil merekam keduanya, tetapi sampling depth belum lengkap karena depth
  menetap di luar toleransi. Deployment paket host baru ke Jetson belum dilakukan.
  Hasil rinci ada di [catatan lanjutan 9 Oktober](dokumentasi%20dan%20PRD/Integrasi_ESP_Teensy_HIL_dan_Rosbag_2026-10-09.md).

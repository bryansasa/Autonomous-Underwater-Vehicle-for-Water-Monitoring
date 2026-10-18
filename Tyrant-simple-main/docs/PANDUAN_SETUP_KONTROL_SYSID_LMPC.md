# Panduan setup Tyrant: hardware, kontrol manual, tuning, SysID dan LMPC

Tanggal pemeriksaan source: **13 Oktober 2026 WIB**. Panduan ini menjadi pegangan utama sebelum uji GUI dengan micro-ROS asli. Status di bawah berasal dari source repository, bukan pengujian hardware baru. Pada penyusunan dokumen ini tidak dilakukan upload, aktivasi motor atau perubahan firmware.

## 1. Apakah pekerjaan kode tinggal mengganti pin?

**Belum.** Komunikasi, estimator sederhana, kontrol manual stabil, misi, perekaman dan pipeline SysID sudah tersedia. Kendaraan riil masih memerlukan konfigurasi geometri, karakterisasi actuator, validasi sensor dan implementasi LMPC.

| Bagian | Sudah ada | Masih diperlukan |
|---|---|---|
| Teensy/micro-ROS | Agent serial, heartbeat, mode, telemetry, failsafe | Validasi ulang setelah sensor/ESC riil dipasang |
| ESP32-S3 | Dua bus I2C, EZO EC/pH/DO, suhu analog, dua INA226, MOSFET terpisah | Pin final, model/kalibrasi suhu, kalibrasi sensor dan pengujian rail riil |
| Estimator | Roll/pitch, yaw+bias, depth dari tekanan | Mounting aktual, kalibrasi magnetometer pada robot terakit, referensi pressure dan density |
| Kontrol sederhana | Roll/pitch/yaw **PD**, depth **P**, surge/sway effort langsung | Tuning wet; tidak ada depth Kd/Ki atau velocity hold |
| Allocator | TAM dan damped least-squares, 8 kanal | Geometri produksi dan konsistensi skala wrench/thrust |
| PWM | Backend dan mapper pulse tersedia | Pin final, arah, neutral/deadband/range, karakterisasi serta profil hardware tervalidasi |
| Tes individual thruster | Belum ada endpoint per-thruster yang siap dipakai | Prosedur bench dan jalur tes terisolasi dengan timeout/neutral/batas output |
| SysID | START/STOP, sample 20 Hz, bag, excitation HIL | Eksperimen wet dan model yang tervalidasi; preprocessing/identification tooling final |
| LMPC | **Belum ada solver/controller/model terpasang** | Model, sintesis, implementasi, pengujian waktu komputasi dan fallback |
| GUI | Mockup dan gateway snapshot read-only | Frontend live, command/ACK, ownership input, sampling host yang diperluas, kamera |

Urutan utama: **sensor → actuator/geometri → manual dan P/PD → SysID wet → validasi model → LMPC → kualifikasi kontrol GUI**. GUI telemetry read-only dapat diuji lebih awal; tidak perlu menunggu LMPC untuk melihat data asli.

## 2. Profil firmware dan pemilik proses

### 2.1 Pilih profil secara eksplisit

| Profil | Sensor/state | Actuator | Penggunaan |
|---|---|---|---|
| Teensy `teensy41` | Sensor riil | Backend DISABLED | Bring-up sensor; tidak menghasilkan PWM fisik |
| `teensy41-mock-thrusters` | Sensor riil | Mock + geometri sintetis | Tes jalur software; tidak untuk motor |
| `teensy41-hil` | State dari plant ROS | Mock + geometri sintetis | Tes misi/SysID HIL; bukan model robot riil |
| `teensy41-pwm-skeleton` | Sensor riil | Kode PWM aktif, pin default `0xFF` | Compile check; default init gagal tertutup, bukan profil motor siap pakai |
| ESP `esp32-s3-sim` | Sintetis | Kebijakan power simulasi | Namespace `/tyrant/payload_sim` |
| ESP `esp32-s3-devkitm-1` | Driver sensor riil | GPIO MOSFET | Namespace `/tyrant/payload` |

Mengisi pin pada `teensy41` saja **tidak mengaktifkan PWM**. Mengisi pin tanpa geometri produksi juga belum membuat allocator siap. Jangan memakai geometri sintetis HIL untuk chassis riil.

### 2.2 Dua cara menjalankan sistem — pilih satu

**Cara A: laptop, proses manual.** Dua agent jika kedua board terpasang; satu pemilik heartbeat Teensy; heartbeat ESP terpisah. Teleop atau excitation menjadi pemilik command manual, tidak keduanya.

**Cara B: Jetson autostart.** Container `tyrant-mission` mengelola dua agent, host misi, heartbeat kedua board dan, pada konfigurasi bench lama, plant HIL. Jangan menjalankan salinan agent/host/plant/heartbeat dari laptop pada domain yang sama. Untuk manual dari laptop, teleop harus `publish_heartbeat=false`, sementara host tetap IDLE dan tidak mengirim misi.

Excitation SysID yang tersedia selalu menerbitkan heartbeat Teensy dan meminta MANUAL. Jalankan hanya pada stack HIL terisolasi tanpa host/teleop/heartbeat lain. Belum ada parameter untuk menonaktifkan heartbeat excitation.

## 3. Persiapan laptop, USB dan Jetson

### 3.1 Terminal laptop — lingkungan ROS

Jalankan di **setiap terminal laptop baru** yang memakai ROS:

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/microros_ws/install/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
```

Workspace agent laptop yang ditemukan pada pemeriksaan ini bernama `microros_ws`. Jika lokasi agent berbeda, source lokasi install yang benar; jangan copy `build/install` x86 laptop ke Jetson ARM64.

Build source host bila berubah, bukan setiap akan menyalakan robot:

```bash
cd /home/charisto/tyrant-simple/ros2_ws
colcon build --packages-select tyrant_interfaces tyrant_payload_interfaces tyrant_teleop tyrant_sim tyrant_mission_host --symlink-install
source install/setup.bash
ros2 interface show tyrant_interfaces/msg/ManualCommand
ros2 interface show tyrant_payload_interfaces/msg/SensorPowerStatus
```

### 3.2 Alias USB tetap — terminal HOST, bukan container

Identitas board yang sebelumnya diverifikasi:

| Board | Serial | Alias |
|---|---|---|
| ESP32-S3 | `28:84:85:8B:BD:38` | `/dev/tyrant-esp` |
| Teensy | `13843280` | `/dev/tyrant-teensy` |

Di laptop, pasang aturan yang tersedia jika belum ada:

```bash
sudo install -m 0644 /home/charisto/tyrant-simple/firmware/esp/deployment/99-tyrant-esp.rules /etc/udev/rules.d/99-tyrant-esp.rules
sudo install -m 0644 /home/charisto/tyrant-simple/firmware/esp/deployment/99-tyrant-teensy.rules /etc/udev/rules.d/99-tyrant-teensy.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty --action=add
udevadm settle
```

Verifikasi setelah cabut/pasang atau reboot:

```bash
for board in /dev/tyrant-esp /dev/tyrant-teensy; do
  echo "$board"
  readlink -f "$board"
  udevadm info --query=property --name="$board" | grep '^ID_SERIAL_SHORT='
done
```

`ttyACM0`/`ttyACM1` boleh tertukar. Yang wajib tetap cocok adalah serial melalui alias. Di Jetson, aturan dipasang di **host Jetson** dari salinan file yang sama setelah ID diverifikasi. Container autostart melihatnya sebagai `/host-dev/tyrant-esp` dan `/host-dev/tyrant-teensy`. Aturan alias tidak menambah izin port; periksa group `dialout` bila permission denied.

### 3.3 Upload — laptop, agent pemilik port dihentikan dahulu

Upload HIL untuk latihan tanpa motor:

```bash
cd /home/charisto/tyrant-simple/firmware/teensy
pio run -e teensy41-hil --target upload --upload-port /dev/tyrant-teensy
```

Upload Teensy sensor riil, **PWM tetap disabled**:

```bash
cd /home/charisto/tyrant-simple/firmware/teensy
pio run -e teensy41 --target upload --upload-port /dev/tyrant-teensy
```

ESP simulasi:

```bash
cd /home/charisto/tyrant-simple/firmware/esp
.pio-core/penv/bin/python -m platformio run -e esp32-s3-sim --target upload --upload-port /dev/tyrant-esp
```

ESP sensor riil memakai perintah yang sama dengan environment `esp32-s3-devkitm-1`. Python virtual environment ESP hanya menentukan lokasi PlatformIO; fungsinya sama dengan `pio`. Jika file executable tersebut tidak ada, gunakan instalasi PlatformIO yang tersedia. Jangan menjalankan serial monitor dan agent pada port yang sama.

Jika library micro-ROS cached memakai kapasitas entity lama, hanya saat itu lakukan `pio run -e teensy41-hil -t clean_microros`, lalu build/upload ulang environment tersebut. Ini bukan langkah harian.

### 3.4 Terminal SSH HOST Jetson — perintah harian

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker logs --tail 50 tyrant-mission
docker inspect tyrant-mission --format '{{json .Config.Env}}'
timedatectl status
docker exec -it tyrant-mission bash
```

**Di dalam container:**

```bash
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
source /mission_ws/install/setup.bash
ros2 node list
ros2 topic echo /tyrant/host/mission/status std_msgs/msg/String --once --full-length
ros2 topic echo /tyrant/system/health --once
```

Container HIL lama tidak berubah menjadi hardware hanya dengan upload firmware. Sebelum beralih, hentikan container secara normal, simpan konfigurasi lama, lalu siapkan ulang dengan `TYRANT_HIL_PLANT=false`, `TYRANT_TEENSY_SIMULATED=false`, namespace `/tyrant/payload` dan **plan hardware yang tervalidasi**. Script `start_mission_autostart.sh` menolak nama container yang sudah ada; jangan mengeksekusinya di atas container lama atau memakai default plan HIL sebagai misi hardware. Perubahan environment lewat `docker exec` tidak mengubah supervisor aktif.

Tidak perlu build ulang agent yang sudah bekerja. Package Tyrant dibuild dari source pada ARM64 jika source berubah. VSC/Remote SSH tidak menjadi syarat.

## 4. Konfigurasi sensor dan validasi sebelum motor

### 4.1 File yang perlu disesuaikan

| File | Isi yang harus diverifikasi |
|---|---|
| `firmware/teensy/include/config/sensor_config.h` | HWT905 baud/mounting, freshness, density air, cadence pressure |
| `firmware/teensy/src/sensors/sensor_hardware.cpp` | HWT905 menggunakan `Serial1`; ubah binding bila kabel UART berubah |
| `firmware/teensy/include/config/simple_estimator_config.h` | Kalibrasi magnetometer dan setting estimator |
| `firmware/esp/include/payload_config.h` | Semua GPIO, address I2C, polaritas MOSFET, shunt dan konversi suhu |

Mounting HWT905 saat ini: sensor X→BODY +X, Y→BODY −Y, Z→BODY −Z, baud 9600. Verifikasi terhadap pemasangan aktual; jangan menyalin tanda itu jika orientasi board berubah. FullDepth driver saat ini memakai keluarga MS5837-30BA dan Wire default; cocokkan sensor yang benar-benar terpasang. Density default 1025 kg/m³; sesuaikan medium uji, jangan menyamakan density air tawar dengan laut.

Pin ESP sementara: I2C payload SDA8/SCL9; power SDA10/SCL11; ADC suhu7; MOSFET EC4/pH5/suhu6/DO15, active-high. Dua INA boleh sama-sama address `0x40` karena berada di bus berbeda. Shunt rail sensor R100 = 0,1 Ω; shunt thruster 200 A/75 mV = 0,000375 Ω. Rating shunt bukan batas arus aman keseluruhan rangkaian. `TEMPERATURE_CALIBRATION_CONFIRMED=false`: **suhu riil tetap belum valid** sampai model/rangkaian dan konversinya diverifikasi. Jangan mengubah flag ke true hanya agar GUI menampilkan angka.

### 4.2 Menyalakan stack laptop manual

**Terminal A**, setelah source: agent Teensy.

```bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/tyrant-teensy -b 115200 -v4
```

**Terminal B**, setelah source: agent ESP.

```bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/tyrant-esp -b 115200 -v4
```

**Terminal C:** heartbeat Teensy untuk tahap sensor tanpa teleop.

```bash
ros2 topic pub --rate 10 /tyrant/host_heartbeat std_msgs/msg/UInt32 '{data: 1}'
```

**Terminal D:** heartbeat ESP riil.

```bash
ros2 topic pub --rate 10 /tyrant/payload/host_heartbeat std_msgs/msg/UInt32 '{data: 1}'
```

Untuk ESP sim, ganti `/tyrant/payload` menjadi `/tyrant/payload_sim` pada semua perintah payload. Board memeriksa umur penerimaan heartbeat; nilai konstan pada perintah bench ini bukan timestamp. Saat teleop mulai dan menjadi pemilik heartbeat Teensy, hentikan Terminal C. Pada Jetson autostart, semua agent/heartbeat ini sudah dimiliki supervisor/host dan tidak dijalankan lagi.

Periksa pada terminal pengamatan:

```bash
ros2 topic echo /tyrant/communication/diagnostics --once
ros2 topic echo /tyrant/system/health --once
ros2 topic echo /tyrant/simple_state --once
ros2 topic echo /tyrant/sensors/imu --once
ros2 topic echo /tyrant/sensors/pressure --once
ros2 topic echo /tyrant/payload/communication/diagnostics --once
```

Diamkan IMU saat startup untuk inisialisasi estimator. Komunikasi sehat tidak berarti estimator siap. Tanpa pressure sensor, depth invalid adalah kondisi yang benar; jangan menggantinya dengan depth sintetis pada build hardware.

### 4.3 Set Surface berbeda dari perintah naik

Buka subscriber status di terminal pengamatan **sebelum request**, karena ACK dapat hanya terbit ketika request diproses:

```bash
ros2 topic echo /tyrant/depth/reference/status
```

Saat kendaraan di permukaan, pressure valid dan mode IDLE, kirim dari terminal command:

```bash
ros2 topic pub --once /tyrant/mode/request tyrant_interfaces/msg/ModeRequest '{request_id: 101, requested_mode: 1}'
ros2 topic echo /tyrant/mode/status --once
ros2 topic pub --once /tyrant/depth/reference/request tyrant_interfaces/msg/DepthReferenceRequest '{request_id: 102, command: 1}'
```

Periksa request_id/accepted/reason dari status, bukan hanya keberhasilan publish. Set Surface menetapkan nol pressure; tidak menjalankan gerak menuju permukaan. Amati depth saat sensor turun dengan jarak yang diketahui: tanda positif harus ke bawah. Goyangkan robot perlahan untuk verifikasi tanda roll/pitch/yaw dan arah kompas sebelum motor aktif.

### 4.4 Sensor payload dan power

Buka echo status terlebih dahulu di terminal terpisah:

```bash
ros2 topic echo /tyrant/payload/sensor_power/status
```

Kemudian request satu sensor (EC=1, pH=2, suhu=3, DO=4):

```bash
ros2 topic pub --once /tyrant/payload/sensor_power/request tyrant_payload_interfaces/msg/SensorPowerRequest '{request_id: 201, sensor_id: 1, enable: true}'
ros2 topic echo /tyrant/payload/water_quality --once
ros2 topic echo /tyrant/payload/power/sensors --once
ros2 topic echo /tyrant/payload/power/thruster --once
```

Cocokkan ACK 201. Jika heartbeat ESP tidak sehat, ON ditolak reason 5; OFF tetap diizinkan jika transport menerima perintah. Setelah ON tunggu warm-up dan pembacaan baru. GPIO ON bukan bukti rail listrik terukur; cek INA dan wiring. Nilai NaN/invalid saat sensor belum ada adalah benar.

Request OFF:

```bash
ros2 topic pub --once /tyrant/payload/sensor_power/request tyrant_payload_interfaces/msg/SensorPowerRequest '{request_id: 202, sensor_id: 1, enable: false}'
```

**Lulus tahap sensor:** identitas port tepat; counter disconnect tidak terus naik pada kondisi normal; heartbeat sehat; validity sesuai sensor aktual; arah state benar; ACK daya dan pengukuran INA cocok. Magnetometer dikalibrasi kembali pada robot terakit, jauh dari gangguan yang berbeda dari kondisi operasi.

## 5. Tes thruster: yang bisa dilakukan sekarang dan gerbang hardware

### 5.1 Tes software HIL sekarang

Upload Teensy HIL dan nyalakan agent. Saat belum ada plant lain:

```bash
ros2 launch tyrant_sim hil_plant.launch.py
```

Lanjutkan teleop pada bagian 6, amati:

```bash
ros2 topic echo /tyrant/control/wrench_request
ros2 topic echo /tyrant/control/thruster_command
ros2 topic echo /tyrant/actuation/status
```

Harapan: backend mock, physical_output_enabled false, command virtual berubah sesuai input. SAFE/stale harus netral. Ini tidak menguji kabel, ESC, motor atau thrust riil.

### 5.2 Sebelum tes motor fisik — pekerjaan yang masih harus dikerjakan

1. Isi `docs/thruster_geometry_template.csv` untuk delapan motor: posisi r terhadap origin body yang dipilih, meter, dan arah gaya positif d unit vector BODY-FRD. Tetapkan nomor1–8 terhadap index0–7. Salin nilai terverifikasi ke `loadProductionGeometry()` di `thruster_config.h` dan ubah keberhasilan load setelah data benar. CSV tidak dibaca otomatis saat runtime.
2. Verifikasi TAM: tiap kolom berasal dari `[d; r×d]`. Periksa controllability pada axis yang memang dibutuhkan; jangan menganggap semua konfigurasi punya rank6.
3. Isi pin PWM, neutral/reverse/forward, deadband dan inversion per kanal. Angka 1100/1500/1900 µs dan deadband0,05 saat ini adalah placeholder. Cocokkan ESC dan ukur sinyal, jangan menganggap arah/range universal.
4. Tentukan hubungan command→pulse→thrust. Mapper saat ini linear dengan deadband, allocator normalized; belum ada tabel thrust riil/Newton. Konsistensi skala gaya/momen dan thrust perlu diselesaikan sebelum mengklaim allocator fisik terkalibrasi atau model LMPC physical.
5. Siapkan profil hardware yang eksplisit dan uji neutral saat boot, invalid command, SAFE dan watchdog. Skeleton bukan persetujuan hardware. Validasi latency loop dengan pembacaan pressure blocking dan watchdog backend100 ms; jangan memperpanjang timeout hanya untuk menutupi loop yang macet.
6. Buat/validasi jalur bench individual yang membatasi kanal, amplitudo, durasi dan timeout, terpisah dari allocator kendaraan. **Belum ada perintah ROS siap pakai untuk “nyalakan motor nomor3”.** Mempublish ThrusterCommand tidak otomatis menggerakkan motor: topic tersebut adalah telemetry output firmware.

Tes motor dilakukan sesuai kebutuhan pendinginan/submersion motor aktual, dengan kendaraan tertahan dan pemutus daya fisik dapat dijangkau. SAFE software tidak menggantikan pemutus daya. Mulai dari sinyal neutral dengan daya motor terisolasi; baru lanjut uji terbatas tiap motor setelah jalur bench disiapkan.

Catat hasil tiap motor:

| Motor/index | Pin/ESC | Neutral/range/deadband | Arah gaya + | V/A/W | Thrust +/− bila diukur | Hasil timeout |
|---|---|---|---|---|---|---|
| 1/0 … 8/7 | Isi aktual | Isi aktual | Cocok d | Ukur | Ukur, jangan tebak | Netral/fault |

**Lulus actuator:** semua kanal teridentifikasi, neutral benar, arah benar, geometri/mapping valid, tidak ada fault/reject berulang dan failsafe terukur. Angka software normalized bukan persentase thrust riil. Tidak lanjut manual wet atau SysID wet jika gerbang ini belum selesai.

## 6. Tes manual control

### 6.1 Mapping controller laptop

Controller USB/Bluetooth harus terdeteksi sebelum menilai robot:

```bash
ros2 run joy joy_node
```

Di terminal lain:

```bash
ros2 run tyrant_teleop tyrant_joy_probe
```

Catat axis/button nyata, ubah `ros2_ws/src/tyrant_teleop/config/ps_controller.yaml`, lalu rebuild paket teleop. Hentikan kedua probe sebelum launch gabungan. Tidak adanya `/dev/input/js0` saja belum membuktikan controller tidak bisa dipakai joy/SDL; lihat hasil `/joy` dan probe.

Default yang harus diverifikasi: leftY surge, leftX sway, rightX yaw; R2 turun/L2 naik; L1 deadman; Cross MANUAL, Square IDLE, Circle SAFE, Triangle Set Surface. Roll/pitch stick tidak diaktifkan default, robot auto-level.

### 6.2 Menjalankan

**Stack laptop manual:** hentikan publisher heartbeat Teensy terpisah; teleop default menjadi pemiliknya.

```bash
ros2 launch tyrant_teleop ps_teleop.launch.py
```

**Host Jetson sudah aktif, controller ada di laptop:** untuk menghindari heartbeat duplikat, pakai dua terminal laptop setelah source:

```bash
ros2 run joy joy_node --ros-args -p autorepeat_rate:=20.0 -p deadzone:=0.03
```

```bash
ros2 run tyrant_teleop tyrant_teleop --ros-args --params-file /home/charisto/tyrant-simple/ros2_ws/src/tyrant_teleop/config/ps_controller.yaml -p publish_heartbeat:=false
```

Gunakan ROS_DOMAIN_ID yang sama, konektivitas DDS dua arah dan host mission IDLE. Jangan memakai jalur ini bersamaan dengan excitation atau misi aktif. Ini teleop ROS laptop, terpisah dari Gamepad browser GUI.

### 6.3 Urutan uji

1. Mulai IDLE; cek health/state/backend. Pada HIL nyalakan plant; pada hardware jangan nyalakan plant.
2. Minta MANUAL; lihat accepted dan actual mode. Tanpa deadman, tidak boleh ada stream gerak aktif.
3. Tahan deadman, uji satu axis dalam amplitudo kecil yang sesuai batas bench/wet. Surge + berarti maju, sway + kanan, heave + lebih dalam, yaw + putar kanan.
4. Heave/yaw adalah **laju perubahan referensi**, bukan input PWM langsung. Saat stick netral tetapi deadman masih aktif, depth/heading terakhir di-hold bila state valid; roll/pitch tetap auto-level.
5. Lepas deadman: teleop mengirim netral sekali lalu berhenti, command menjadi stale. Ini berbeda dari netral stick dengan deadman aktif. Uji nyata bahwa output akhirnya netral; jangan menilai dari satu message wrench saja.
6. Uji SAFE, controller putus, agent/heartbeat hilang dan invalid state satu per satu. Pantau mode, fault, thruster command dan PWM yang diterapkan. Reconnect tidak boleh dianggap resume gerak otomatis.

Teensy manual timeout250 ms, teleop joy timeout0,20 s, SAFE timeout1 s; backend watchdog100 ms. Ukur perilaku gabungan dari bag/sinyal; jangan menjumlahkan atau menyamakan timeout ini tanpa bukti.

Stop software dari terminal yang masih tersambung:

```bash
ros2 topic pub --once /tyrant/mode/request tyrant_interfaces/msg/ModeRequest '{request_id: 301, requested_mode: 4}'
ros2 topic echo /tyrant/mode/status --once
ros2 topic echo /tyrant/actuation/status --once
```

Mode4=SAFE, bukan depth hold. Kebijakan EMERGENCY/controlled surface berbeda; jangan mengujinya pertama kali bersama tes manual motor.

## 7. Tuning kontrol sederhana yang sekarang ada

### 7.1 Parameter dan persamaan aktual

Edit `firmware/teensy/include/config/control_config.h`; tuning masih **compile-time**, belum ada API runtime/gain GUI.

| Axis | Persamaan normalized wrench | Default development |
|---|---|---|
| Depth | Z = clamp(Kp × (depth_ref − depth)) | Kp0,80; **tanpa Kd/Ki** |
| Roll | K = clamp(Kp × wrap(roll_ref − roll) − Kd × p) | Kp2,00/Kd0,35 |
| Pitch | M = clamp(Kp × (pitch_ref − pitch) − Kd × q) | Kp2,00/Kd0,35 |
| Yaw | N = clamp(Kp × wrap(yaw_ref − yaw) − Kd × r) | Kp1,50/Kd0,25 |
| Surge/sway | X/Y = effort setelah deadzone | Tidak ada velocity/position feedback |

Angle radian, rate rad/s, depth meter; output normalized, bukan Newton/Nm. Damping yaw memakai gyro BODY yang dikoreksi fixed bias saat inisialisasi; bias yaw KF disimpan terpisah, bukan otomatis dikurangkan lagi pada term Kd. max depth rate0,25 m/s, yaw slew45°/s, roll/pitch reference±15°, reference depth0–10 m adalah batas development, bukan izin operasi10 m.

### 7.2 Prosedur tuning wet

1. Tetapkan konfigurasi ballast/trim, geometri, actuator, density dan sensor yang sama sepanjang eksperimen. Selesaikan tanda actuator/sensor terlebih dahulu; tanda salah tidak diperbaiki dengan gain negatif.
2. Simpan salinan config awal beserta firmware revision/hash. Rekam state, wrench, command actuator, status dan power.
3. Pilih gain awal konservatif berdasarkan karakterisasi actual robot, bukan langsung menganggap default aman. Ubah satu parameter per percobaan; tiap perubahan build/upload ulang profil hardware yang tervalidasi. Hentikan agent saat upload.
4. Tuning roll/pitch pada sudut kecil di sekitar trim, lalu yaw. Naikkan Kp bertahap sesuai respons, atur Kd untuk meredam osilasi. Damping memakai gyro sehingga noise dan delay perlu diperhatikan. Hindari tuning dengan keluaran terus saturated atau geometri salah.
5. Depth baru diuji setelah pressure/zero valid. Gunakan perubahan depth kecil dan catat settling/overshoot/steady offset. Karena hanya P, offset buoyancy dapat tetap ada. Jika butuh damping/feedforward/integral, itu **pekerjaan kode baru**, bukan mengganti pin atau mengisi depth_kd yang belum tersedia.
6. Uji axis terpisah lalu kombinasi. Roll/pitch/yaw/depth dapat berkopel lewat allocator; hasil satu axis belum menjamin kombinasi baik.

Tiap percobaan catat: gain, reference/input, overshoot, settling time, error steady, noise, saturation/residual, V/A dan fault. Tetapkan kriteria penerimaan berdasarkan kemampuan robot; jangan menetapkan hasil numerik seolah sudah terbukti. Gain akhir P/PD dipertahankan sebagai baseline/fallback sebelum LMPC.

## 8. SysID: perekaman, eksperimen dan pemeriksaan hasil

### 8.1 Latihan HIL sekarang

Gunakan Teensy HIL dan agent aktif, tetapi hentikan teleop, plant/host/heartbeat lain. Helper akan menjalankan plant dan excitation sendiri:

```bash
cd /home/charisto/tyrant-simple
./companion/jetson/run_hil_sysid.sh 1001 step_yaw 0.25 12
```

Ini contoh HIL, **bukan amplitudo rekomendasi motor riil**. Helper memberi metadata `hil=true`, `validated_vehicle_model=false`. Dataset ini hanya membuktikan jalur software/rekaman; jangan dipakai sebagai model hydrodynamics kendaraan.

Profile tersedia: step_surge/sway/heave/roll/pitch/yaw; PRBS keenam axis; chirp_yaw. Semua PRBS dan chirp memakai profile_id10: nama/parameter lengkap wajib masuk metadata. Multisine belum ada. Excitation otomatis belum dikualifikasi sebagai prosedur wet dan belum punya guard hardware terpisah; jangan sekadar mengganti firmware lalu menjalankan contoh HIL di air.

### 8.2 SysID wet melalui kontrol manual yang sudah tervalidasi

Prasyarat: actuator/manual/failsafe wet lulus, state yang digunakan valid, satu pemilik command/heartbeat, batas eksperimen disepakati. Untuk awal, gunakan rangkaian input kecil terencana lewat teleop; otomatisasi wet memerlukan review jalur excitation terlebih dahulu.

**Terminal recorder**, sesudah source, mulai bag sebelum START agar ACK terekam:

```bash
mkdir -p ~/tyrant_sysid
session_dir="$HOME/tyrant_sysid/wet_e2001_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$session_dir"
ros2 bag record -o "$session_dir/bag" \
  /tyrant/sysid/sample /tyrant/sysid/status \
  /tyrant/manual/command /tyrant/control/wrench_request \
  /tyrant/control/thruster_command /tyrant/actuation/status \
  /tyrant/simple_state /tyrant/sensors/imu /tyrant/sensors/pressure \
  /tyrant/mode/status /tyrant/system/health \
  /tyrant/communication/diagnostics /tyrant/payload/power/thruster
```

**Terminal status**, buka sebelum START/STOP agar ACK tidak terlewat:

```bash
ros2 topic echo /tyrant/sysid/status
```

**Terminal command**, ID contoh experiment2001/profile6 untuk yaw:

```bash
ros2 topic pub --once /tyrant/sysid/control tyrant_interfaces/msg/SysIdControl '{request_id: 401, command: 1, experiment_id: 2001, profile_id: 6}'
```

Pastikan accepted=true, active=true dan experiment_id2001. START recorder SysID sendiri tidak memulai gerakan. Catat netral awal, excitation terencana dan netral akhir. Setelah selesai hentikan sesi, minta SAFE, baru Ctrl+C recorder:

```bash
ros2 topic pub --once /tyrant/sysid/control tyrant_interfaces/msg/SysIdControl '{request_id: 402, command: 0, experiment_id: 2001, profile_id: 6}'
ros2 topic pub --once /tyrant/mode/request tyrant_interfaces/msg/ModeRequest '{request_id: 403, requested_mode: 4}'
ros2 topic echo /tyrant/mode/status --once
```

Di terminal recorder yang sama setelah Ctrl+C:

```bash
ros2 bag info "$session_dir/bag"
```

Helper `run_sysid_session.sh 2001 6` juga tersedia untuk START/record/STOP, tetapi daftar topiknya belum mencakup seluruh telemetry PWM/power di atas. SysIdSample sudah memuat delapan actuator command normalized; sample itu bukan measured thrust atau pulse_us. Pakai daftar eksplisit di atas jika ingin evidence actuator lengkap.

### 8.3 Metadata eksperimen wajib

Simpan file catatan di sebelah bag: `hil=false`, profile name, experiment ID, amplitudo/durasi/pola aktual, gain P/PD, versi pin/geometri/ESC/thrust, firmware/source revision, batas output, state valid yang dipakai, massa/ballast/trim, sensor calibration, medium/density, tether, V baterai dan kejadian fault. Jangan menulis `validated_vehicle_model=true` sebelum validasi independen selesai.

### 8.4 Apa yang bisa diidentifikasi dengan sensor saat ini?

Roll/pitch/yaw dan depth memiliki feedback. Kandidat model awal: heave/depth, yaw/rate serta attitude yang perlu dipertahankan. Heave velocity belum merupakan state estimator nyata; jika diperlukan, perlu observer/filter tervalidasi dengan noise/delay yang dicatat.

Surge/sway velocity dan posisi XY **tidak tersedia**. Command surge/sway dapat dicatat, tetapi model kecepatan/posisinya tidak dapat divalidasi hanya dari durasi command atau double integration IMU. Tambahkan pengukuran eksternal yang tervalidasi jika hendak mengidentifikasi/mengendalikan gerak XY. Planned XY tetap planned, bukan posisi aktual.

Eksperimen melalui stabilized controller adalah closed-loop SysID. Stick heave/yaw mengubah reference; input plant harus berasal dari **actuator setelah allocator**, bukan stick saja. Pilih teknik identifikasi closed-loop yang menangani korelasi input/noise atau eksperimen tambahan yang tervalidasi; fitting naive stick→yaw bukan model actuator→vehicle.

### 8.5 Pemeriksaan bag sebelum fitting

- ID/status benar, sample ada, mode/propulsion sesuai fase eksperimen.
- Sampling SysID20 Hz bukan berarti IMU/pressure20 Hz: HWT sekitar10 Hz, pressure cadence5 Hz. Hindari menghitung snapshot state berulang sebagai observasi independen.
- Timestamp uptime board bukan UTC. Periksa jeda/drop/latency, urutan sample, reset dan alignment input/output.
- Exclude periode invalid, reboot, fault atau saturasi yang tidak sesuai rancangan identifikasi; simpan data mentah utuh dengan penanda alasan.
- Gunakan excitation yang cukup informatif pada band yang terukur; jangan memilih chirp lebih cepat dari kemampuan sensor/loop.
- Pisahkan sesi untuk fitting dan validasi. Bandingkan prediksi pada data baru, residual, coupling dan sensitivitas terhadap battery/load/tether.

Belum tersedia satu command repository untuk menghasilkan model LMPC tervalidasi dari bag secara otomatis. Tahap preprocessing, fitting dan validasi perlu dibangun, disimpan versinya dan diperiksa.

## 9. Implementasi LMPC — pekerjaan berikutnya, bukan fitur yang sudah ada

### 9.1 Sepakati model dan lokasi kontrol

Usulan awal mengikuti arsitektur repository: reduced LMPC di Teensy, menggantikan penghasil wrench sederhana secara terkontrol, sementara safety/mode/allocator/PWM tetap menjadi pemilik gate. ESP tetap payload; Jetson menangani plan/recording/GUI. Pilihan lokasi final harus dibuktikan oleh kemampuan solver/latency, bukan diputuskan hanya karena nama LMPC.

Tentukan state x, input u, output y, satuan, sample time Ts dan trim/equilibrium secara eksplisit. Contoh kerangka model discrete `x[k+1] = A*x[k] + B*u[k]`, `y[k] = C*x[k]` setelah identifikasi; ini belum matriks robot yang siap dipakai.

Jika model input memakai delapan normalized actuator, keputusan QP dan integrasinya ke allocator berbeda dari model body wrench. Pilih satu konvensi; jangan memasang model command-thruster ke solver wrench tanpa transformasi tervalidasi. Offset buoyancy, arah gaya dan batas nonlinear actuator juga harus ditangani.

### 9.2 Urutan implementasi

| Tahap | Yang dibuat | Bukti selesai |
|---|---|---|
| Model offline | Preprocessing bag, fitting A/B/C/trim, metadata model | Prediksi pada sesi independen dan batas domain operasi |
| Desain MPC | Horizon Np/Nc, Q/R, bounds input/Δinput/state, observer bila perlu | Simulasi tracking/noise/constraint; infeasibility terdeteksi |
| Solver Teensy | QP bounded memory/iteration, profiling waktu/RAM | Worst-case waktu solve sesuai budget scheduler, tidak menghambat heartbeat/sensor/watchdog |
| Integrasi controller | Interface reference/state, valid gate, model version, output convention | Satu controller aktif; tidak ada PD dan MPC mengirim authority bersamaan |
| Fallback | Timeout/nonfinite/infeasible/stale → kebijakan fallback/netral | Uji fault eksplisit; P/PD hanya dipakai jika kondisi dan reference aman |
| Telemetry/SysID | Controller aktif, solve status/time, model version, tracking/constraint | Bag menunjukkan controller/fallback dan output yang benar |
| HIL | Closed-loop, noise/drop, delay, step, saturation | Semua jalur keselamatan lulus; HIL tidak mengesahkan model riil |
| Wet terbatas | Bandingkan dengan baseline P/PD | Tracking/constraint/latency terukur sebelum memperluas operasi |

Model/gain pertama tetap hardcode berversi bila diperlukan. Runtime tuning/GUI baru aktif setelah ada kontrak request/ACK/readback dan enforcement firmware. Tidak ada command `enable_lmpc` atau file model final yang saat ini bisa dijalankan.

### 9.3 Kriteria sebelum menyatakan LMPC siap

Model valid pada domain yang dipakai; observer/state tersedia; tanda/satuan sesuai actuator; solver worst-case selesai tepat waktu; invalid/stale/infeasible/timeout tidak menghasilkan command liar; fallback tidak menyembunyikan fault; mode/Stop tetap mempunyai authority; output ceiling diterapkan oleh firmware; baseline dan LMPC dibandingkan pada konfigurasi robot yang sama. Jangan mengaktifkan posisi XY LMPC tanpa feedback XY tervalidasi.

## 10. Gerbang sebelum GUI micro-ROS asli

**Untuk GUI monitoring read-only**, cukup komunikasi nyata, kontrak namespace/provenance benar, validity/stale dan freshness ditangani, tanpa data SIM tersisip. LMPC bukan prasyarat monitoring.

**Untuk GUI mengendalikan kendaraan**, selesaikan actuator/manual/failsafe, kontrak command/ACK/timeouts, satu pemilik heartbeat dan stream manual antar-browser, Stop, state actual dan recovery. Setpoint/tuning/thruster-ceiling yang belum ada interface-nya tetap disabled. Perluasan sampling host untuk semua langkah/during/after/depth tidak stabil belum diimplementasikan hanya karena mockup menampilkannya.

Gateway awal laptop tersedia:

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
cd /home/charisto/tyrant-simple/gui/backend
/usr/bin/python3 server.py --payload-namespace /tyrant/payload
```

Di terminal lain:

```bash
curl -s http://127.0.0.1:8090/api/state | python3 -m json.tool
```

Ini menerima telemetry nyata, tidak mempublish command/heartbeat; frontend mockup belum terhubung. Tidak otomatis deploy/autostart Jetson. Jangan menganggap tombol mockup melakukan command board.

## 11. Cheatsheet akhir dan diagnosis cepat

| Gejala | Periksa/penyelesaian |
|---|---|
| Package/type tidak ditemukan | Source ROS dan workspace interface yang benar pada terminal tersebut |
| Agent tersambung tetapi estimator false | Sensor terpasang, mounting, warm-up, pressure/reference dan validity; bukan sekadar restart agent |
| PWM tidak bergerak pada teensy41 | Memang backend disabled; ikuti gerbang hardware bagian5, jangan memaksa gate |
| Skeleton ready=false | Pin/default belum valid atau init PWM gagal; cek fault/config |
| Thruster salah arah | Nomor, kabel, positive d dan inversion; bukan gain negatif |
| Sensor ON ditolak reason5 | Heartbeat ESP belum sehat, wrong namespace atau host pemilik tidak aktif |
| Suhu NaN pada hardware | Model/calibration belum dikonfirmasi atau sensor invalid |
| Disconnect count meningkat terus | USB/power, agent duplikat, baud, executor/publish failure; amati counter delta |
| Depth tidak valid padahal angkanya ada | Nilai terakhir bukan live; periksa pressure/state age dan validity |
| AUTO ditolak | Mission loaded, reduced state, komunikasi, allocator/backend ready; jangan bypass |
| SysID sample banyak tetapi model buruk | Sumber feedback lambat/berulang, input salah, clipping, closed-loop bias atau excitation tidak informatif |
| Copy install laptop ke Jetson gagal | Arsitektur x86/ARM64 berbeda; copy source dan build ARM64 |
| GUI terlihat live tetapi source SIM | Mockup belum terhubung; jangan memakai animasi sebagai evidence robot |

Perintah inspeksi paling sering:

```bash
ros2 node list
ros2 topic list
ros2 topic info /tyrant/host_heartbeat --verbose
ros2 topic info /tyrant/manual/command --verbose
ros2 topic hz /tyrant/simple_state
ros2 topic hz /tyrant/sysid/sample
ros2 topic echo /tyrant/system/health --once
ros2 topic echo /tyrant/actuation/status --once
ros2 bag info /path/aktual/ke/bag
```

`topic info --verbose` berguna mencari publisher heartbeat/manual yang ganda. Gunakan path bag aktual untuk perintah terakhir. Stop bag dengan Ctrl+C agar finalized; jangan kill recorder sebagai cara rutin.

## 12. Checklist pekerjaan yang tersisa

- [ ] Pin/kabel/identity board final, sensor asli dan kalibrasi suhu/air/IMU.
- [ ] Geometri produksi, skala allocator, arah dan karakterisasi ESC/thruster.
- [ ] Jalur tes individual dan profil PWM hardware tervalidasi.
- [ ] Manual wet, timeout/SAFE, batas output dan baseline P/PD.
- [ ] Wet SysID, metadata, preprocessing dan model independen tervalidasi.
- [ ] Solver/integrasi/fallback/telemetry LMPC serta HIL dan wet qualification.
- [ ] Konfigurasi Jetson hardware menggantikan HIL secara eksplisit.
- [ ] Frontend live/command ACK/ownership, perluasan host sampling dan kamera.

Acuan source utama: `control_config.h`, `thruster_config.h`, `stabilized_manual_controller.cpp`, `thruster_backend.cpp`, `thruster_output_mapper.cpp`, `payload_config.h`, interface ROS, `excitation_node.py`, supervisor Jetson. Penjelasan khusus tersimpan di `docs/teleop.md`, `docs/sysid.md`, `docs/hil_sim_sysid.md`, `docs/actuation_pwm.md`, `docs/jetson_autostart.md` dan PRD GUI. Dokumen ini menyatukan alur setup; bukan pernyataan bahwa tahap hardware/LMPC telah lulus.


### Pemeriksaan dokumen

Sintaks 36 blok perintah terminal diperiksa tanpa menjalankannya; 10 contoh publish dicocokkan dengan field/type interface ROS terpasang tanpa mengirim message. Path source/profil/helper dicocokkan dengan repository. Tidak dilakukan uji motor, SysID wet, solver LMPC atau deployment baru saat menyusun panduan ini.

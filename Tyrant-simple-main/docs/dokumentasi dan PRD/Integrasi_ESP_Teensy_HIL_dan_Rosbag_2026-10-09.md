# Kelanjutan integrasi ESP–Teensy: HIL dan rosbag — 9 Oktober 2026

Catatan ini melanjutkan dokumentasi implementasi 8 Oktober menuju sesi 9 Oktober.
Semua waktu pengujian berikut menggunakan WIB (Asia/Jakarta). Nama folder sesi
menggunakan UTC, sehingga `20261009T051049Z` berarti sekitar 12:10 WIB.

Dokumen sebelumnya: [integrasi host 8 Oktober](../payload_mission_host.md),
[cheatsheet host](../payload_mission_commands.md), dan
[validasi ESP 8 Oktober](../../firmware/esp/docs/validasi_2026-10-08.md).

## 1. Baseline yang sudah dibuat pada akhir sesi sebelumnya

- Firmware ESP dipindahkan ke `firmware/esp`.
- Paket `tyrant_interfaces` (Teensy) dan `tyrant_payload_interfaces` (ESP) tetap
  terpisah. Schema ESP bersumber dari `ros2_ws/src/tyrant_payload_interfaces`,
  dirujuk melalui symlink firmware. Firmware Teensy belum diubah.
- `tyrant_mission_host` menyediakan heartbeat kedua board, koordinasi segmen
  gerak dan sampling, serta rosbag, CSV, metadata dan event dalam satu sesi.
- Toleransi depth dan parameter sampling dapat diatur dalam YAML per titik.
- Pilihan daya auto: ON sepanjang misi atau ON pada titik pengukuran; manual
  tetap dikendalikan operator. Sampling payload yang gagal tidak menghalangi
  kelanjutan misi setelah batas waktu; hasil titik ditandai tidak lengkap.
- LMPC, GUI dan deployment ulang paket host di Jetson belum dilakukan.
- Build ESP dua profil, 28 test host/regresi, dan uji ROS endpoint tiruan sudah
  lulus. Itu merupakan baseline sebelum pengujian dua board bersama.

## 2. Setup pengujian 9 Oktober

Pengujian memakai board Teensy dengan profil HIL, ESP dengan profil simulasi,
plant dinamika simulasi pada laptop, dua proses agent serial, dan host mission.
Depth dan nilai payload dalam sesi ini adalah data simulasi; ini bukan validasi
sensor fisik, aktuator fisik atau kendaraan di air.

Satu agent membuka `/dev/tyrant-teensy`, agent lain `/dev/tyrant-esp`. Nomor
`ttyACM` dapat berpindah, sedangkan alias mengikuti identitas board.

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/microros_ws/install/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
```

Terminal plant:

```bash
ros2 launch tyrant_sim hil_plant.launch.py
```

Terminal agent + host:

```bash
ros2 launch tyrant_mission_host mission_host.launch.py start_agents:=true \
  output_dir:=/home/charisto/tyrant-simple/ros2_ws/bags/missions
```

Launcher mengirim heartbeat Teensy dan ESP otomatis 10 Hz. Tidak perlu publisher
heartbeat lain. Misi baru berjalan setelah service start. Bila agent sudah dibuka
manual, gunakan `start_agents:=false` agar port tidak dibuka dua kali.

## 3. Masalah yang ditemui dan penjelasannya

### State Teensy awal tidak valid meskipun heartbeat sehat

Operator sempat melihat `communication_healthy=true`, tetapi `estimator_ready=false`
serta attitude, heading, depth invalid. Source HIL mempertahankan angka state
terakhir saat input terlalu lama tidak diterima, lalu menandainya DEGRADED/invalid.
Heartbeat sehat tidak menjamin publisher plant mengirim state.

Pemeriksaan yang digunakan:

```bash
ros2 node list
ros2 topic hz /tyrant/sim/state_input
ros2 topic echo /tyrant/simple_state --once
```

Setelah plant aktif, operator menunjukkan `status=1` dan ketiga validitas true.
State valid kembali; mode SAFE sebelum start merupakan kondisi yang sesuai.

### Status host dan heartbeat berbeda dari agent

Agent hanya menjembatani komunikasi board. Node `/tyrant_mission_host` yang
mengirim heartbeat dan `/tyrant/host/mission/status` berkala, termasuk fase IDLE.
Topic status tersebut tidak seharusnya kosong saat node host sudah berjalan.

### Daya sensor ON selama misi dan OFF setelah selesai

Event mencatat empat request ON diterima dan empat request OFF diterima.
Status daya itu adalah perintah logis firmware, bukan bukti tegangan MOSFET fisik.
Setelah OFF, water quality NaN, valid=false, state=0 dan umur `4294967295` sesuai
semantik belum memiliki sampel dalam periode ON saat ini. Sequence tetap dapat
meningkat karena penghitung siklus bukan indikator sensor ON.

## 4. Pemeriksaan rosbag yang benar-benar direkam

Kedua bag dibuka dan pesan didekode secara offline. Tidak dilakukan replay,
pengiriman perintah board, atau perubahan parameter firmware dalam pemeriksaan.

| Sesi | Mulai WIB | Durasi pesan | Jumlah pesan |
| --- | --- | ---: | ---: |
| `20261009T050636Z_bcd9c966` | 9 Oktober 12:06:36 | 128,665 detik | 24.998 |
| `20261009T051049Z_79051c04` | 9 Oktober 12:10:49 | 134,202 detik | 26.042 |

Lokasi sesi: `ros2_ws/bags/missions/<nama_sesi>/`.
Keluaran mencakup `session.json`, `events.jsonl`, `samples.csv`, serta `bag/`.

Sesi terbaru memiliki 45 pesan water quality, 670 simple state, 1.341 monitoring
daya thruster ESP, 671 monitoring rel sensor, 8 ACK daya sensor, serta pesan
kendali, status misi/mode, health, diagnostik dan heartbeat kedua board.

| Sensor simulasi | Pesan dengan nilai finite dan valid | Rentang |
| --- | ---: | --- |
| EC | 40 dari 45 | 901,35–1.496,30 µS/cm |
| pH | 43 dari 45 | 6,40–7,99 |
| Suhu | 43 dari 45 | 24,51–27,48 °C |
| DO | 42 dari 45 | 1,50–8,49 mg/L |

Sebagian pesan invalid ikut direkam. Profil simulasi memang memiliki fase
gangguan sensor; OFF di akhir juga menghasilkan data invalid. Ini tidak
berarti seluruh rekaman hilang atau semua invalid disebabkan putus komunikasi.

Pada sesi terbaru, diagnostik ESP awal dan akhir sama:
connection_count=4, disconnect_count=3, ping_failures=882, publish_failures=53,
host_heartbeat_healthy=true. Tidak ada penambahan counter tersebut sepanjang
rekaman yang diamati; ini belum membuktikan kestabilan untuk waktu yang lebih panjang.

## 5. Mengapa counts sensor nol padahal nilainya ada?

`counts` adalah jumlah sampel baru/valid yang diterima sebagai pengukuran pada
titik depth setelah syarat stabilisasi terpenuhi. Itu bukan nilai sensor dan
bukan jumlah seluruh pesan dalam bag. Seluruh data tetap disimpan ketika fase
TRAVEL atau STABILIZING, tetapi belum menjadi sampel resmi titik misi.

Kedua sesi masuk WAIT/STABILIZING, tetapi tidak memiliki event `sampling_started`.
Dengan toleransi depth ±0,1 m, depth menetap di luar rentang:

| Target | Depth akhir STABILIZING sesi pertama | Sesi terbaru |
| --- | ---: | ---: |
| 1 m | 1,133 m | 0,866 m |
| 3 m | 3,135 m | 3,133 m |

Pada sesi terbaru, pH tetap valid pada 20 snapshot fase STABILIZING depth 1 dan
12 snapshot depth 3. Jadi data payload tersedia, tetapi gerbang sampling belum
lolos. Kedua titik berakhir dengan `Sampling/stabilization timeout` setelah
batas waktu 40 detik, dengan seluruh counts=0.

Langkah surge, sway dan heading selesai. Counts nol pada langkah-langkah itu
memang sesuai karena tidak meminta sampling. Heading merupakan target absolut
-90°, bukan rotasi relatif -90° pada setiap pengulangan misi; jika heading awal
sudah dekat target, langkah heading dapat selesai sangat cepat.

`COMPLETE` berarti urutan eksekusi host selesai. Kedua metadata sesi menunjukkan
`all_sampling_points_complete=false`, sehingga tidak boleh dilaporkan bahwa
pengukuran kedua titik sudah berhasil.

## 6. Status penerimaan dan keputusan akhir sesi

| Bagian | Status |
| --- | --- |
| Dua board terhubung dan pesan kedua board direkam | Teramati berhasil pada sesi ini |
| Heartbeat host dan ACK daya | Berhasil pada sesi yang diperiksa |
| Daya sensor ON/OFF sesuai misi | Berhasil secara logis pada firmware simulasi |
| Gerak surge/sway/heading | Selesai menurut status Teensy HIL |
| Rosbag dapat dibuka dan data kualitas air tersedia | Berhasil |
| Sampling resmi pada target depth | Belum berhasil; kedua titik tidak lengkap |
| Controller depth akurat/stabil pada kendaraan fisik | Belum diuji |
| Sensor fisik, GUI, LMPC, deployment ulang Jetson | Belum selesai / belum dilakukan |

Saat beralih dari gerak depth ke WAIT, controller Teensy mempertahankan referensi
internal yang belum secara eksplisit dikunci ke target misi. Hasil HIL menunjukkan
offset sekitar 0,13 m. Perbaikan referensi depth pernah diusulkan, tetapi pengguna
memilih melanjutkan pemeriksaan rosbag dahulu. **Tidak ada perubahan Teensy atau
pelonggaran toleransi yang dilakukan dalam sesi ini.**

## 7. Langkah berikutnya yang disarankan

1. Uji pengumpulan sampel dengan toleransi konfigurasi ±0,2 m sebagai eksperimen
   HIL, tanpa perubahan firmware Teensy. Ini hanya menguji alur sampling dengan
   rentang lebih lebar, bukan perbaikan akurasi controller. Simpan sebagai rencana
   uji tersendiri agar parameter asli tetap dapat dibandingkan.
2. Pastikan muncul `sampling_started`, counts memenuhi target per sensor, dan
   `all_sampling_points_complete=true`; buka bag hasilnya untuk memeriksa nilai,
   validitas, kedalaman aktual dan penanda fase. Batas waktu tetap berlaku jika
   profil simulasi sedang menghasilkan kegagalan sensor.
3. Setelah hasil laptop dinilai cukup, deploy dua paket host baru ke container
   Jetson dan ulangi dua agent, heartbeat serta rekaman. Jangan salin artefak
   build/install laptop x86 ke Jetson ARM64; bangun source di Jetson.
4. GUI dan kamera webcam dikerjakan setelah kontrak/status host diuji. LMPC dan
   perbaikan hold depth tetap pekerjaan terpisah yang perlu pembahasan.

Daftar ini adalah usulan berikutnya, bukan tindakan yang sudah dilakukan.

### Persiapan eksperimen berikutnya setelah persetujuan pengguna

Rencana `ros2_ws/src/tyrant_mission_host/config/two_depth_hil_sampling_020m.yaml`
telah dibuat dan lolos validator rencana host. Mission ID berbeda, hanya toleransi
dua langkah depth yang dilonggarkan menjadi ±0,2 m; parameter stabilisasi, sampling,
gerak, dan toleransi heading tetap sama. File awal tidak diubah. Firmware tidak
diubah atau di-upload. Hasil sampling pada dua board menggunakan rencana baru
masih menunggu pengujian operator; ini belum dinyatakan PASS.

Perintah peluncuran ada di [cheatsheet](../payload_mission_commands.md).

### Hasil eksperimen ±0,2 m — 9 Oktober, 17:28 WIB

Bag terbaru `20261009T102835Z_11be845a` dibuka dan didekode. Rencana yang tersimpan
adalah `two_depth_hil_sampling_020m`. Rekaman berisi 16.581 pesan selama 85,315 detik,
termasuk 23 snapshot water quality. Kedua titik memiliki event `sampling_started`
dan hasil `Per-sensor valid sample targets met`.

| Titik | EC / pH / suhu / DO yang memenuhi syarat | Rentang estimasi depth terkait sampel |
| --- | --- | --- |
| Target 1 m | Masing-masing 3 sampel | 0,967630–0,967721 m |
| Target 3 m | Masing-masing 3 sampel | 3,033581–3,038144 m |

CSV mengonfirmasi 24 baris qualified: empat sensor × tiga sampel × dua titik.
Metadata akhir menunjukkan `COMPLETE` dan `all_sampling_points_complete=true`.
Seluruh 426 pesan simple state memiliki depth valid. Counter gangguan ESP awal
dan akhir sama: connection_count=2, disconnect_count=1, ping_failures=682,
publish_failures=14, host_heartbeat_timeout_count=1; heartbeat sehat pada keduanya.
Counter tersebut adalah riwayat sebelum sesi, tidak bertambah sepanjang bag ini.

**Pengumpulan sampel dua titik pada eksperimen HIL ini lulus.** Ini menggantikan
status menunggu pengujian rencana ±0,2 m pada paragraf persiapan sebelumnya.
Toleransi awal ±0,1 m dan firmware Teensy tidak diubah. Hasil ini bukan validasi
sensor fisik, tuning controller kendaraan, sinkronisasi clock presisi, atau LMPC.
Langkah berikutnya dapat dilanjutkan ke deployment paket host di Jetson.

Hasil decoding: [sesi sampling lengkap](../validation/mission_host_2026-10-09/20261009T102835Z_11be845a.json).

Ringkasan hasil decoding:
[sesi pertama](../validation/mission_host_2026-10-09/20261009T050636Z_bcd9c966.json),
[sesi terbaru](../validation/mission_host_2026-10-09/20261009T051049Z_79051c04.json).

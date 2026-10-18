# Plant HIL berhenti saat misi dan perbaikan host — 10 Oktober 2026

Kelanjutan [catatan 9 Oktober](Integrasi_ESP_Teensy_HIL_dan_Rosbag_2026-10-09.md).
Waktu lokal menggunakan WIB. Bag `20261009T172737Z_6a8f85a6` dimulai sekitar
10 Oktober 00:27:37 WIB; nama folder menggunakan UTC.

## Hasil pemeriksaan sebelum perbaikan

Operator menghentikan plant ketika misi aktif. Bag dibuka offline dan menunjukkan:

- Pengukuran titik depth 1 selesai: tiga sampel qualified untuk setiap sensor.
- State pertama depth invalid muncul 32,122 detik sejak awal pesan bag.
- Command thruster disabled dan nol pertama teramati 0,00483 detik setelah pesan
  invalid tersebut. Seluruh 192 command yang diperiksa setelah jeda 0,2 detik
  disabled/nol. Ini bukti pada backend mock/HIL, bukan pengukuran aktuator fisik.
- Tidak ada baris sampel qualified setelah pesan invalid pertama.
- Mode SAFE teramati 2,193 detik setelah invalid; host FAILED setelah 2,313 detik.
- Host masih menandai surge selesai berdasarkan durasi, kemudian mencoba langkah
  sway. Request AUTO ditolak dengan reason=5 (autonomy belum siap), barulah host gagal.
- ACK OFF diterima untuk keempat kanal sensor setelah kegagalan misi.

Proteksi output Teensy bekerja pada trace tersebut. Kekurangan host: belum ada
pemeriksaan estimator/state yang langsung membatalkan seluruh fase misi; kondisi
tidak valid baru menghalangi mode AUTO untuk segmen berikutnya.

Data pemeriksaan: [ringkasan trace sebelum perbaikan](../validation/mission_host_2026-10-10/20261009T172737Z_6a8f85a6.json).

## Perubahan yang telah diizinkan dan dibuat

Perubahan hanya pada paket `tyrant_mission_host` di `ros2_ws`; firmware Teensy dan
ESP tidak diubah. Host sekarang:

1. Memerlukan state fresh/valid selain health yang siap saat start.
2. Memeriksa attitude, heading, depth, nilai finite roll/pitch/yaw/depth dan status FAULT.
3. Membatalkan misi aktif saat `estimator_ready=false`, state invalid atau tidak
   diterima melewati `depth_fresh_s` (contoh default 0,5 detik).
4. Memeriksa kondisi tersebut saat menerima state/health, timer, ACK, status selesai
   serta payload; tidak menunggu durasi surge/sway atau batas waktu sampling.
5. Menghapus request gerak/ON yang belum dikirim, lalu meminta STOP, SAFE dan OFF
   untuk sensor terpilih. ACK/status terlambat tidak membuka segmen berikutnya.
6. Menyimpan langkah yang terputus sebagai `complete=false`, dengan alasan state
   invalid, stale/missing, atau estimator belum siap. Titik yang sudah berhasil
   sebelum gangguan tetap tercatat sebagai berhasil.

Ketika host IDLE atau hanya merekam manual, state invalid tidak otomatis mengubah
mode board. Kegagalan sensor payload tetap mengikuti kebijakan titik tidak lengkap
dan lanjut setelah timeout; kebijakan itu berbeda dari kehilangan state kendaraan.

## Verifikasi setelah perubahan

- 37 test logika host/regresi teleop/sim: PASS.
- Build paket `tyrant_mission_host`: PASS.
- ROS lokal dengan endpoint tiruan: PASS untuk sampling normal, rekaman manual,
  sensor payload gagal, serta state invalid/stale saat langkah gerak.
- Pada endpoint tiruan, invalid membatalkan misi setelah sekitar 0,037 detik sejak
  injeksi; tidak ada state baru membatalkan misi sekitar 0,523 detik dengan freshness
  0,5 detik. STOP/SAFE/OFF diterima dan langkah gerak dicatat gagal.
- Nilai waktu tersebut hasil satu uji endpoint tiruan, bukan batas latensi yang
  dijamin pada board fisik. Pengujian ulang operator pada Teensy HIL masih diperlukan.

## Mengaktifkan perubahan dan mengulang pengujian

Hentikan launcher host lama, lalu:

```bash
cd /home/charisto/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tyrant_mission_host --symlink-install
source /home/charisto/microros_ws/install/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
```

Tidak perlu upload ulang firmware. Jalankan plant seperti sebelumnya. Di terminal
host, gunakan rencana uji ±0,2 m:

```bash
ros2 launch tyrant_mission_host mission_host.launch.py start_agents:=true \
  plan:=/home/charisto/tyrant-simple/ros2_ws/src/tyrant_mission_host/config/two_depth_hil_sampling_020m.yaml \
  output_dir:=/home/charisto/tyrant-simple/ros2_ws/bags/missions
```

Gunakan `start_agents:=false` jika kedua agent masih berjalan terpisah. Setelah
state dan heartbeat sehat, mulai melalui service seperti panduan sebelumnya.
Hentikan plant saat fase TRAVEL pada surge. Hasil yang diharapkan: host FAILED
karena state invalid atau estimator tidak siap, tidak menandai surge berhasil,
tidak membuka sway, dan STOP/SAFE/OFF teramati. Periksa bag terbaru setelah selesai.

Respons dimulai saat host menerima informasi invalid, atau setelah batas freshness
terlampaui. Timeout source HIL, laju telemetry dan latensi ROS turut memengaruhi
waktu dari penghentian proses plant sampai gangguan diketahui host.

## Pengujian ulang operator setelah perbaikan — 10 Oktober

Dua sesi terakhir dipilih berdasarkan `started_utc` di metadata, karena waktu
modifikasi folder dapat berubah saat berkas disalin. Keduanya dibuka dan didekode
offline, termasuk pengecekan CSV serta event; tidak ada replay/perintah ke board.

### Sesi 00:45 WIB: plant dihentikan saat sway

Bag `20261009T174528Z_6b544ded`: 9.098 pesan selama 46,685 detik.
Titik depth 1 berhasil (EC 3 sampel; pH/suhu/DO masing-masing 6) dan surge selesai
sebelum gangguan. Counts boleh melebihi target karena host menunggu semua sensor
memenuhi minimal 3 sampel. Gangguan terjadi saat langkah `right` aktif.

- State invalid pertama pada detik 44,685 sejak awal pesan bag.
- Request STOP teramati 0,00500 detik sesudahnya; SAFE 0,00579 detik sesudahnya.
- Command disabled/nol pertama teramati 0,00454 detik sesudahnya.
- Topic status host memperlihatkan FAILED 0,04979 detik sesudahnya, dengan alasan
  `Teensy state invalid`. Langkah `right` dicatat `complete=false`.
- Tidak ada command enabled/nonzero dalam 87 pesan setelah jeda 0,2 detik;
  tidak ada sampel qualified setelah invalid. Langkah heading/depth 3 tidak dimulai.

Respons pembatalan saat gangguan state **lulus pada rekaman HIL ini**. Ini waktu
yang diamati relatif terhadap pesan invalid, bukan waktu pasti sejak tombol Ctrl+C.

### Sesi 00:47 WIB: misi normal sesudah gangguan

Bag `20261009T174759Z_9f333d9e`: 12.728 pesan selama 65,268 detik, termasuk
30 pesan water quality. Tidak ditemukan state invalid atau estimator tidak siap.
Kedua titik memperoleh masing-masing 3 sampel qualified EC/pH/suhu/DO.
Seluruh langkah selesai, `COMPLETE` dan `all_sampling_points_complete=true`.
Ini memverifikasi jalur normal tetap bekerja setelah perubahan host.

Counter diagnostik ESP awal/akhir kedua sesi tidak bertambah:
connection_count=4, disconnect_count=3, ping_failures=5439, publish_failures=51;
heartbeat sehat. Dengan demikian kedua sesi ini belum merupakan pengujian
agent ESP sengaja dihentikan ketika misi aktif. Uji kehilangan state Teensy dan
regresi misi normal sudah terbukti; uji gangguan ESP saat sampling masih tersisa.

Data pemeriksaan:
[sesi gangguan](../validation/mission_host_2026-10-10/20261009T174528Z_6b544ded.json),
[sesi normal](../validation/mission_host_2026-10-10/20261009T174759Z_9f333d9e.json).

## Agent ESP dihentikan dan dinyalakan kembali — 10 Oktober, 00:56 WIB

Bag `20261009T175624Z_b4f2b0b4` dibuka offline: 18.102 pesan dalam 98,458 detik.
Titik depth 1 memperoleh tiga sampel per sensor sebelum gangguan. Jeda antar
heartbeat ESP terbesar sekitar 53,093 detik, dari detik 36,195 sampai 89,288
relatif awal bag. Dengan demikian hilangnya agent yang terlihat pada rekaman
dimulai selama rangkaian gerak setelah titik pertama, lalu meliputi sampling
depth 3; bukan ketika sampling titik pertama masih aktif.

- Seluruh 491 simple state memiliki depth valid; Teensy tetap mengirim state
  selama pesan ESP berhenti. Langkah surge/sway/heading selesai.
- Depth 3 masuk SAMPLING saat ESP belum kembali. Tidak ada baris qualified
  selama jeda heartbeat, sehingga data lama tidak memenuhi counts secara ulang.
- Heartbeat/diagnostik ESP kembali; connection_count naik 5→6,
  disconnect_count dan reconnect_count naik 4→5. Heartbeat host sehat kembali.
- Snapshot water quality terakhir sebelum gap memiliki sequence 6062; pertama
  setelah gap 6086, dengan uptime tetap meningkat. Ini konsisten dengan reconnect
  tanpa reboot dan siklus yang tidak dikirim, bukan replay data offline.
- Snapshot pertama setelah gap memiliki EC invalid/ERROR; pH/suhu/DO memperoleh
  masing-masing satu sampel qualified sebelum batas waktu depth 3 tercapai.
- Depth 3 berakhir tidak lengkap: EC=0, pH/suhu/DO=1, alasan
  `Sampling/stabilization timeout`. `COMPLETE` untuk urutan misi dan
  `all_sampling_points_complete=false` dilaporkan dengan benar.
- Setelah selesai, empat request OFF mendapat ACK accepted=true.

Penanganan putus/reconnect payload, tidak menghitung data lama, serta penandaan
titik tidak lengkap **teramati sesuai kebijakan pada HIL ini**. Karena depth 3
adalah titik terakhir, bag ini tidak menguji langkah gerak setelah timeout titik
tersebut; namun gerak Teensy tetap berlangsung selama agent ESP terputus.
Ketiga skenario laptop (misi normal, plant hilang, agent ESP hilang/pulih) kini
memiliki bukti pada bag. Tahap berikutnya dapat dimulai dengan deployment host
ke Jetson dan pengulangan verifikasi pada container ARM64.

Hasil decoding: [sesi gangguan agent ESP](../validation/mission_host_2026-10-10/20261009T175624Z_b4f2b0b4.json).

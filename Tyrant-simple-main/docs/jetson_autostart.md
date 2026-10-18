# Autostart Jetson — dua agent dan heartbeat host

Konfigurasi saat ini adalah bench HIL: ESP simulasi, Teensy HIL, dan plant
simulasi. Container `tyrant-mission` menjalankan supervisor, host misi, dua
agent serial, serta plant HIL. Host kembali ke IDLE setiap startup; misi dan
perekaman tidak dimulai otomatis. Heartbeat ke kedua board berjalan otomatis.

Supervisor `companion/jetson/run_mission_companion.py` menjalankan executable
langsung. Setiap agent menunggu alias USB boardnya sendiri. Jika agent keluar
atau port terlepas, agent tersebut dipulihkan setelah port tersedia tanpa
restart host. Jika host/plant keluar, supervisor berhenti, menutup proses lain,
dan restart policy Docker memulai container kembali.

Saat penghentian normal container, supervisor meminta STOP/SAFE melalui service
host, memberi waktu pengiriman OFF sensor dan penutupan recorder, lalu
menghentikan proses. Jika host/board sudah tidak tersedia, konfirmasi STOP/OFF
tidak dapat diasumsikan; komunikasi dan failsafe tetap diperiksa dari telemetry.

## Pemasangan yang digunakan

Pada host Jetson, source supervisor disimpan di
`/home/nvidia/tyrant-mission-autostart/companion/jetson/`.
Workspace agent lama `/home/nvidia/ros2_docker/ws` dipasang read-only ke `/ws`;
workspace baru `/home/nvidia/ros2_docker/mission_ws` dipasang ke `/mission_ws`.
Alias USB host dipasang melalui `/dev` ke `/host-dev`.

Perintah pembuatan pertama (container lain harus berhenti):

```bash
TYRANT_HIL_PLANT=true bash ~/tyrant-mission-autostart/companion/jetson/start_mission_autostart.sh
```

Launcher menolak jika container sudah ada atau container Tyrant lain masih
berjalan. Container lama disimpan untuk rollback. Image tetap
`tyrant-companion:bench`, tanpa rebuild agent/image.

Docker aktif saat boot; restart policy container `unless-stopped`. Container
yang sengaja dihentikan dengan `docker stop` tetap berhenti setelah reboot
sampai dijalankan kembali dengan `docker start`.

## Perintah harian — terminal SSH HOST Jetson

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker logs --tail 40 tyrant-mission
docker inspect tyrant-mission --format 'Status={{.State.Status}} RestartCount={{.RestartCount}} Policy={{.HostConfig.RestartPolicy.Name}}'
timedatectl status
```

Masuk ke container:

```bash
docker exec -it tyrant-mission bash
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
source /mission_ws/install/setup.bash
```

Di dalam container, pemeriksaan dan kontrol misi:

```bash
ros2 topic echo /tyrant/host/mission/status std_msgs/msg/String --once --full-length
ros2 topic echo /tyrant/system/health --once
ros2 topic echo /tyrant/payload_sim/communication/diagnostics --once
ros2 service call /tyrant/host/mission/start std_srvs/srv/Trigger '{}'
ros2 service call /tyrant/host/mission/stop std_srvs/srv/Trigger '{}'
```

Perekaman manual tanpa memulai misi:

```bash
ros2 service call /tyrant/host/recording/start std_srvs/srv/Trigger '{}'
ros2 service call /tyrant/host/recording/stop std_srvs/srv/Trigger '{}'
```

Jangan menjalankan agent, plant, host, atau publisher heartbeat lain pada
domain ROS yang sama selama container ini aktif.

Stop/start/restart pada HOST:

```bash
docker stop -t 45 tyrant-mission
docker start tyrant-mission
docker restart -t 45 tyrant-mission
```

Untuk kembali ke container manual, hentikan `tyrant-mission`, lalu
`docker start tyrant-mission-dev`. Untuk supervisor lama Teensy/logger,
gunakan `docker start tyrant-companion` setelah semua container lain berhenti.

## Sinkronisasi waktu

Jetson menggunakan NetworkManager `Wired connection 1` dengan DNS persisten
`8.8.8.8,1.1.1.1` dan `ipv4.ignore-auto-dns=yes` (sudah ada saat pemeriksaan).
Server waktu ditetapkan di `/etc/systemd/timesyncd.conf.d/tyrant.conf`:

```ini
[Time]
NTP=time.cloudflare.com ntp.ubuntu.com
FallbackNTP=ntp.ubuntu.com
```

`systemd-timesyncd` diaktifkan saat boot. Pemeriksaan:

```bash
timedatectl status
systemctl status systemd-timesyncd --no-pager
date -u
```

Harapkan `System clock synchronized: yes`. NTP memerlukan koneksi internet,
termasuk forwarding/NAT laptop bila memakai Ethernet sharing. Koneksi ke
`8.8.8.8` berhasil pada pengujian ini; kegagalan ping `1.1.1.1` sendiri tidak
membuktikan internet terputus. Host tetap mengirim heartbeat jika NTP belum
tersedia; service start misi belum mempunyai pemeriksaan sinkronisasi jam.
Periksa waktu sebelum merekam. Koreksi waktu sebelumnya juga memperbaiki RTC.

## Peralihan ke firmware hardware

Container saat ini dibuat dengan `TYRANT_HIL_PLANT=true`, namespace
`/tyrant/payload_sim`, dan `TYRANT_TEENSY_SIMULATED=true`. Sebelum firmware
hardware digunakan, buat konfigurasi container yang sesuai: plant dimatikan,
namespace `/tyrant/payload`, dan provenance Teensy real. Perubahan environment
melalui `docker exec` tidak mengubah konfigurasi supervisor yang sudah aktif.
Pengujian ini tidak mengesahkan sensor riil atau thruster riil.

## Hasil validasi

Validasi 10 Oktober 2026 WIB:

- Autostart container berhasil; host masuk IDLE tanpa memulai misi.
- Agent ESP sengaja dihentikan dan dipulihkan otomatis; PID host tetap 32,
  agent Teensy tetap berjalan, dan container tidak restart karena uji ini.
- Restart container saat misi aktif menghasilkan sesi
  `20261009T185340Z_04638124` dengan status STOPPED. Bag terbaca normal:
  2.782 pesan selama 14,13 detik. Empat ACK ON dan empat ACK OFF diterima;
  mode akhir yang direkam SAFE (4). Host baru kembali IDLE.
- Reboot Jetson benar-benar dilakukan (boot ID berubah). Container kembali
  berjalan otomatis, kedua heartbeat sehat, dan host tetap IDLE.
- NTP tersinkronisasi sebelum dan sesudah reboot. RTC juga menunjukkan waktu
  yang benar. Server yang dipakai `time.cloudflare.com`.
- Setelah reboot, ESP menjadi ttyACM0 dan Teensy ttyACM1. Kedua alias tetap
  cocok dengan nomor serial: ESP `28:84:85:8B:BD:38`, Teensy `13843280`.
- Dua pemeriksaan diagnostik ESP setelah reboot menunjukkan counter tetap:
  connection 7, disconnect 6, reconnect 6, ping failures 3308, publish
  failures 86. Nilai ini mencakup gangguan pengujian; tidak bertambah di
  antara kedua pemeriksaan. RestartCount container sesudah boot adalah 0.

Kondisi akhir: container `tyrant-mission`, kedua agent, heartbeat host, dan
plant HIL **sedang aktif**. Misi IDLE. Container lama tetap berhenti.

Bukti: [laporan](validation/jetson_autostart_2026-10-10/autostart-report.json),
[telemetry sesudah reboot](validation/jetson_autostart_2026-10-10/autostart-validation/health-after-reboot.log),
[waktu sesudah reboot](validation/jetson_autostart_2026-10-10/autostart-validation/time-after-reboot.log),
dan [log supervisor](validation/jetson_autostart_2026-10-10/autostart-validation/container-runtime.log).
Bag restart dan metadata disimpan di folder validation yang sama serta
workspace Jetson. Tes regresi supervisor lama (empat tes) juga lulus;
supervisor baru diverifikasi melalui runtime Docker/board dan reboot di atas.

Yang belum diuji: cabut/pasang fisik USB (uji ESP memakai penghentian proses
agent), boot dengan salah satu board absen, mati daya mendadak, serta profil
hardware riil. Uji reboot normal tidak membuktikan perilaku mati daya mendadak.

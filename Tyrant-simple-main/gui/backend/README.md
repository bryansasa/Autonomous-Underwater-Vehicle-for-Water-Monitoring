# Gateway GUI tahap 1 — telemetry ROS

Gateway membaca snapshot nyata dari ROS ke `GET /api/state`. Tidak memakai data contoh, membuat agent, heartbeat, publisher perintah atau recorder baru. Semua kemampuan kontrol dinyatakan belum tersedia. Frontend mockup tetap SIM dan belum memakai API ini.

## Menjalankan di laptop terlebih dahulu

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
cd /home/charisto/tyrant-simple/gui/backend
/usr/bin/python3 server.py --payload-namespace /tyrant/payload_sim
```

Untuk ESP produksi/simulasi firmware yang menggunakan namespace produksi, pilih `--payload-namespace /tyrant/payload`. Namespace harus mengikuti konfigurasi board/host, bukan ditentukan hanya dari nama environment firmware.

Terminal kedua:

```bash
curl -s http://127.0.0.1:8090/api/state | python3 -m json.tool
```

Tidak perlu board aktif untuk menjalankan API, tetapi stream tanpa publisher akan memiliki `received: false`, `stale: true`, `data: null`. Agent dan heartbeat tetap dijalankan oleh setup host yang ada.

Di container Jetson, source `/opt/ros/humble/setup.bash` dan `/ws/install/setup.bash`, lalu jalankan source gateway yang telah disalin. Penambahan service/autostart gateway belum dilakukan; jangan menyalakan host misi kedua. API default hanya bind localhost. Akses jaringan operasional memerlukan bind yang sesuai dan frontend satu origin; CORS bebas tidak ditambahkan.

## Kontrak snapshot

- `schema_version: 1`, `server_time_utc`, `source: ROS`, namespace/profile payload dan capability.
- `streams`: navigation, health, mode, mission_board, teensy_diagnostics, thrusters, actuation, depth_reference, water_quality, dua power, sensor_power_ack, payload_health, esp_diagnostics dan mission_host.
- Tiap stream menyimpan topic/type, received, reception_age_ms, stale_after_ms, stale dan message data asli. Field float NaN/Infinity menjadi JSON null; flag valid sumber tetap dipertahankan.
- Reception age memakai clock monotonik backend. `timestamp_us` board tetap uptime; tidak dikonversi menjadi UTC. Age/validity tiap kanal air tetap dibaca terpisah oleh client.
- Ambang tampilan awal 2 s untuk Teensy/host dan 8 s untuk payload. Ini batas umur penerimaan snapshot, bukan keputusan keselamatan atau pengganti stale threshold sensor di firmware. Field accepted pada ACK lama tidak dibalik hanya karena usia event bertambah.
- Host mission status masih berbentuk field String JSON sumber; schema engine tidak diubah pada tahap ini.
- Subscription memakai best-effort volatile untuk kompatibilitas publisher. Status/event yang tidak dipublikasikan berkala baru tersedia setelah event berikutnya; snapshot ini belum merupakan readback persisten status daya atau rekaman.
- POST ditolak; tidak ada endpoint arbitrary ROS publish. API snapshot belum streaming WebSocket.

## Verifikasi dan tahap berikutnya

`python3 -m unittest -v test_state.py` menguji missing data, normalisasi nonfinite, clock/uptime, freshness dan pemisahan namespace. Interface ROS dicek dapat dimuat dari workspace. Uji HTTP memeriksa snapshot dan penolakan POST. Data board riil dan deployment Jetson belum diuji oleh gateway ini.

Tahap berikut: koneksi frontend live yang mematikan fitur simulasi saat memakai API; pembacaan valid/stale per kanal; lalu kontrak command/ACK serta ownership manual. Perluasan sampling host untuk semua jenis langkah/during/after tetap pekerjaan terpisah sebelum planner GUI aktif riil. Gateway tidak boleh membuat frontend SIM terlihat seolah state board asli.

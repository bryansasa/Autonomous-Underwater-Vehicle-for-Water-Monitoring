# Kontrak payload dan rencana rekaman multi kedalaman

Update setelah persetujuan integrasi: koordinasi awal dan rekaman host kini tersedia
di `ros2_ws/src/tyrant_mission_host`, tanpa perubahan firmware Teensy. Lihat
[panduan integrasi HIL](../../../docs/payload_mission_host.md). Rencana di bawah
mencatat konteks sebelum implementasi; GUI dan deployment Jetson masih tahap berikutnya.

Tanggal: 2026-10-08. **Rencana host untuk dibahas**, belum diimplementasikan di
Teensy, `ros2_ws`, GUI, atau deployment Jetson. ESP tidak memiliki sensor depth
atau otoritas kendali misi.

## Topic firmware

Semua topic di namespace `/tyrant/payload`:

| Arah | Suffix | Tipe | Pola |
|---|---|---|---|
| masuk | host_heartbeat | std_msgs/UInt32 | host perlu mengirim berkala |
| masuk | sensor_power/request | SensorPowerRequest | perintah ON/OFF |
| keluar | sensor_power/status | SensorPowerStatus | ACK request_id |
| keluar | water_quality | PayloadWaterQuality | setelah siklus akuisisi adaptif |
| keluar | power/sensors | PayloadPower | 5 Hz |
| keluar | power/thruster | PayloadPower | 10 Hz |
| keluar | health | PayloadHealth | 2 Hz |
| keluar | heartbeat | std_msgs/UInt32 | 1 Hz |
| keluar | communication/diagnostics | PayloadCommunicationDiagnostics | 1 Hz |

Keenam tipe custom berada di paket `tyrant_payload_interfaces` dan tetap terpisah
dari `tyrant_interfaces`. ID daya: 1 EC, 2 pH, 3 suhu, 4 DO. INA monitor_id:
1 rel sensor, 2 bus thruster. Power request adalah set-state, bukan toggle.
`actual_enabled` melaporkan perintah GPIO, bukan hasil pengukuran tegangan saklar.

## Semantik waktu dan validitas

- `PayloadWaterQuality.timestamp_us`: uptime ESP 64-bit saat snapshot dirakit;
  **bukan ROS time, UTC, ataupun clock Teensy**. Tidak wrap pada 71 menit.
- `*_age_ms`: umur sejak pembacaan sukses kanal selesai diterima ESP; `UINT32_MAX`
  jika belum ada sampel pada periode ON saat ini. Ini adalah umur hasil pembacaan,
  bukan timestamp pasti proses konversi internal sensor.
- Kanal gagal dapat menyimpan nilai terakhir dengan valid=false dan age yang
  terus bertambah. OFF menghapus sampel kanal. Jangan merekam invalid sebagai nol.
- `sequence`: nomor siklus selesai, meningkat juga ketika agent tidak tersambung.
  Gap menandai siklus yang tidak terkirim; tidak ada buffer replay offline.
  Restart ESP mengulang uptime dan sequence. Reconnect tanpa restart mempertahankannya.
- `PayloadPower.timestamp_us`: waktu akuisisi register terakhir berhasil; 0 jika
  belum berhasil. Periksa valid/state; nilai arus/daya invalid berupa NaN.
- `PayloadHealth.timestamp_us`: waktu snapshot health. `uptime_ms` field uint32
  mengikuti millis (wrap ~49 hari), berbeda dengan uptime timestamp 64-bit.

## Integrasi yang perlu dibahas dahulu

1. Tambahkan paket payload yang sama ke build host laptop/Jetson, tanpa
   mengganti interface Teensy. Tetapkan cara menjaga satu sumber schema.
2. Jalankan agent ESP terpisah dari agent Teensy dengan port by-id/udev unik;
   identifikasi USB ESP fisik dahulu. Jangan menebak ttyACM0/ttyACM1.
3. Tentukan pemilik heartbeat payload: node pendamping payload/misi atau
   kebijakan bersama. Firmware saat ini tidak mengubah heartbeat Teensy.
4. Rekam semua topic payload bersama `/tyrant/simple_state`,
   `/tyrant/mission/status`, mode, dan system health dalam bag yang sama.
   Pastikan nama/topic aktual host sebelum mengubah daftar logger.
5. Susun penggabung data host untuk setiap **titik dan kedalaman** misi:
   mission/session ID, step ID, target depth, depth aktual, validitas depth,
   fase transisi/stabilisasi/dwell, waktu host, sequence payload, umur kanal,
   data EC/pH/DO/suhu, dan status power/komunikasi.
6. Tanda tangani kriteria pengambilan sampel: sensor ON + warm-up selesai,
   depth valid dan stabil dalam toleransi selama waktu tertentu, lalu kumpulkan
   beberapa **sampel baru** saat dwell. Nilai berulang/replay bukan sampel baru.
   Hindari menempelkan snapshot akhir transisi ke titik depth berikutnya.
7. Tentukan toleransi waktu dan metode sinkronisasi. Bag menerima pesan dengan
   waktu host, tetapi serial memiliki latensi; uptime ESP tidak boleh langsung
   dibandingkan dengan uptime Teensy. Untuk korelasi presisi, sepakati tambahan
   timestamp tersinkron/boot-session ID atau metode estimasi offset dan batas
   galat terlebih dahulu. Field schema belum ditambahkan sepihak.
8. Tentukan kebutuhan sampling per titik: EA-DSRA hingga 5 detik dapat membatasi
   jumlah sampel dalam dwell singkat. Bahas mode sampling tetap saat dwell atau
   dwell yang cukup panjang, beserta penanganan sensor invalid/ESP putus.

## Acceptance test tahap berikutnya

- Dua agent aktif bersamaan, tiap node/topic berasal dari board yang benar.
- Putus/sambung USB ESP tidak mengganggu node Teensy; ESP pulih tanpa reboot.
- Heartbeat host berhenti: ON ditolak, OFF diterima, status stale/timeout akurat.
- Lepas satu EZO/INA: kanal terkait invalid/error; kanal/bus lain tetap diukur.
- Ukur INA dengan tegangan/arus referensi dan kalibrasi suhu setelah model jelas.
- Misi multi depth simulasi: rekaman dapat membedakan transisi dan dwell,
  menghasilkan sampel valid di tiap titik, serta menandai gap/data invalid.
- Verifikasi reboot ESP dikenali sebagai sesi baru oleh penggabung data host.

Dokumen PDF awal menggambarkan beberapa fitur yang belum aktif pada source awal.
Perubahan firmware ini mengaktifkan EA-DSRA dan monitoring nyata, tetapi hasil
penghematan energi dan kelulusan hardware tetap memerlukan pengukuran baru.

# Laporan revisi GUI 04 — 10 Oktober 2026

## Hasil perubahan

Navigasi sekarang hanya terpadu pada kamera. Pilihan Terpadu/Panel dihapus; orientasi robot, depth dan kompas tidak lagi memiliki sekat card. Satu lapisan latar transparan tipis memberi kontras, dengan blur pada latar saja. Instrumen dan angka tetap tajam. Attitude indicator transparan tetap tersedia saat kamera diperbesar.

Grafik diganti menjadi histori titik pembacaan dengan garis, skala nilai adaptif, label waktu dan detail titik. Detail menampilkan waktu, sequence, nilai/unit, depth, validity dan stabilitas. Pemilihan tersedia melalui hover, sentuh atau panah keyboard saat grafik fokus. Rentang 1/5/15 menit dan tombol bekukan hanya mengubah tampilan; pengumpulan data terus berjalan. OFF/invalid membuat celah, bukan angka nol; histori sebelumnya dipertahankan. Periode tanpa histori tetap kosong. Histori preview dibatasi 900 titik per kanal dan tetap berlabel simulasi.

## Penyesuaian yang didasarkan pada kode

| Acuan source | Perubahan preview dan maknanya |
|---|---|
| `ros2_ws/src/tyrant_interfaces/msg/MissionCommand.msg`, `ros2_ws/src/tyrant_mission_host/tyrant_mission_host/core.py` | Tambahan effort (%), timeout (s) dan toleransi per langkah (m/°). Effort gerakan nol serta timeout yang tidak melebihi durasi WAIT/SURGE/SWAY ditolak. Pengaturan dikunci selama misi; ID langkah bertahan setelah pengurutan. |
| `firmware/esp/src/main.cpp`, `firmware/esp/src/power_controller.cpp` | Switch sensor menunggu ACK contoh sebelum mengganti status. Skenario heartbeat host ESP timeout menolak ON dengan SYSTEM_NOT_READY (5), tetapi menerima OFF saat transport masih tersedia. |
| `ros2_ws/src/tyrant_payload_interfaces/msg/SensorPowerStatus.msg` | Status confirmed berasal dari accepted/actual_enabled, bukan sekadar posisi switch. Actual enabled berarti commanded GPIO, bukan pengukuran suplai MOSFET. Saat transport putus tidak dibuat ACK board palsu. |
| `ros2_ws/src/tyrant_payload_interfaces/msg/PayloadWaterQuality.msg` | ON belum langsung menghasilkan nilai valid: INITIALIZING sampai sampel baru. OFF/invalid dikosongkan; histori tetap ada. |
| `ros2_ws/src/tyrant_payload_interfaces/msg/PayloadPower.msg` | Dua rail menampilkan watt selain volt/ampere. INA sensor mengukur rail bersama, bukan arus setiap sensor. |
| `ros2_ws/src/tyrant_interfaces/msg/SimpleState.msg` | Heading invalid dikosongkan di CSV, disertai heading_valid; depth dan penanda stabilitas tetap terpisah. |

CSV contoh bertambah dari 17 menjadi 21 kolom: `heading_valid`, `step_id`, `sampling_timing` dan `phase`. Nilai phase membedakan MOTION, AFTER_MOTION dan MANUAL_RECORD. CSV dan grafik tetap memakai data sintetis browser; tidak menghasilkan rosbag. Fokus grafik juga tidak mengaktifkan tombol gerak manual.

## Verifikasi

Pemeriksaan otomatis Chrome berhasil untuk navigasi tunggal dan blur latar saja; sensor pending/ACK; ON ditolak dan OFF diterima saat heartbeat ESP timeout; titik/detail/rentang/bekukan grafik; penolakan effort nol dan timeout tidak cukup; misi contoh selesai; CSV dengan 21 kolom; empat window dan kamera fullscreen pada 840×390, 390×840 dan 320×720. Tidak ditemukan overflow horizontal halaman atau error JavaScript pada skenario tersebut. Tampilan desktop juga diperiksa.

Ini pemeriksaan preview browser laptop. Gesture Pixel, controller fisik, webcam, tether, backend Jetson serta ACK board nyata belum diuji melalui GUI ini.

## Pekerjaan integrasi yang masih diperlukan

1. Perluas schema/validator/engine mission host untuk sampling selama atau setelah semua jenis langkah dan depth tidak stabil yang diberi penanda. Host saat ini masih membatasi sampling DIVE/SURFACE dan qualification depth. Perubahan preview belum mengubah perilaku host itu.
2. Gateway Jetson harus menjadi pemilik tunggal perintah, heartbeat, rekaman dan snapshot rencana; lakukan arbitration input antar-browser, pending/timeout/ACK nyata serta pembacaan kembali status board. Controller di browser masih pemeriksaan input, belum teleop yang dikualifikasi.
3. Konversi effort persen ke nilai [-1,1], yaw/toleransi derajat ke radian dan durasi detik ke milidetik sesuai kontrak. Simpan offset referensi yaw sebagai metadata; jangan mengubah yaw estimator. Effort/timeout/toleransi pada preview belum memengaruhi controller fisik dan gerakan contoh tetap dipercepat.
4. Rekaman riil harus menggunakan validity, sequence dan age per kanal untuk association depth/acquisition. Timestamp uptime ESP bukan UTC. Hindari menghitung snapshot telemetry berulang sebagai sampel sensor baru. Preview empat kanal serempak belum menjadi model acquisition sensor.
5. Hubungkan kamera riil, daftar sensor yang dipilih untuk misi, penyimpanan/export-import rencana dan data backend. Parameter tuning/ceiling thruster tetap memerlukan kontrak, ACK/readback dan enforcement Teensy; angka command thruster bukan measured thrust.

## Lingkup file

Perubahan berada pada `gui/mockup/index.html`, `gui/mockup/style.css`, `gui/mockup/app.js`, `gui/mockup/README.md`, PRD `docs/dokumentasi dan PRD/PRD_GUI_Tyrant_V1.0.md` serta laporan ini. Firmware Teensy/ESP, workspace ROS dan deployment Jetson tidak diubah.


## Review lanjutan setelah revisi 04

Sekat tipis dikembalikan atas permintaan pengguna antara orientasi 3D, depth dan yaw. Ini memperbarui keputusan tanpa sekat di awal laporan. Navigasi tetap terpadu dan transparan; blur hanya pada latar. Pemeriksaan layout 1440/840/390/320 px berhasil.

Pekerjaan berikutnya sudah dimulai melalui `gui/backend`: gateway read-only dengan GET `/api/state` untuk 15 stream ROS. Empat tes snapshot, pemuatan semua interface dari workspace dan uji HTTP gateway nyata berhasil. Data belum diterima tetap null/stale; NaN/Infinity dinormalisasi menjadi null, tanpa mengubah validity atau uptime board. API belum mengirim kontrol, heartbeat atau merekam; tidak ada perubahan firmware/node host/deployment Jetson. Frontend tetap SIM dan belum terhubung ke API. Petunjuk lengkap di `gui/backend/README.md`.

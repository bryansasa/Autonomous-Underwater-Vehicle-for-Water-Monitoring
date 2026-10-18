# Mockup GUI Tyrant

Empat window responsif untuk review PRD GUI: Operasi, Kontrol & Misi, Grafik & Rekaman, serta Diagnostik & Tuning. Semua aset tersedia lokal, tanpa CDN atau paket tambahan.

**Ini preview simulasi. Tidak ada koneksi ROS, serial, Jetson, kamera, atau aktuator.** Angka sensor, validitas, status mode, batas output dan hasil misi adalah data contoh. Tampilan 3D adalah model skematis orientasi, bukan model kendaraan atau posisi XY aktual.

## Membuka

Buka `index.html` di browser. Untuk preview melalui server lokal dari laptop:

```bash
cd /home/charisto/tyrant-simple/gui/mockup
python3 -m http.server 8088 --bind 127.0.0.1
```

Buka `http://127.0.0.1:8088`. Server ini hanya untuk preview lokal, bukan deployment backend Jetson atau akses HP. Untuk akses HP perlu jaringan/server yang dapat dijangkau, lalu uji origin dan Gamepad API sesuai PRD.

## Alur review

1. Operasi: ubah ON/OFF sensor. Perhatikan nilai menjadi kosong ketika OFF.
2. Kontrol & Misi: pilih MANUAL pada bar atas, lalu tahan Space dengan W/S, A/D, Q/E atau R/F untuk melihat input. Lepas Space atau pindah fokus menghasilkan netral. Keyboard tidak menangkap gerak ketika fokus pada formulir/tombol. Escape melakukan Stop contoh, kecuali ketika kamera diperbesar: Escape menutup tampilan kamera.
3. Controller laptop/HP: pilih sumber Controller untuk melihat axes perangkat yang terbaca browser. Mapping/deadman controller **belum dikualifikasi**; pada mockup hanya pemeriksaan input, tidak menjalankan gerak.
4. Pilih AUTO pada bar atas, lalu jalankan misi simulasi. Setiap langkah dipercepat menjadi sekitar tiga detik; toleransi, waktu stabil dan jumlah sampel hanya menunjukkan bentuk konfigurasi. Jumlah contoh/sensor bukan bukti bahwa seluruh sampel baru/valid telah dihimpun oleh host nyata.
5. Grafik & Rekaman: lihat grafik sintetis dan sampel contoh. Jalankan rekaman manual atau selesaikan misi, lalu unduh CSV berlabel `SIMULATED`. Maksimal 600 baris/sesi, 10 sesi dalam memori. Reload menghapus data preview. Tidak membuat rosbag.
6. Diagnostik: pilih data tidak valid/link terputus; nilai navigasi/kualitas air menjadi kosong, input netral dan misi aktif menjadi FAILED. Memulihkan skenario normal menghasilkan IDLE tanpa resume otomatis.
7. Tuning: Apply batas contoh hanya saat IDLE. Nilai gain hanya baca; LMPC belum tersedia. Apply tidak mengubah firmware dan tidak menghasilkan ACK board.

## Batas preview

- Tidak ada video nyata; panel kamera sengaja menampilkan placeholder.
- Monitoring daya adalah angka contoh. Pada kondisi data invalid/link putus, nilainya dikosongkan dan diberi label tidak valid/stale.
- Planner memuat effort, timeout dan toleransi per langkah. Freshness, snapshot rencana dan validator host riil belum terhubung; konfigurasi preview tidak menggerakkan controller board.
- Grafik memuat celah sintetis untuk menunjukkan data invalid, bukan histori board.
- Orientasi hanya mengikuti nilai contoh yang dapat diubah di Diagnostik. Belum ada estimator di browser.
- Deadman dan Stop berlaku pada state lokal satu browser; arbitration antar-browser belum diimplementasikan.
- Tidak menerapkan batas thruster atau tuning riil. Ini tetap membutuhkan interface, readback dan enforcement firmware.

Spesifikasi acuan: `docs/dokumentasi dan PRD/PRD_GUI_Tyrant_V1.0.md`.

## Pemeriksaan 10 Oktober 2026

Pengujian browser Chrome otomatis mencakup empat tab pada viewport 1440×900, 840×390, 390×840 dan 320×720 tanpa overflow horizontal halaman. Diperiksa pula sensor OFF, keyboard/deadman dan kehilangan fokus, Stop/SAFE, misi contoh selesai, unduhan CSV berlabel simulasi, abort saat link terputus, pemulihan ke IDLE tanpa resume, serta Apply batas contoh hanya saat IDLE. Tidak ditemukan error JavaScript dalam skenario tersebut. Tampilan desktop dan portrait HP diperiksa melalui screenshot.

Ini pengujian browser laptop dengan viewport HP, bukan pengujian perangkat Pixel/controller/Webcam/Jetson/tether riil.

## Revisi visual 02 · 10 Oktober 2026

Kamera menjadi pusat Operasi dengan overlay depth, heading, mode dan rekaman; instrumen orientasi/depth/kompas disatukan. Sensor tampil sebagai baris ringkas dengan switch daya dan umur data. Mode dipilih dari bar atas pada semua window. Log default menampilkan satu aktivitas terakhir dan dapat diperluas.

Fitur baru untuk review:

- Fullscreen kamera mengisi area browser melalui dialog modal. Stop dan mode tetap terlihat di dalamnya. Tutup atau Escape mengembalikan panel ke Operasi; Escape di luar dialog tetap Stop. Belum mengubah browser ke mode fullscreen OS.
- Kesiapan simulasi disertai alasan saat depth/attitude tidak valid atau link terputus. Ini bukan pemeriksaan kesiapan board nyata.
- Umur data menggunakan waktu monotonik penerimaan contoh. Saat skenario invalid/putus, timer terus bertambah dan nilai HUD menjadi kosong. OFF ditampilkan terpisah dari stale.
- Ringkasan misi pada Operasi menampilkan langkah, target/durasi, progress yang dipercepat, selisih depth dan jumlah contoh sintetis. Tombol Buka planner membuka window misi.

Pemeriksaan browser tambahan berhasil untuk buka/tutup/Escape/Stop pada fullscreen, alasan kesiapan, umur data yang bertambah setelah putus, ringkasan langkah/sampel/REC, log yang dapat diperluas, serta empat window dan dialog pada lebar 840/390/320 px. Tidak ditemukan error JavaScript dalam skenario tersebut. Desain ini menunggu review pengguna sebelum integrasi backend.

## Revisi 03 · navigasi, heading dan sampling

- Pada revisi 03 tersedia pilihan Terpadu/Panel. Revisi 04 menggantinya dengan navigasi terpadu saja, berupa overlay tipis tanpa sekat instrumen.
- Attitude indicator transparan mengikuti roll/pitch contoh, termasuk saat kamera diperbesar. Layout diuji pada beberapa ukuran browser; pinch zoom tidak diblokir oleh viewport/CSS. Gesture fisik Pixel belum diuji.
- Referensi yaw opsional: Arah sekarang = 0° menyimpan heading asli sebagai offset. Target relatif dikonversi ke heading asli; OFF mengembalikan kerangka default. Referensi dikunci selama misi aktif. Penjelasan ? awalnya tersembunyi.
- Semua langkah boleh sampling ON/OFF, selama gerak atau sesudah selesai. Panah atas/bawah mengurutkan langkah.
- Sampel dengan depth belum stabil tetap tampil. Penandanya memakai jendela riwayat depth yang dipilih dan rentang 0,05 m, bukan syarat untuk mengambil contoh. Tidak cukup riwayat juga ditandai BELUM STABIL. Kuota mode selama gerak tidak memperpanjang gerakan; jika kurang, hasil akhir simulasi FAILED.
- CSV simulasi menambah heading_raw_deg, yaw_mission_deg, yaw_reference_enabled, yaw_offset_deg, depth_stable. Sampel tabel adalah contoh serempak empat kanal, bukan model acquisition time sensor riil.

Backend host belum mendukung perluasan sampling ini: validator core.py masih membatasi DIVE/SURFACE dan qualification masih membutuhkan target depth/stabilisasi. ESP tidak perlu mengetahui jenis langkah untuk mempublikasikan telemetry. Kontrak plan/engine/recording host perlu diperluas dan diuji sebelum menghubungkan GUI. Firmware Teensy/ESP belum diubah pada revisi mockup ini.

Pemeriksaan revisi 03 berhasil: referensi 37°→0°, target relatif 90°→heading asli 127°, kembali ke acuan asli saat OFF, bantuan tersembunyi, kedua panah urutan, sampling semua enam jenis langkah, selama/sesudah, penanda BELUM STABIL tanpa menghalangi sampel, reference terkunci saat misi, CSV 17 kolom, serta overlay/fullscreen pada 840/390/320 px. Pengujian kuota yang tidak terpenuhi memastikan gerakan tidak diperpanjang diam-diam dan hasil ditandai FAILED. Layout sentuh 320 px dan tampilan Stop/REC di dialog diperiksa. Tidak ada error JavaScript pada skenario pengujian tersebut. Ini tetap emulasi browser, bukan uji gesture/controller/streaming di Pixel riil.


## Revisi 04 · overlay tipis, grafik dan kontrak board

Navigasi hanya terpadu pada kamera. Tidak ada pilihan Panel atau card terpisah antar-instrumen; blur hanya pada lapisan latar transparan. Model orientasi, kompas, indikator dan angka tetap tajam.

Grafik menyimpan histori contoh, menampilkan titik pembacaan, sumbu waktu/nilai dan detail titik lewat hover, sentuh atau tombol panah saat grafik fokus. Pilih rentang 1/5/15 menit dan Bekukan tampilan tanpa menghentikan pengumpulan data. OFF/invalid menjadi celah, bukan nol; histori lama tetap ada. Rentang yang belum memiliki data dibiarkan kosong. Histori grafik dibatasi 900 titik per kanal; angka dan waktu tetap sintetis.

Perbaikan sesuai kontrak Teensy/ESP:

- Planner menambah effort persen, timeout dan toleransi per langkah. Effort nol untuk gerakan serta timeout yang tidak melebihi durasi langkah berwaktu ditolak. ID langkah bertahan ketika urutan diubah. Pengaturan dikunci saat misi aktif; controller nyata belum menggunakannya.
- Switch sensor menunggu ACK contoh sebelum mengganti status terkonfirmasi. ON menampilkan INITIALIZING sampai pembacaan baru. Actual enabled adalah perintah GPIO, bukan bukti suplai listrik terukur.
- Diagnostik menyediakan skenario heartbeat host ESP timeout. Sesuai firmware, ON ditolak dengan SYSTEM_NOT_READY (5), sementara OFF diizinkan bila transport masih tersedia. Koneksi putus tidak dibuat seolah-olah menerima ACK penolakan board.
- Monitoring dua rail menampilkan watt selain volt/ampere. INA rail sensor merupakan satu monitor bersama, bukan arus individual empat sensor.
- CSV kini 21 kolom: ditambahkan heading_valid, step_id, sampling_timing dan phase. Heading invalid dikosongkan; depth tidak stabil tetap diberi penanda.
- Fokus pada grafik tidak mengaktifkan keyboard teleop.

Pemeriksaan Chrome otomatis berhasil untuk overlay dan blur latar saja, pending/ACK sensor, penolakan ON dan penerimaan OFF saat heartbeat ESP timeout, titik/detail/rentang/bekukan grafik, validasi effort/timeout, misi contoh selesai, CSV 21 kolom, serta empat window dan fullscreen pada viewport 840×390, 390×840 dan 320×720. Tidak ditemukan error JavaScript. Pemeriksaan sebelumnya pada revisi 03 merupakan catatan historis, termasuk format CSV 17 kolom yang sudah diganti.

Laporan rinci: `docs/gui_mockup_review_2026-10-10.md`. Firmware Teensy/ESP, workspace ROS dan deployment Jetson tidak diubah pada revisi ini.


## Penyesuaian setelah revisi 04

Sesuai review pengguna, sekat tipis dikembalikan antara orientasi 3D, depth dan yaw/kompas. Desktop memakai garis vertikal; HP memakai garis horizontal di bawah orientasi dan vertikal antara depth/kompas. Tetap satu navigasi terpadu, latar transparan dan instrumen tajam. Pemeriksaan 1440/840/390/320 px lulus tanpa overflow.

Fondasi telemetry nyata berada di `gui/backend/README.md`; frontend ini masih SIM sampai koneksi API diterapkan.

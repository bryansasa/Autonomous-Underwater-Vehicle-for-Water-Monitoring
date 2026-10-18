# Deployment host misi dan payload ke Jetson — 10 Oktober 2026

Host misi, interface payload terpisah, serta simulasi sudah dibangun dan
diuji pada Jetson ARM64. Container `tyrant-mission-dev` memakai workspace
`/home/nvidia/ros2_docker/mission_ws`; workspace dan build sebelumnya tetap
disimpan. Agent micro-ROS ARM64 lama digunakan kembali.

Lima paket build berhasil, 37 tes logika lulus, dan tes runtime ROS dengan
endpoint tiruan lulus termasuk recorder dan penanganan state invalid/stale.
Misi board HIL `20261009T183003Z_e22db023` juga berhasil: lima langkah selesai,
dua titik mendapat tiga sampel valid untuk tiap sensor, dan bag berisi
15.786 pesan selama 81,08 detik. Sensor simulasi OFF setelah misi; mode SAFE.
Tidak ada disconnect/reconnect selama rekaman dan output fisik nonaktif.

Alias serial `/dev/tyrant-esp` dan `/dev/tyrant-teensy` sudah dipasang pada
host Jetson berdasarkan nomor serial board. Di container, gunakan prefix
`/host-dev/`. Host launch mengirim heartbeat ke kedua board dan membuka dua
agent; belum ada autostart host dua board setelah boot.

Masalah yang diselesaikan: jam Jetson tertinggal (disesuaikan dengan laptop),
konflik plugin pytest (plugin tambahan dinonaktifkan untuk tes), serta proses
agent tertinggal setelah shutdown wrapper `ros2 run` (launch menjalankan
binary agent langsung; shutdown ulang berhasil tanpa agent tertinggal).

Plant, host misi, kedua agent, dan heartbeat pengujian sudah dihentikan.
Container baru tetap idle. Firmware kedua board tidak diubah dalam sesi ini.

## Lanjutan: autostart dan reboot

Container `tyrant-mission` sekarang aktif dengan dua agent, heartbeat host,
dan plant HIL otomatis. Setiap startup host tetap IDLE; misi tidak otomatis
dimulai atau dilanjutkan. Agent ESP yang sengaja dihentikan berhasil dipulihkan
tanpa restart host/Teensy. Restart saat misi aktif menutup bag normal sebagai
STOPPED, dengan empat ACK OFF sensor dan mode SAFE.

Reboot Jetson berhasil diuji: container menyala sendiri, alias USB tetap benar
meskipun nomor tty bertukar, kedua heartbeat sehat, dan NTP tersinkronisasi.
Konfigurasi server NTP disimpan secara persisten. Kondisi akhir sesi lanjutan
adalah container autostart aktif, misi IDLE, serta container lama berhenti.

Panduan harian dan bukti: [autostart Jetson](../jetson_autostart.md).
Sensor riil, thruster riil, GUI, webcam, dan LMPC belum dinyatakan tervalidasi
oleh pengujian ini. Profil container saat ini tetap HIL/simulasi.

Perintah lengkap, hasil, serta tautan bukti ada di
[panduan deployment](../jetson_payload_mission_deployment.md).

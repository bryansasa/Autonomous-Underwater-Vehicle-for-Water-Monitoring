# Tyrant-AQ: Autonomous Underwater Vehicle (AUV) for Water Quality Monitoring

[![Telkom University](https://img.shields.io/badge/Telkom%20University-FTE%20Elektro-red.svg)](https://telkomuniversity.ac.id/)
[![Laboratory](https://img.shields.io/badge/Laboratory-SPELL%20Lab-blue.svg)](#)
[![ROS 2](https://img.shields.io/badge/ROS%202-Humble%20Hawksbill-green.svg)](https://docs.ros.org/en/humble/)
[![Hardware](https://img.shields.io/badge/Hardware-Teensy%204.1%20%7C%20ESP32--S3%20%7C%20Jetson-orange.svg)](#)
[![Field Site](https://img.shields.io/badge/Field%20Site-Saguling%20Reservoir-teal.svg)](#)

Dokumentasi dan basis kode terpadu untuk penelitian Tugas Akhir wahana selam nirawak **Tyrant-AQ AUV** dalam misi pemantauan kualitas air di Waduk Saguling, Jawa Barat.

---

* **Bryan Gabriel Izaac Sasabone** (NIM: 101022300195)
* **Charisto Brilliant R.P** (NIM: 101022330187)
* **Laboratorium:** *Signal Processing & Embedded Logic Laboratory (SPELL Lab)*  
  Fakultas Teknik Elektro, Universitas Telkom

---

## 🏛️ Arsitektur Sistem

```
+---------------------------------------------------------------------------------+
|                              LAPTOP OPERATOR / GCS                              |
|  +-------------------------------------+   +---------------------------------+  |
|  |     Desktop GCS (PyQt5 + 3D STL)    |   |    Web Telemetry Console        |  |
|  | - Tab 1: Telemetri & 3D STL Visual  |   | - 4-Window Three.js STL Viewer  |  |
|  | - Tab 2: Kontrol Manual & 9-Col Misi|   | - Polling REST API /api/state   |  |
|  +------------------^------------------+   +----------------^----------------+  |
+---------------------|---------------------------------------|-------------------+
                      | TCP Port 9000                         | HTTP Port 8090
                      v                                       v
+---------------------------------------------------------------------------------+
|                             ON-BOARD JETSON (LINUX)                             |
|  +-------------------------------------+   +---------------------------------+  |
|  |       gcs_ros2_bridge.py            |   |   gui/backend/server.py         |  |
|  |  (Jembatan ROS 2 <-> GCS TCP:9000)  |   |  (HTTP REST Gateway Port 8090)  |  |
|  +------------------^------------------+   +----------------^----------------+  |
|                     |                                       |                   |
|                     +-------------------+-------------------+                   |
|                                         | Topic ROS 2                           |
|  +--------------------------------------v------------------------------------+  |
|  |                 tyrant_mission_host & tyrant_teleop                       |  |
|  |  - Supervisor Heartbeat 10 Hz        - Failsafe Timeout 250 ms            |  |
|  |  - Perekaman Rosbag Ilmiah           - Jembatan Controller PS4/DS4 (Joy)  |  |
|  +-------------------^--------------------------------------^----------------+  |
+----------------------|--------------------------------------|-------------------+
                       | USB (/dev/tyrant-teensy)             | USB (/dev/tyrant-esp)
                       v                                      v
       +-------------------------------+      +-------------------------------+
       |       TEENSY 4.1 FISIK        |      |       ESP32-S3 FISIK          |
       |  - Navigasi 6-DOF & IMU/Depth |      |  - micro-ROS (Humble)         |
       |  - Kendali Pendorong Manual   |      |  - Atlas EZO (pH, EC, DO, Temp|
       |  - Failsafe 250 ms Neutral    |      |  - Dual INA226 (Thruster+Rel) |
       |  - Kontrak: /tyrant/simple... |      |  - On-chip EA-DSRA Modulation |
       +-------------------------------+      +-------------------------------+
```

---

## 📁 Struktur Repositori

| Direktori / File | Deskripsi |
| :--- | :--- |
| `GCS-Submersible/` | Aplikasi **Desktop Ground Control Station (GCS)** berbasis PyQt5 dengan visualisasi 3D STL interaktif, tactical mission planner 9 kolom, kalibrasi *Set Surface*, dan jembatan TCP/ROS 2. |
| `Tyrant-simple-main/` | Basis kode utama AUV mencakup firmware Teensy 4.1, firmware ESP32-S3 micro-ROS, ROS 2 workspace (`ros2_ws`), dan Web Console Telemetri (`gui/mockup`). |
| `GUI Kalibrasi/` | Antarmuka grafis desktop terdedikasi untuk kalibrasi modul sensor Atlas Scientific EZO (pH, EC, Dissolved Oxygen, Suhu). |
| `simulasi_ea_dsra/` | Skrip simulasi matematis & pemodelan algoritma adaptasi sampling rate kualitas air berdasarkan fluktuasi air dan sisa kapasitas baterai LiPo 6S. |
| `ros2_ws/` | Paket definisi pesan ROS 2 (`tyrant_payload_interfaces`) mencakup 6 skema pesan telemetri kustom. |
| `PANDUAN_INTEGRASI_HARDWARE_DAN_GCS.pdf` | Dokumen panduan langkah-demi-langkah integrasi hardware mikrokontroler, udev rules Jetson, command execution, dan failsafe operasi. |
| `IMPLEMENTATION_PLAN.pdf` | Dokumen rencana implementasi dan arsitektur integrasi sistem telemetri AUV. |

---

## 🚀 Panduan Menjalankan Sistem

### 1. Menjalankan Desktop Ground Control Station (GCS)
Pada laptop Windows:
1. Masuk ke folder `GCS-Submersible`.
2. Jalankan berkas launcher:
   ```cmd
   BUKA_GCS_SUBMERSIBLE.bat
   ```
3. Masukkan IP Jetson target dan Port `9000`, lalu klik **CONNECT**.
4. Gunakan **Tab 1** untuk memantau sikap orientasi 3D dan kedalaman. Gunakan **Tab 2** untuk kendali manual, nol permukaan air (*Set Surface*), dan penyusunan tahapan misi lapangan.

### 2. Menjalankan Web Telemetry Console
Pada laptop operator atau browser mobile:
1. Masuk ke `Tyrant-simple-main/gui/mockup/`.
2. Buka berkas `index.html` menggunakan browser Chrome/Edge, atau jalankan server lokal:
   ```bash
   npx serve .
   ```
3. Web console secara otomatis melakukan *handshake* ke gateway ROS 2 di `http://127.0.0.1:8090/api/state`. Jika terhubung, badge otomatis berubah menjadi **● LIVE · ROS 2**.

### 3. Menjalankan Kendali Manual Controller (DualShock 4 / DS4)
1. Hubungkan controller DS4 ke Jetson (via Bluetooth atau kabel Micro-USB).
2. Jalankan launcher teleop ROS 2 di Jetson:
   ```bash
   ros2 launch tyrant_teleop ps_teleop.launch.py
   ```
3. **Pemetaan Tombol:**
   * **L1**: Tombol *Deadman Switch* (wajib ditahan saat menggerakkan robot).
   * **Stik Kiri**: Maju/Mundur (*Surge*) dan Geser Kiri/Kanan (*Sway*).
   * **Stik Kanan**: Putar Haluan (*Yaw*).
   * **Trigger R2 / L2**: Menyelam (*Heave Down*) / Naik Permukaan (*Heave Up*).
   * **✖ (Cross)**: Mode MANUAL | **◼ (Square)**: Mode IDLE | **⬤ (Circle)**: Emergency SAFE.

---

## 🛡️ Standar Keselamatan (Failsafe)
1. **Deadman Switch:** Perintah pendorong manual hanya dieksekusi selama tombol pengaman ditekan. Pelepasan tombol seketika menetralkan seluruh pendorong dalam 250 ms.
2. **Heartbeat Supervisor (10 Hz):** Jetson mengirimkan denyut nadi pengawas ke kedua mikrokontroler. Jika komunikasi terputus >1000 ms, sistem beralih ke proteksi *SAFE*.
3. **Proteksi Baterai (EA-DSRA):** Jika kapasitas baterai LiPo 6S turun di bawah ambang kritis ($SoC \le 30\%$), interval sensor kualitas air dimodulasi ke mode hemat daya (1–5 detik).

---

*SPELL Laboratory — Fakultas Teknik Elektro, Universitas Telkom (2026)*

# 📌 RESUME SESI & STATUS PROYEK TYRANT-AQ AUV

**Sesi Percakapan Antigravity:** `681ce70e-82e3-4a56-bc47-63f2391395b6`  
**Proyek:** Autonomous Underwater Vehicle (AUV) for Water Quality Monitoring — Waduk Saguling  
**Laboratorium:** SPELL Laboratory (Signal Processing & Embedded Logic Laboratory), Telkom University  
**Pengembang:** Bryan Gabriel Izaac Sasabone & Charisto Brilliant R.P  
**Status GitHub:** [https://github.com/bryansasa/Autonomous-Underwater-Vehicle-for-Water-Monitoring](https://github.com/bryansasa/Autonomous-Underwater-Vehicle-for-Water-Monitoring) (Branch `main`)  
**Waktu Pembaruan Terakhir:** Oktober 2026

---

## 🚀 1. Ringkasan Pencapaian & Status Terkini

### A. Web Telemetry Console (`Tyrant-simple-main/gui/mockup/`)
* **3D STL Interactive Viewer (Three.js):** Memuat model `finaltes2.STL` secara lokal dengan rotasi interaktif, goyangan air alami (*water buoyancy oscillation*), dan sinkronisasi sikap wahana (Roll, Pitch, Yaw).
* **Live Webcam & Jetson Video Stream:** Dilengkapi tombol toggle `📹 Buka Kamera` yang langsung mengaktifkan webcam laptop/USB lokal (resolusi 720p/1080p 30 FPS).
* **HUD Navigasi Melayang:** Garis sayap horizon sikap kapal (*attitude overlay*), angka kedalaman (*depth*), dan kompas haluan melayang transparan di atas video live.
* **Simulasi Air Bergerak (*Dynamic Underwater Simulation*):** Jika kamera mati, panel memutar animasi lingkungan bawah air alami (pantulan cahaya caustics dan gelembung air mengapung).
* **Auto-Detect Gateway ROS 2:** Polling otomatis ke `http://127.0.0.1:8090/api/state` setiap 500 ms; beralih otomatis dari `SIMULASI · OFFLINE` ke `● LIVE · ROS 2` saat backend Jetson terdeteksi.
* **Branding:** Terintegrasi logo resmi SPELL Laboratory di header.

### B. Desktop Ground Control Station (`GCS-Submersible/`)
* **Restrukturisasi Tab 1:** Panel matriks pendorong telah dipindahkan agar ruang visualisasi 3D STL CAD (OpenGL) menjadi sangat lega dan fokus pada navigasi sikap.
* **Penyelarasan Tab 2:** Mengimplementasikan kendali manual pendorong, kalibrasi nol permukaan (*Set Surface Reference*), dan *Tactical Mission Planner* 9 kolom.
* **Branding:** Logo resmi SPELL Laboratory tersemat di Quick Action Bar atas.
* **Standalone Executable (.exe):** Berhasil dibuild dengan PyInstaller menjadi bundle mandiri di `GCS-Submersible/dist/Tyrant-AQ_GCS/Tyrant-AQ_GCS.exe` lengkap dengan launcher `Jalankan_GCS.bat`.

### C. Kendali Lapangan & Failsafe
* **Controller DualShock 4 (DS4):** Modul `tyrant_teleop` (`ps_controller.yaml`) membaca DS4 via Bluetooth/USB:
  * `L1`: Tombol **Deadman Switch** (wajib ditahan, lepas = motor netral dalam 250 ms).
  * `Stik Kiri`: Surge (Maju/Mundur) & Sway (Geser Kiri/Kanan).
  * `Stik Kanan`: Yaw (Belok Kiri/Kanan).
  * `Trigger R2/L2`: Heave (Menyelam / Naik ke Permukaan).
  * `✖ / ◼ / ⬤ / ▲`: MANUAL / IDLE / SAFE Emergency / Set Surface.

### D. Firmware & Algoritma Adaptif EA-DSRA
* **ESP32-S3 (firmware/esp):** micro-ROS Humble, 4 sensor kualitas air Atlas Scientific EZO (pH, DO, EC, Temp), power-gating MOSFET, monitoring daya ganda (INA226 Thruster 6S & Rel Sensor), dan algoritma on-chip EA-DSRA memodulasi interval sampling 1.0–5.0 detik dengan proteksi DO kritis ($DO \le 2.0\text{ mg/L}$).
* **Teensy 4.1 (firmware/teensy):** Estimasi kedalaman Bar30, IMU 9-DOF, alokasi pendorong (TAM), dan timeout perintah manual 250 ms.

### E. Repositori GitHub
* Repositori bersih dan terstruktur rapi di branch `main`.
* Folder besar non-inti (`GUI Kalibrasi/`, `simulasi_ea_dsra/`, `ros2_ws/`, arsip `.rar`, file build `dist/`) otomatis difilter oleh `.gitignore` sehingga ukuran repo ringan dan aman.
* Berkas panduan PDF (`PANDUAN_INTEGRASI_HARDWARE_DAN_GCS.pdf` dengan kode berformat kontras tinggi, `IMPLEMENTATION_PLAN.pdf`, `PANDUAN_GAZEBO_BLACK_SCREEN_UBUNTU.pdf`) dan dokumentasi markdown tersimpan aman di repositori.

---

## 💻 2. Panduan Cepat Perintah Terminal (Cheatsheet)

### Menjalankan Web Console (Browser):
```powershell
cd "d:\Tugas Akhir\Tugas-Akhir-YEN\Program-YEN\Tyrant-simple-main\gui\mockup"
.\BUKA_CONSOLE_WEB.bat
# Akses: http://127.0.0.1:8088
```

### Menjalankan Desktop GCS:
```powershell
cd "d:\Tugas Akhir\Tugas-Akhir-YEN\Program-YEN\GCS-Submersible"
.\BUKA_GCS_SUBMERSIBLE.bat
# Atau via Python:
python main.py
```

### Menjalankan Jembatan ROS 2 & Mission Host di Jetson:
```bash
# Terminal 1: Mission Host & micro-ROS Agents
source /opt/ros/humble/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
ros2 launch tyrant_mission_host mission_host.launch.py start_agents:=true

# Terminal 2: Gateway HTTP untuk Web Console (Port 8090)
cd /home/charisto/tyrant-simple/gui/backend
python3 server.py --bind 0.0.0.0 --port 8090 --payload-namespace /tyrant/payload

# Terminal 3: Kendali Teleop Controller PS4/DS4
ros2 launch tyrant_teleop ps_teleop.launch.py
```

---

## 🎯 3. Langkah Berikutnya (Next Steps)
1. Uji koneksi fisik mikrokontroler Teensy 4.1 dan ESP32-S3 ke Jetson menggunakan kabel USB tether.
2. Pasang aturan udev statis di Jetson (`/etc/udev/rules.d/99-tyrant.rules`).
3. Lakukan pengujian kendali manual stik DS4 di kolam uji / waduk.

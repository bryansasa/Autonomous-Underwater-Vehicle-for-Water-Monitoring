# Tyrant-AQ AUV Ground Control Station (GCS) - QGC Fly View Inspired

Aplikasi antarmuka pemantauan dan kendali modern berbasis Python & PyQt5 untuk **Wahana Submersible Otonom Pemantau Kualitas Air Waduk (Saguling)**.

---

## Fitur Utama

1. **Primary Flight Display (PFD) HUD**:
   - Artificial Horizon (Pitch & Roll dari MARG IMU WitMotion HWT905)
   - Heading Compass Tape (Yaw 0°–360°) dengan Target Heading Bug
   - Depth Ladder Tape (0.00–5.00 m) dengan pembacaan sensor tekanan Bar30
   - EKF Disturbance Observer Vector ($|\hat{d}|$ gaya arus fluida)

2. **Water Quality Matrix Dashboard**:
   - Pemantauan 4 parameter: pH, Dissolved Oxygen (DO), Suhu, dan Konduktivitas (TDS)
   - Indikator evaluasi otomatis terhadap **Baku Mutu Air PP No. 22 / 2021 & Permenkes No. 2 / 2023**
   - Komparasi sinyal mentah (*RAW*) vs hasil rekonstruksi adaptif (*SC*)

3. **6-Thruster Propulsion & LMPC Force Monitor**:
   - Visualisasi grafis 6 thruster PWM (1100–1900 µs, 1500 µs netral)
   - 4 DoF Virtual Forces: $\tau_x$ (*Surge*), $\tau_y$ (*Sway*), $\tau_z$ (*Heave*), $M_\psi$ (*Yaw*)
   - Metrik waktu komputasi pengontrol LMPC Quadratic Programming (*WCET < 100 ms*)

4. **Power Management & EA-DSRA Display**:
   - Tegangan baterai terfilter Kalman 1D vs pembacaan mentah INA226
   - Indikator State of Charge (*SoC %*)
   - Faktor pembobotan penalti energi $W_{ea}$
   - Interval adaptif $T_{ea}$ dinamis per kanal sensor

5. **Hardware-Accelerated Real-Time Oscilloscope**:
   - Grafik telemetri multi-kanal berbasis `PyQtGraph` (60 FPS bebas lag)
   - Channel selector interaktif & buffer pembersihan instan

6. **Kontrol Misi & Input Fleksibel**:
   - Mode operasi: *Manual*, *Depth Hold*, *LMPC Station-Keeping*, *Autonomous Step-Profiling Mission*
   - Kontrol Gamepad / Joystick Analog 4 DoF + Keyboard Deadman Switch (`W/S/A/D/Q/E/Panah`)
   - Emergency Physical Kill Switch (*Relay Contactor 200A cut-off*)

---

## Cara Menjalankan

### A. Di Windows
1. **Instalasi Dependensi (Pertama kali):**
   Klik dua kali `install_dependencies.bat` atau via terminal:
   ```cmd
   pip install -r requirements.txt
   ```
2. **Jalankan Aplikasi GCS:**
   Klik dua kali `run_gcs.bat` atau via terminal:
   ```cmd
   python main.py
   ```

### B. Di Linux / Ubuntu (Native - Tanpa Wine!)
> **Penting:** Aplikasi ini berbasis Python murni & PyQt5, sehingga berjalan secara native di Ubuntu tanpa emulator Wine.
1. **Instalasi Dependensi di Ubuntu (Cukup Sekali):**
   ```bash
   bash install_dependencies_ubuntu.sh
   ```
   Atau jika install manual via apt:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-pyqt5 python3-pyqt5.qtopengl python3-pyqtgraph python3-serial python3-numpy python3-reportlab python3-websockets libxcb-cursor0 libxcb-xinerama0 libgl1 libglib2.0-0
   pip3 install -r requirements.txt
   ```
2. **Jalankan Aplikasi GCS:**
   ```bash
   bash run_gcs.sh
   # atau langsung
   python3 main.py
   ```

---

## Menjalankan Simulator Hardware (Uji Coba Lokal)
Jika wahana fisik belum tersambung, jalankan mock simulator Teensy di terminal terpisah:
- **Windows:** Klik dua kali `run_simulator.bat`
- **Linux/Ubuntu:** `python3 mock_teensy_streamer.py`

Lalu pada aplikasi GCS, pastikan IP adalah `127.0.0.1` dan port `9000`, kemudian klik **CONNECT**.


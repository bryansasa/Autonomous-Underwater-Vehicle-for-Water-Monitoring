# DOKUMEN RENCANA IMPLEMENTASI & ROADMAP PENGEMBANGAN GCS
## Wahana Submersible Otonom Pemantau Kualitas Air Waduk Saguling (Tyrant-AQ)

**Penulis / Pengembang:**
1. **Bryan Gabriel Izaac Sasabone** (NIM: 101022300195)
2. **Charisto Brilliant R.P** (NIM: 101022330187)

**Program Studi:** S1 Teknik Elektro, Fakultas Teknik Elektro, Telkom University  
**Fokus Penelitian:** Sistem Kendali Pergerakan Berbasis Decoupled LMPC + EKF dan Akuisisi Adaptif Sadar Energi Berbasis EA-DSRA + Filter Kalman 1D pada Arsitektur Twin-Hull 6 Thruster  
**Versi Dokumen:** v2.0 (Edisi Lengkap: 3D Navigasi, Kamera Feed, Foxglove Studio Bridge, Mode Real/Dummy, dan Roadmap Masa Depan)

---

## 1. PENDAHULUAN & TUJUAN PERANCANGAN

Pengembangan antarmuka **Ground Control Station (GCS)** ini bertujuan untuk menyediakan sarana operasional yang ramah pengguna (*user-friendly*), praktis, dan berkinerja tinggi guna memantau kualitas air Waduk Saguling serta mengendalikan pergerakan wahana submersible secara real-time.

Struktur antarmuka dirancang bersih dalam **3 Tab Utama**:
1. **Tab 1: Kontrol Wahana, Monitor Sensor & Rekam Data** — Dashboard pemantauan seluruh sensor, kendali manual *Deadman Switch* (W/S), LMPC Station-Keeping, visualisasi **Orientasi 3D Navigasi** / **PFD Horizon 2D** / **Live Camera Feed**, dan perekaman CSV/MCAP dengan *live timer*.
2. **Tab 2: Grafik Sensor Realtime** — Visualisasi 4 slot grafik interaktif berbasis PyQtGraph (60 FPS) yang dapat dipilih parameternya secara dinamis (pH, DO, Suhu, Konduktivitas, Kedalaman, Arus, Baterai, TBM, dan sinyal RAW).
3. **Tab 3: Import & Analisis CSV** — Fitur analisis data offline untuk memuat file CSV hasil misi, meninjau tabel data, menghitung statistik (*Min, Max, Mean, Std*), dan mengeplot multi-kurva interaktif.

---

## 2. MATRIKS CHECKLIST FITUR SISTEM (CURRENT FEATURES)

| Kategori | Nama Fitur | Deskripsi Teknis | Status |
| :--- | :--- | :--- | :---: |
| **Kontrol & Dashboard** | **Kontrol Manual 6-DOF (Deadman Switch)** | Kontrol gerak 6 derajat kebebasan: Translasi (Surge, Sway, Heave) dan Rotasi (Roll, Pitch, Yaw) via GUI & keyboard dengan safety release otomatis. | **[✓] Selesai** |
| **Kontrol & Dashboard** | **Decoupled LMPC Control** | Kontrol kedalaman otomatis (Station-Keeping) dengan target depth setpoint, tuning horizon Np & Nc. | **[✓] Selesai** |
| **Kontrol & Dashboard** | **8 Sensor Metric Cards** | Kartu pembacaan nilai real-time: Kedalaman, DO, pH, Suhu, Konduktivitas, Baterai, Arus, dan Error Z. | **[✓] Selesai** |
| **Kontrol & Dashboard** | **6-Thruster Propulsion Matrix** | Indikator bar grafis PWM real-time untuk 4 thruster horizontal dan 2 thruster vertikal. | **[✓] Selesai** |
| **Kontrol & Dashboard** | **CSV Logger & Live Timer** | Perekam data CSV otomatis dengan nama file kustom dan indikator timer digital aktif (`HH:MM:SS`). | **[✓] Selesai** |
| **Navigasi Visual** | **Orientasi 3D Navigasi** | Model 3D Twin-Hull AUV berotasi 6-DOF (Roll, Pitch, Yaw) real-time dengan interaksi mouse orbit drag & zoom. | **[✓] Selesai** |
| **Navigasi Visual** | **PFD Horizon HUD 2D** | Primary Flight Display dengan Artificial Horizon pitch/roll, depth ladder tape, heading tape, & vektor arus EKF. | **[✓] Selesai** |
| **Vision & Kamera** | **Input Live Camera Feed** | Stream video kamera USB underwater / RTSP / Simulasi dengan overlay Tactical HUD dan tombol Snapshot 1-klik. | **[✓] Selesai** |
| **Simulasi & Hardware** | **Dual Mode (Real vs Dummy)** | Switch 1-klik antara Hardware Real (Ethernet TCP/UDP atau USB Serial) dan Engine Simulator Internal built-in. | **[✓] Selesai** |
| **Observabilitas** | **Foxglove Studio Bridge** | WebSocket server `ws://localhost:8765` broadcast telemetri real-time, export log MCAP, & preset layout. | **[✓] Selesai** |
| **Desain Antarmuka** | **Auto-Scalable & Responsive GUI** | Layout adaptif berbasis dynamic stretch & high-DPI scaling yang responsif pada berbagai ukuran layar. | **[✓] Selesai** |
| **Grafik Sensor** | **4-Slot Dynamic Plots (Tab 2)** | Visualisasi multi-kanal 60 FPS bebas lag berbasis PyQtGraph dengan pilihan sensor via checkbox. | **[✓] Selesai** |
| **Analisis Offline** | **CSV Importer & Stats (Tab 3)** | Plot multi-kurva interaktif dari berkas log CSV, kalkulasi instan Min/Max/Mean/Std, & tabel pratinjau. | **[✓] Selesai** |

---

## 3. INTEGRASI FOXGLOVE STUDIO

### 3.1 Arsitektur Companion WebSocket Bridge
GCS menyediakan background WebSocket Server pada `ws://localhost:8765`:
- **Channel Siaran:**
  - `/auv/attitude` : Sudut Roll, Pitch, Yaw, dan Kedalaman $Z$.
  - `/auv/water_quality` : Nilai pH, Dissolved Oxygen (mg/L), Suhu (°C), dan Konduktivitas (µS/cm).
  - `/auv/thrusters` : Nilai PWM Motor Thruster 1 s/d 6.
  - `/auv/power` : Tegangan Baterai (V), Arus (A), dan SoC Kalman (%).
  - `/auv/diagnostics` : LMPC error, WCET compute time, dan gangguan arus (Surge/Sway).
- **Format MCAP (.mcap):** Ekspor log misi format biner standar robotika untuk playback interaktif di Foxglove Studio.
- **Preset Konfigurasi:** Berkas `config/foxglove_preset.json` siap di-import untuk tata letak visual instan.

---

## 4. ROADMAP UPGRADE FITUR MASA DEPAN (IN FUTURE UPGRADES)

Berikut adalah rencana roadmap pengembangan lanjutan untuk meningkatkan otonomi, kecerdasan buatan, dan keandalan wahana *Tyrant-AQ*:

| No | Fitur Masa Depan | Fokus Inovasi | Spesifikasi & Rencana Implementasi | Prioritas |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **Autonomous Waypoint Mission Planner** | Navigasi Waypoint 3D & Acoustic Tracking | Perancangan rute misi otomatis berbasis peta satelit waduk (QGIS / Leaflet), integrasi sensor akustik USBL / DVL untuk estimasi koordinat bawah air tanpa sinyal GPS. | **Tinggi (P1)** |
| **2** | **AI Underwater Computer Vision** | Deteksi Objek & Kekeruhan Air (YOLOv8/11) | Pemrosesan citra kamera bawah air real-time untuk deteksi sampah plastik, gulma eceng gondok, sedimentasi, dan estimasi kekeruhan air (*turbidity index*) berbasis AI on-edge. | **Tinggi (P1)** |
| **3** | **3D Bathymetric Heatmap & Contour** | Pemetaan Batimetri & Kualitas Air 3D | Algoritma interpolasi spasial (Kriging / IDW) untuk menghasilkan peta kontur sebaran pH, DO, dan suhu 3D sepanjang kedalaman dan area waduk. | **Sedang (P2)** |
| **4** | **Smart Failsafe & Geo-Fencing** | Prosedur Darurat Otonom | Pengapungan darurat otomatis (*Auto Surface Blow / Drop Weight*) saat baterai kritis (<15%), kehilangan heartbeat tethering >5s, atau kebocoran kompartemen elektronik. | **Tinggi (P1)** |
| **5** | **Cloud IoT Sync & Web Dashboard** | Sinkronisasi Cloud Telemetri | Pengunggahan data telemetri otomatis ke cloud broker (MQTT / Firebase / InfluxDB) untuk pemantauan multi-user jarak jauh via browser internet. | **Sedang (P2)** |
| **6** | **Wireless Optical / Acoustic Telemetry** | Komunikasi Nirkabel Bawah Air | Integrasi transreceiver optik nirkabel (Blue-Green LED) berkecepatan tinggi untuk transfer data nirkabel saat wahana beroperasi tanpa kabel tethering. | **Eksplorasi (P3)** |

---

## 5. PANDUAN PENGOPERASIAN GCS

1. **Menjalankan GCS:** Jalankan `python main.py` atau klik [run_gcs.bat](file:///d:/Tugas%20Akhir/Tugas-Akhir-YEN/Program-YEN/GCS-Submersible/run_gcs.bat).
2. **Pilih Mode Operasi:**
   - Pilih **`Mode Simulasi (Dummy)`** untuk uji coba sistem tanpa hardware fisik.
   - Pilih **`Mode Real (Hardware)`** lalu klik *Set & Konek* untuk terhubung ke Teensy 4.1.
3. **Navigasi & Visual:**
   - Klik tab pilihan di atas panel navigasi untuk beralih antara **[ Orientasi 3D ]**, **[ PFD Horizon 2D ]**, dan **[ Live Camera Feed ]**.
   - Gunakan mouse drag untuk memutar sudut pandang 3D dan scroll untuk zoom in/out.
4. **Kontrol Manual W / S:** Centang *Aktifkan Mode Manual [W / S]*, tahan **W** untuk naik, dan tahan **S** untuk turun.
5. **Koneksi Foxglove Studio:** Buka [studio.foxglove.dev](https://studio.foxglove.dev), pilih *Open Connection* -> *Foxglove WebSocket* -> hubungkan ke `ws://localhost:8765`.

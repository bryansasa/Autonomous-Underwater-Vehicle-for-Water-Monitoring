Aplikasi desktop GUI Kalibrasi mandiri yang mengadopsi **tata letak, struktur antarmuka, dan tema warna persis seperti `Program-WGG`**, untuk instrumen **Sensor Kualitas Air** dan **Sensor Orientasi & Gerak Wahana Submersible**.

---

## 1. Tata Letak Antarmuka (Gaya Program-WGG)

Antarmuka dirancang dalam satu dashboard utuh tanpa tab tersembunyi (*single unified dashboard*) yang terdiri dari:
1. **Ethernet Connection Bar:** Konfigurasi IP (`192.168.1.177`), Port (`9001`), tombol `Connect`, indikator status koneksi, dan selector mode `Real Hardware` vs `Simulasi (Mock)`.
2. **Real-Time Sensor Data Bar:**
   - Baris 1 (Kualitas Air): `pH`, `EC (µS)`, `DO (mg/L)`, `Temp (°C)`.
   - Baris 2 (Orientasi & Gerak): `Roll (°)`, `Pitch (°)`, `Heading (°)`, `Kedalaman (m)`.
3. **Panel Kalibrasi 3 Kolom:**
   - **Kolom 1:** `pH Calibration (Atlas Scientific EZO)` (Mid, Low, High, Status, Clear) & `Dissolved Oxygen — DO`.
   - **Kolom 2:** `Conductivity Calibration (Atlas Scientific EZO EC)` (Dry, One Point 1413, Low, High, Status, Clear) & `Temperature — DS18B20`.
   - **Kolom 3:** `Orientasi & Gerak Wahana (IMU & Depth)` (Gyro Zero-Bias, Horizon Leveling Tare, Magnetometer 360°, Depth Tare & Densitas).
4. **Communication Log:** Terminal teks riwayat pengiriman perintah (TX) dan respon mikrokontroler (RX) dengan tombol `Clear Log`.
5. **Data Recording Bar:** Tombol `Record`, pemilihan lokasi simpan CSV, pengaturan `Interval Rekam` (detik), dan timer durasi rekam live.
6. **Zoom Scaling:** Mendukung pintasan `Ctrl + Scroll Roda Mouse` untuk memperbesar/memperkecil ukuran font dan elemen visual secara dinamis.

### A. Sensor Kualitas Air
1. **Sensor pH (Atlas Scientific EZO / Modular):**
   - Kalibrasi 3-Titik: Mid-Point (`pH 7.00`), Low-Point (`pH 4.00`), High-Point (`pH 10.00`).
   - Cek status respon kalibrasi aktif (`CAL_PH,?`) dan reset pabrik (`CAL_PH,clear`).
   - Kompensasi suhu otomatis dari sensor suhu (Atlas Scientific Surveyor™ RTD PT-1000).
2. **Sensor Konduktivitas Listrik / EC (EZO EC):**
   - Kalibrasi Kering (*Dry Calibration* di udara bebas).
   - Kalibrasi 1-Titik dengan larutan standar kustom (default $1413\ \mu\text{S/cm}$).
   - Kalibrasi rentang lebar Low ($12880\ \mu\text{S/cm}$) dan High ($80000\ \mu\text{S/cm}$).
3. **Sensor Dissolved Oxygen / DO (DFRobot Analog / EZO-DO):**
   - Kalibrasi 100% saturasi oksigen (di udara lembap jenuh).
   - Kalibrasi 0% Zero DO menggunakan larutan Sodium Sulfit ($Na_2SO_3$ 5%).
4. **Sensor Suhu (Atlas Scientific Surveyor™ RTD Meter V3.1 + PT-1000 Probe):**
   - Probe: Platinum Class B RTD PT-1000 (-50°C s.d. 200°C).
   - Karakteristik Output Analog: Rentang 0–3.00 V dengan sensitivitas $9\ \text{mV/}^\circ\text{C}$ dan tegangan nominal $1.058\ \text{V}$ pada $0.0^\circ\text{C}$.
   - Rumus Konversi Datasheet: $T = \frac{V - 1.058}{0.009}$.
   - Kalibrasi Ice Bath $0.0^\circ\text{C}$ (offset zero) dan kalibrasi titik acuan kustom.
5. **Smart Stability Detector:**
   - Visualisasi grafik *real-time* berbasis `PyQtGraph` (60 FPS).
   - Menghitung standar deviasi ($\sigma$) dan rentang sinyal secara dinamis.
   - Indikator status kestabilan: badge **[STABIL / SIAP KALIBRASI]** (hijau) vs **[FLUKTUATIF / MENUNGGU]** (kuning).

### B. Sensor Orientasi & Gerak Robot (IMU & Depth)
1. **IMU Gyroscope (Zero-Rate Bias):**
   - Mengumpulkan 100–500 sampel saat wahana diam tanpa getaran, menghitung bias offset rata-rata $(\bar{\omega}_x, \bar{\omega}_y, \bar{\omega}_z)$, lalu menyimpan offset ke EEPROM.
2. **Horizon Leveling Tare:**
   - Tombol 1-klik untuk mengunci sudut Roll & Pitch ke $0.0^\circ$ saat robot di posisi trim datar.
3. **Magnetometer Hard-Iron & Soft-Iron Calibration:**
   - Scatter plot interaktif 2D/3D dari vektor $(B_x, B_y)$ saat robot diputar $360^\circ$ / gerakan angka 8.
   - Algoritma *Algebraic Least-Squares Fitting* untuk mendeteksi offset pusat dan distorsi elips.
4. **Sensor Kedalaman Tekanan (MS5837 / Bar30):**
   - Tare tekanan atmosfer lokal saat wahana mengapung di permukaan air ($Z = 0.00\ \text{m}$).
   - Pengaturan densitas fluida ($\rho = 997.0\ \text{kg/m}^3$ untuk Waduk Saguling).

### C. Sistem Operasi & Pencatatan Data
- **Dual-Mode:** Dapat beralih 1-klik antara **Real Hardware (Ethernet TCP)** dan **Simulasi (Built-in Mock)** untuk uji coba tanpa hardware.
- **CSV Data Logger:** Perekam data ber-timer dengan interval yang dapat diatur ($0.1 - 60.0$ detik).
- **Terminal TX/RX:** Monitor komunikasi data mentah antara PC dan mikrokontroler.

---

## 2. Struktur Direktori

```
Program-YEN/GUI Kalibrasi/
├── main.py                     # Titik masuk utama aplikasi
├── requirements.txt            # Dependensi Python
├── run_gui_kalibrasi.bat       # Launcher Windows 1-klik
├── README.md                   # Dokumentasi lengkap
├── config/
│   └── cal_config.json         # Konfigurasi default jaringan & threshold
├── core/
│   ├── comm_client.py          # TCP socket thread & command parser
│   ├── mock_server.py          # Simulator internal untuk pengujian offline
│   ├── cal_engine.py           # Logika deteksi stabilitas & ellipse fitting
│   └── data_logger.py          # Perekam CSV telemetri
└── ui/
    ├── styles.py               # Tema visual Catppuccin Macchiato (Dark)
    ├── main_window.py          # Jendela utama
    ├── tab_water_quality.py    # Tab kalibrasi kualitas air
    ├── tab_motion_imu.py       # Tab kalibrasi IMU & gerak robot
    └── widgets/
        ├── metric_card.py      # Kartu metrik nilai sensor
        └── stability_plotter.py# Grafik kestabilan sinyal real-time
```

---

## 3. Cara Menjalankan Aplikasi

### Opsi 1: Menggunakan File Batch (Paling Mudah)
Cukup klik dua kali berkas:
```
run_gui_kalibrasi.bat
```

### Opsi 2: Menggunakan Terminal / Command Prompt
```bash
cd "d:\Tugas Akhir\Tugas-Akhir-YEN\Program-YEN\GUI Kalibrasi"
python main.py
```

---

## 4. Panduan Prosedur Kalibrasi

### A. Kalibrasi pH
1. Hubungkan GUI ke wahana (atau pilih Mode Simulasi untuk latihan).
2. Bilas elektroda pH dengan air akuades/demineralisasi, lalu seka perlahan dengan tisu kering bebas serat.
3. Celupkan elektroda ke larutan buffer **pH 7.00**.
4. Pantau kurva pada grafik kestabilan. Saat badge menampilkan **[● STABIL / SIAP KALIBRASI]**, klik tombol **Mid (7.00)**.
5. Tunggu respon `*OK` di terminal.
6. Bilas kembali elektroda, lalu celupkan ke buffer **pH 4.00**, tunggu stabil, klik **Low (4.00)**.
7. *(Opsional untuk rentang basa)* Bilas dan celupkan ke buffer **pH 10.00**, klik **High (10.00)**.

### B. Kalibrasi Konduktivitas (EC)
1. Keringkan probe EC sepenuhnya di udara terbuka, lalu klik **Kalibrasi Udara Kering (Dry)**.
2. Celupkan probe ke larutan standar $1413\ \mu\text{S/cm}$.
3. Tunggu pembacaan stabil pada grafik, klik **Kalibrasi 1-Point**.

### C. Kalibrasi Gyroscope & Horizon Leveling (IMU)
1. Letakkan robot pada dudukan uji datar di permukaan yang kokoh dan bebas dari getaran mesin.
2. Klik tombol **Mulai Kalibrasi Gyro (Wahana Diam)**. Progress bar akan berjalan hingga 100% mengumpulkan sampel offset nol.
3. Setelah posisi robot dipastikan rata air (level), klik tombol **Tare Horizon (Set Roll & Pitch = 0.0°)**.

### D. Kalibrasi Kedalaman (Depth Tare)
1. Letakkan wahana di permukaan air waduk sebelum memulai penyelaman.
2. Masukkan densitas air waduk ($997.0\ \text{kg/m}^3$) lalu klik **Set**.
3. Klik tombol **Tare Permukaan Air (Z = 0.00 m)**.

---

## 5. Referensi Format Protokol

| Perintah TX | Deskripsi | Format Respon RX |
| :--- | :--- | :--- |
| `CAL_PH,mid,7.00` | Kalibrasi pH 7.00 | `CAL_RESP,PH,*OK,Mid Calibrated` |
| `CAL_PH,low,4.00` | Kalibrasi pH 4.00 | `CAL_RESP,PH,*OK,Low Calibrated` |
| `CAL_PH,high,10.00` | Kalibrasi pH 10.00 | `CAL_RESP,PH,*OK,High Calibrated` |
| `CAL_EC,dry` | Kalibrasi probe EC kering | `CAL_RESP,EC,*OK,Dry Zero Saved` |
| `CAL_EC,one,1413` | Kalibrasi EC 1-Titik | `CAL_RESP,EC,*OK,Single Point Calibrated` |
| `CAL_DO,sat,100` | Kalibrasi DO 100% Udara | `CAL_RESP,DO,*OK,100% Sat Recorded` |
| `CAL_IMU,gyro` | Kalibrasi Zero-Bias Gyro | `CAL_RESP,IMU,*OK,Gyro Calibrated` |
| `CAL_IMU,level` | Tare Roll/Pitch ke 0.0° | `CAL_RESP,IMU,*OK,Level Tare Set` |
| `CAL_MAG,start` | Mulai stream magnetik 360° | `CAL_MAG_RAW,bx,by,bz` |
| `CAL_DEPTH,tare` | Tare nol kedalaman permukaan | `CAL_RESP,DEPTH,*OK,Surface Zero Tare` |

---

*SPELL Laboratory | Program Studi S1 Teknik Elektro, Fakultas Teknik Elektro, Telkom University*

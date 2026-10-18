# Tyrant payload — ESP32-S3

Firmware ESP32-S3 untuk EZO-EC, EZO-pH, EZO-DO (masing-masing dengan isolated
board), input suhu analog, empat MOSFET sensor, dan dua INA226.
Firmware dipindahkan dari `esp` ke `firmware/esp` setelah persetujuan pengguna.
Schema payload bersumber dari `ros2_ws/src/tyrant_payload_interfaces`; direktori
`extra_packages/tyrant_payload_interfaces` adalah symlink ke paket tersebut.
Interface Teensy tetap terpisah dan firmware Teensy tidak diubah pada integrasi ini.
Panduan host: [integrasi HIL dan rekaman](../../docs/payload_mission_host.md).

## Konfigurasi hardware

Edit **`include/payload_config.h`**. Nomor GPIO berikut **sementara**, bukan
klaim bahwa kabel sudah terpasang sesuai tabel. Target board PlatformIO masih
`esp32-s3-devkitm-1` dari proyek awal; sesuaikan dengan varian board S3 fisik.

| Fungsi | GPIO sementara | Keterangan |
|---|---|---|
| I2C pertama SDA / SCL | 8 / 9 | EC, pH, DO dan INA226 rel keempat sensor |
| I2C kedua SDA / SCL | 10 / 11 | INA226 thruster / board power 6S |
| Suhu analog | 7 | ADC1, terpisah dari MOSFET |
| MOSFET EC | 4 | Default OFF |
| MOSFET pH | 5 | Default OFF |
| MOSFET suhu | 6 | Default OFF |
| MOSFET DO | 15 | Default OFF; dahulu bertabrakan dengan suhu pada GPIO 7 |

Pin MOSFET mengikuti `MOSFET_ACTIVE_HIGH`. Ada pemeriksaan compile-time pin
bertabrakan. Tetap sesuaikan pin dengan pinout/flash/PSRAM board fisik Anda.
Inisialisasi setiap bus I2C dilakukan satu kali dengan timeout transaksi 20 ms.

Alamat sementara: EZO-EC `0x64`, pH `0x63`, DO `0x61`, INA226 `0x40` pada
masing-masing bus. Kedua INA boleh memakai alamat sama karena bus terpisah.

Kalibrasi shunt yang dikonfirmasi pengguna:

- Thruster: **200 A / 75 mV = 0,000375 ohm**.
- Rel sensor: **R100 = 0,1 ohm**.

INA226 membaca register tegangan bus dan shunt aktual, memeriksa ID chip,
konfigurasi, conversion-ready dan saturasi. Arus dihitung dari tegangan shunt /
resistansi; daya = tegangan bus × arus. Tidak ada `rand()` atau data daya simulasi.
Nilai 200 A adalah spesifikasi shunt, bukan klaim kemampuan jalur PCB/konektor.

**Model/rangkaian sensor suhu belum dikonfirmasi.** `TEMPERATURE_CALIBRATION_CONFIRMED`
masih `false`: pembacaan suhu tidak dilabeli valid. Rumus linear lama
`(V - 1.058) / 0.009` hanya kandidat Surveyor. Jangan aktifkan sampai rumus cocok
dengan modul aktual. Probe RTD mentah memerlukan rangkaian pengukuran, bukan
sekadar rumus tegangan linear tersebut. Parameter ADC dan tegangan input harus
sesuai ESP32-S3 serta rangkaian pengondisi sinyal.

## Perilaku firmware

- USB CDC serial 115200 untuk micro-ROS Humble, domain default 0.
- Tujuh publisher, dua subscription; empat executor handles (dua timer + dua subscription).
- Host heartbeat tetap **`/tyrant/payload/host_heartbeat`**. Nilainya diperlakukan
  sebagai tanda paket diterima; counter tidak divalidasi. Topic dapat diedit di
  konfigurasi. Belum disamakan dengan `/tyrant/host_heartbeat` milik Teensy.
- ESP heartbeat otomatis 1 Hz. Host heartbeat direkomendasikan 10 Hz; timeout
  >1000 ms diperiksa langsung sebelum menerima permintaan ON.
- OFF tetap diterima saat heartbeat tidak sehat. ID sensor diperiksa lebih dahulu.
  Saat heartbeat/agent hilang, sensor yang telah ON **tetap ON**, permintaan ON
  baru ditolak. Ini mempertahankan kebijakan payload; bukan kendali propulsi.
- Sensor yang OFF tidak diakses lewat I2C dan datanya tidak valid. Setelah ON,
  ada warm-up yang dapat dikonfigurasi; gunakan nilai sesuai perangkat aktual.
- EZO dibaca sebagai state machine: request, tunggu konversi, parse respons;
  NACK, respons gagal, teks rusak, NaN, dan data lama tidak dianggap valid.
  EC/DO memakai field pertama respons multikolom: konfigurasi output EZO harus
  sesuai EC dalam uS/cm dan DO dalam mg/L.
- INA monitoring dan heartbeat tetap berjalan saat menunggu konversi EZO.
- Ping agent memakai timeout 100 ms setiap 500 ms. Tiga ping gagal berturut-turut
  memicu teardown/reconnect; ping sukses memutus rentetan kegagalan.
- Publish reliable diberi timeout 100 ms. Kegagalan sesaat tetap dihitung tetapi
  tidak langsung membongkar koneksi. Publish yang seluruhnya gagal tanpa satu
  keberhasilan selama 3 detik memicu pemulihan, demikian juga error fatal executor.
  Heartbeat host lama dibuang saat koneksi ulang. Cleanup hanya memfinalisasi
  resource yang sudah berhasil dibuat.
- Counter error komunikasi/I2C berasal dari hasil operasi. `i2c_bus*_healthy`
  berarti pernah ada transaksi sukses dan tidak ada kegagalan dalam 1 detik
  terakhir; **bukan** jaminan semua perangkat hadir. Periksa state tiap sensor.
- Status MOSFET/`actual_enabled` adalah keadaan perintah GPIO, tanpa feedback
  kelistrikan saklar. `power_transition_error_count=0` tidak membuktikan saklar sehat.

## Akuisisi adaptif EA-DSRA

Siklus akuisisi berikutnya dijadwalkan memakai keluaran EA-DSRA 1–5 detik.
Publikasi kualitas air terjadi ketika siklus akuisisi selesai; publish juga
memuat kanal yang gagal/OFF dengan validitas false. Durasi konversi, retry dan
transport dapat menambah jitter; bukan jaminan hard real-time 1–5 detik.
Power thruster 10 Hz, power sensor 5 Hz, health 2 Hz, heartbeat/diagnostik 1 Hz.

Baterai untuk EA-DSRA berasal dari INA bus kedua (6S), bukan angka simulasi.
Tegangan baterai tak valid atau tidak ada kanal valid memakai interval 1 detik.
DO valid <=2 mg/L memaksa 1 detik, mendahului penalti energi. Riwayat gradien
memakai waktu sampel tiap kanal dan dihapus ketika kanal tidak valid.
Nilai SoC model linear adalah estimasi dan tuning perlu divalidasi pada baterai.
Belum ada bukti penghematan energi 35% dari perubahan ini.

## Interface dan pencatatan misi

Enam `.msg` tetap di `extra_packages/tyrant_payload_interfaces`. Struktur field
belum diubah; host masih perlu membangun paket yang sama pada tahap integrasi.
Lihat [kontrak dan rencana misi multi kedalaman](docs/integrasi_misi.md).

## Build dan uji tanpa hardware

Dari terminal laptop:

```bash
cd /home/charisto/tyrant-simple/firmware/esp
# Toolchain, cache, dan Python build environment ditempatkan di esp.
bash scripts/build.sh
```

Build pertama memerlukan internet serta toolchain ESP32-S3, git, cmake dan
dependensi Python untuk micro-ROS. Script membuat virtualenv lokal (memerlukan
modul Python venv) supaya dependensi build tidak mengubah environment Teensy. Gunakan satu library `micro_ros_platformio`;
prebuilt `micro_ros_arduino` tidak lagi dicampur dengan custom message build.
`payload_microros.meta` mengalokasikan 7 publisher dan 2 subscription.
Tidak ada perintah upload otomatis.

Uji logika di laptop, tidak membuka port serial:

```bash
cd /home/charisto/tyrant-simple/firmware/esp
python3 scripts/run_native_tests.py
```

Test menggunakan GPIO/I2C palsu dan struct yang dihasilkan dari `.msg` aktual.
Diperlukan `g++` dan Python 3; executable/header uji disimpan dalam `.native-test`.
AddressSanitizer dan UndefinedBehaviorSanitizer aktif. Pada sandbox yang
menggunakan ptrace, LeakSanitizer tidak dapat berjalan; gunakan:

```bash
ASAN_OPTIONS=detect_leaks=0 python3 scripts/run_native_tests.py
```

Uji native tidak membuktikan kinerja I2C fisik, USB/reconnect hardware, timing
sensor, polaritas MOSFET atau kebenaran kalibrasi suhu.

Hasil verifikasi: [validasi 2026-10-08](docs/validasi_2026-10-08.md).

## Referensi implementasi

Profil simulasi tanpa sensor: [panduan terminal](docs/uji_simulasi_payload.md).
Build dengan `bash scripts/build.sh esp32-s3-sim`; topic memakai `/tyrant/payload_sim`.
Profil ini tidak mengakses GPIO MOSFET, ADC, atau I2C dan seluruh datanya buatan.
Profil hardware default tetap memakai `/tyrant/payload`.

- [TI INA226 datasheet](https://www.ti.com/lit/ds/symlink/ina226.pdf): register ID,
  configuration, conversion ready, 1.25 mV/LSB bus dan 2.5 uV/LSB shunt.
- [Espressif Arduino I2C](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/i2c.html):
  controller I2C dan timeout.
- [Espressif Arduino ADC](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html):
  pembacaan milivolt dan attenuasi pin.
- [micro-ROS PlatformIO](https://github.com/micro-ROS/micro_ros_platformio):
  custom interfaces `extra_packages` dan alokasi resource melalui user meta.

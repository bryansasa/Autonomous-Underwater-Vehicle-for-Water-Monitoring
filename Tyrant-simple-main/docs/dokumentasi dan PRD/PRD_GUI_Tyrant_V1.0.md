# PRD GUI Tyrant

Versi 1.0 | 10 Oktober 2026 WIB | Spesifikasi produk dan kebutuhan implementasi

GUI ini menjadi antarmuka operasi Tyrant melalui browser laptop dan Google Pixel 7 Pro. Jetson menjalankan backend dan menyajikan seluruh aset web secara lokal. Dokumen ini menetapkan tampilan empat window, perilaku kontrol, integrasi ROS, kebutuhan perangkat, tahapan pengerjaan, serta kriteria penerimaan. Mockup lokal empat window sudah dibuat untuk review; integrasi GUI dengan backend/ROS belum diimplementasikan. Keberhasilan HIL dan autostart Jetson merupakan fondasi integrasi, bukan bukti bahwa fitur GUI terhubung kendaraan sudah tersedia.

## 1 Tujuan produk

Operator dapat melihat kamera dan kondisi kendaraan, mengendalikan MANUAL melalui keyboard atau controller, menyusun serta menjalankan misi multi-kedalaman, dan merekam hasil pengukuran. Pengoperasian tidak memerlukan terminal untuk aktivitas rutin setelah integrasi selesai. Terminal tetap digunakan untuk SysID, build/upload firmware, deployment, serta pemulihan teknis.

Prinsip desain adalah KISS: empat tab/window dengan layout tetap, istilah yang jelas, satu backend sebagai penghubung ROS, dan state yang sama pada semua browser. Tampilan mengambil inspirasi antarmuka kamera dan instrumen Cockpit/Blue Robotics; tidak ada rencana mengganti stack Tyrant dengan BlueOS atau MAVLink.

## 2 Keputusan ruang lingkup

| Keputusan | Ketentuan |
|---|---|
| Bentuk aplikasi | Web responsif yang disajikan Jetson |
| Perangkat | Laptop mendukung keyboard atau controller fisik; Pixel 7 Pro memakai controller fisik |
| Akses bersamaan | Semua perangkat membuka GUI dan fungsi yang sama |
| Navigasi | Empat window tetap tanpa editor layout bebas |
| Kontrol HP | Controller fisik; tanpa joystick layar sentuh pada versi awal |
| EA-DSRA ESP | Tetap hardcode; tidak ada editor parameter EA-DSRA |
| SysID | Tetap melalui terminal; GUI hanya menampilkan status jika tersedia |
| Tuning kontrol | Window keempat; runtime tuning memerlukan interface baru |
| LMPC | Ruang tampilan disiapkan; fungsi aktif setelah controller tersedia |
| Thruster | Skala input manual dipisahkan dari batas output kendaraan |
| Lokalisasi | Orientasi dan depth aktual; tidak mengklaim posisi XY aktual |
| Startup | Heartbeat otomatis dari host Jetson; misi dimulai eksplisit |

Tidak termasuk versi awal: aplikasi Android native, akun dan pembagian peran operator/pemantau, editor widget bebas, peta posisi aktual tanpa sensor posisi, implementasi LMPC, tuning EA-DSRA, tombol menjalankan eksperimen SysID, perekaman video otomatis, serta akses internet publik.

## 3 Kondisi sistem yang sudah tersedia

Pada 10 Oktober 2026, host misi dan interface payload sudah dibangun di Jetson ARM64. Misi board HIL normal, recorder bag/CSV, pemulihan agent ESP, restart container saat misi, serta reboot/autostart telah diuji. Container aktif adalah `tyrant-mission` dalam profil HIL; plant simulasi, kedua agent, dan heartbeat host aktif, sedangkan misi IDLE sampai menerima start.

Paket `tyrant_interfaces` untuk Teensy dan `tyrant_payload_interfaces` untuk ESP tetap terpisah. ESP berada di `firmware/esp`. Teensy memakai estimator sederhana dan controller sementara: depth P, attitude/heading PD, surge/sway berupa effort ternormalisasi. LMPC belum tersedia. Profil produksi Teensy belum mempunyai geometri thruster dan konfigurasi output fisik yang tervalidasi.

EA-DSRA ESP sudah menentukan interval sampling adaptif 1–5 detik dari perubahan kualitas air dan tegangan baterai. Parameter dan diagnostik internalnya belum mempunyai kontrak tuning runtime. Sensor fisik payload dan kamera belum dikualifikasi untuk GUI. Model serta kalibrasi suhu analog belum dikonfirmasi; GUI tidak boleh memaksakan status valid.

## 4 Pengguna dan skenario utama

Pengguna utama adalah operator kendaraan dan tim pengujian. Fungsi yang tersedia ditentukan kemampuan perangkat dan kesiapan sistem, bukan peran akun. Laptop dan HP dapat memantau bersamaan dan mengirim perintah diskret melalui backend yang sama.

Skenario utama adalah pemeriksaan sebelum operasi, kendali manual, misi multi-kedalaman, rekaman manual, peninjauan hasil, dan diagnostik/tuning saat IDLE. Operator harus dapat berpindah window tanpa kehilangan informasi mode, koneksi, serta rekaman.

## 5 Arsitektur dan pembagian tanggung jawab

Browser mengirim perintah dan menerima state melalui backend Jetson. Backend menerjemahkan data ROS menjadi state produk, memvalidasi perintah, mengatur sumber input manual, serta menyediakan daftar sesi dan unduhan. Browser tidak berbicara langsung dengan serial board atau DDS.

Alur sistem adalah browser ke backend Jetson, backend ke ROS 2, lalu host misi/Teensy/ESP sesuai jenis permintaan. Webcam ditangkap di Jetson dan disajikan melalui jalur video terpisah dari telemetry. Backend tidak menjalankan controller kendaraan dan tidak mengambil alih fungsi estimator Teensy.

| Komponen | Tanggung jawab |
|---|---|
| Browser | Tampilan, input keyboard/controller, formulir, grafik |
| Backend GUI | Validasi, command routing, state bersama, freshness, sesi input |
| Host misi | Koordinasi langkah dan sampling, heartbeat, bag/CSV |
| Teensy | Mode, estimator, kontrol, allocator, batas output, failsafe |
| ESP | Sensor air, INA, MOSFET, EA-DSRA hardcode |
| Layanan kamera | Capture, encoding dan stream webcam |

Usulan implementasi adalah satu frontend TypeScript dengan aset lokal, renderer 3D ringan, serta grafik dengan buffer terbatas. Backend Python menjadi layanan tersendiri yang terintegrasi dengan rclpy; framework web dan metode streaming dipilih melalui spike kompatibilitas. Pemilihan library, codec, dan port belum merupakan keputusan final. Tidak perlu microservice tambahan untuk setiap widget.

Heartbeat Teensy dan ESP tetap dimiliki `tyrant_mission_host`; backend GUI tidak membuka agent atau membuat publisher heartbeat baru. Teleop terminal tidak boleh menerbitkan input manual bersamaan dengan gateway GUI. GUI harus dapat berjalan tanpa menggandakan host, plant, agent, atau recorder yang sudah aktif.

## 6 Koneksi jaringan dan perangkat

Sasaran koneksi lapangan adalah Jetson Ethernet ke modul powerline FullDepth sisi kendaraan, sepasang kabel tether ke modul FullDepth sisi permukaan, lalu Ethernet ke hub/adaptor USB-C Pixel. Model board, terminal D+/D−, catu daya, dan karakteristik link harus dikonfirmasi dari perangkat/dokumentasi FullDepth sebelum wiring final. Kompatibilitas modul tidak dinyatakan sudah diuji.

Untuk akses HP dan laptop bersamaan lewat kabel, diperlukan switch Ethernet atau perangkat yang memang menyediakan beberapa port LAN. Hub USB-C dengan satu port Ethernet tidak otomatis menggantikan switch jaringan. Adaptor LAN Pixel harus diuji bersama controller Bluetooth dan pengisian daya jika digunakan.

Jetson dapat menjadi penyedia DHCP pada jaringan tether agar HP tidak memerlukan IP statis manual. Ini kebutuhan jaringan baru, bukan konfigurasi yang sudah diterapkan. Alamat `10.42.0.246` sekarang berasal dari jaringan sharing laptop; perpindahan topologi memerlukan rancangan IP baru yang tidak bertabrakan dengan laptop.

Seluruh aset UI harus tersedia tanpa CDN/internet. GUI memakai satu alamat origin lokal; target deployment HTTPS dan WebSocket aman untuk kompatibilitas browser/controller dan transfer perintah. Sertifikat yang dapat diterima Pixel dan laptop harus disiapkan serta diuji. Tidak menonaktifkan proteksi browser secara global. Internet diperlukan untuk NTP atau pemasangan dependensi bila dipakai, bukan untuk operasi GUI lokal.

## 7 Tata letak bersama

Empat window adalah tab dalam satu aplikasi, bukan empat jendela browser. Tab diberi nama Operasi, Kontrol dan Misi, Grafik dan Rekaman, serta Diagnostik dan Tuning. Bar tetap menampilkan mode aktual, koneksi, sumber input, indikator REC dan tombol Stop.

Target awal kiri/kanan window Operasi adalah 60/40 pada laptop dan Pixel landscape. Kamera memakai sekitar setengah sampai dua pertiga lebar layar. Pada portrait, konten disusun vertikal dengan bar kontrol tetap terjangkau. Fungsi tetap sama; perangkat dengan keyboard atau controller yang tidak tersedia menampilkan alasan kontrol manual tidak aktif.

Target viewport pengujian minimal 1280 × 720 untuk laptop, 840 × 390 CSS pixel untuk landscape HP, dan 390 × 840 untuk portrait. Ini target layout usulan, bukan resolusi fisik Pixel. Ukuran kontrol sentuh minimum 44 × 44 CSS pixel. Angka dan satuan dapat dibaca tanpa zoom; status memakai label/ikon selain warna.

Tidak ada gulir horizontal seluruh halaman pada viewport target. Panel diagnostik yang panjang boleh digulir vertikal. Kamera fullscreen mempertahankan overlay mode, depth, heading, status koneksi dan akses Stop. Tab yang tidak terlihat tidak terus merender 3D/grafik secara penuh.

## 8 Window Operasi

### 8.1 Kamera dan navigasi

Area kiri berisi stream kamera sebagai elemen utama. Bagian bawah kamera memuat model orientasi robot 3D, indikator kedalaman vertikal 2D, dan kompas. Kamera belum tersedia menampilkan placeholder yang jelas; kegagalan video tidak mengosongkan telemetry lain.

Model 3D mengikuti roll/pitch/yaw estimator Teensy. Sumbu model harus dipetakan ke BODY-FRD, dengan penanda depan kendaraan yang jelas. Versi awal dapat memakai model sederhana sampai mesh kendaraan tersedia. Model ini hanya memvisualisasikan orientasi, bukan posisi 3D global atau perpindahan XY.

Depth positif ke bawah, satuan meter. Skala Z menampilkan permukaan nol, depth aktual, serta marker target ketika aktif. Tidak ada ikon perjalanan horizontal aktual. Target belum tersedia ditampilkan sebagai belum tersedia, bukan dihitung dari input terakhir.

Kompas memakai heading estimator yang dikoreksi magnetometer; default menampilkan heading asli 0–360 derajat. Operator boleh memakai nol yaw misi sebagai kerangka relatif. Heading asli tetap disimpan dan target relatif dikonversi ke heading asli sebelum dikirim. Mematikan referensi kembali ke heading asli; ini bukan kalibrasi magnetometer. Penandaan utara magnetik/geografis harus mengikuti kalibrasi dan konvensi yang diverifikasi; yaw valid bukan bukti heading geografis akurat. Roll/pitch/heading/depth juga tersedia sebagai angka.

Saat attitude, heading, atau depth invalid/stale, widget bersangkutan meredup dan menyatakan status. Orientasi terakhir tidak boleh terus dianimasikan seolah data aktual. Nilai terakhir boleh ditampilkan dengan label terakhir dan umur data.

### 8.2 Kualitas air dan daya

Area kanan memuat EC dalam µS/cm, pH tanpa satuan, suhu dalam °C, dan DO dalam mg/L. Tiap kartu menampilkan nilai, validity, umur data, status sensor, dan kontrol ON/OFF. ON berarti status GPIO/MOSFET yang diperintahkan, bukan bukti arus mengalir pada sensor tersebut.

Dua kartu INA menampilkan tegangan V, arus A, daya W, serta validity: bus thruster/board power 6S dan rel gabungan empat sensor. Tidak menampilkan arus masing-masing sensor karena hardware hanya mengukur rel gabungan. Persentase SOC berbasis tegangan, jika kelak tersedia, harus diberi nama estimasi dan tidak dihitung diam-diam sebagai kapasitas baterai pasti.

ON/OFF melalui status MENUNGGU, DITERIMA atau DITOLAK. Nilai switch aktif mengikuti ACK board dan telemetry; request diterima backend saja tidak cukup. Sensor yang menyala dapat tetap WARM-UP, INVALID atau ERROR. Saat AUTO, kontrol sensor yang termasuk kebijakan misi ditangani host; GUI menjelaskan kepemilikan ini dan tidak melawan request otomatis dengan publisher lain.

### 8.3 Status dan log

Status koneksi dipisahkan menjadi browser–Jetson, Teensy/agent, ESP/agent, serta kamera. Tampilan harus membedakan proses container berjalan dari board benar-benar sehat. Mode menampilkan mode aktual dan permintaan yang sedang menunggu konfirmasi.

Log ringkas menyimpan paling banyak 100 event UI: perubahan koneksi, reject perintah, mode, start/stop rekaman, hasil langkah, dan fault. Event berulang dikelompokkan dengan jumlah kemunculan. Waktu menggunakan WIB pada tampilan; UTC dan uptime asli tetap disimpan pada rekaman. Log lengkap dapat dibuka tanpa memenuhi dashboard dengan telemetry setiap frame.

## 9 Window Kontrol dan Misi

### 9.1 Kontrol langsung

Kontrol langsung meliputi mode, input manual aktif, skala manual, target depth, target heading, Set Surface/Nol Kedalaman, Naik ke Permukaan, dan Stop. Target langsung memerlukan kontrak baru; jangan mengirim paket mission diam-diam sebagai pengganti setpoint MANUAL.

Mode yang dapat diminta operator adalah IDLE, MANUAL, AUTO melalui start misi yang terkoordinasi, dan SAFE. BOOT/FAULT/EMERGENCY ditampilkan sebagai status sistem; clear fault/recovery tidak dihadirkan tanpa prosedur dan interface yang sesuai. Mengganti mode ketika misi aktif terlebih dahulu menghentikan misi melalui host dan menunggu konfirmasi, sehingga host tidak mengirim langkah berikutnya sesudah operator berpindah mode.

Set Surface/Nol Kedalaman menetapkan referensi tekanan di permukaan. Label menjelaskan bahwa ini kalibrasi nol, bukan perintah naik. Firmware sekarang mengharuskan IDLE dan pressure valid. Naik ke Permukaan adalah gerak terpisah menuju depth yang ditetapkan, dengan konfirmasi mode/command yang jelas.

Stop adalah penghentian misi/kontrol normal dan request SAFE, bukan emergency stop fisik. SAFE tidak menjamin depth hold. Saat MANUAL, Stop juga membatalkan sesi input aktif; deadman yang masih ditahan tidak boleh segera mengaktifkan gerak kembali. Operator perlu melepas dan mengaktifkan input lagi.

### 9.2 Input manual

Laptop dapat memakai keyboard atau controller fisik; Pixel memakai controller fisik. Pada jalur GUI, controller tersambung ke perangkat yang membuka browser dan dibaca browser, lalu input diteruskan melalui backend Jetson. Tidak ada joystick virtual. Input hanya diterima ketika mode aktual MANUAL, kondisi sistem mendukung, input fresh, serta tombol enable/deadman aktif. Roll/pitch dinetralkan pada mapping awal kecuali mapping khusus diuji.

Mapping keyboard awal yang diusulkan: W/S surge maju/mundur, A/D sway kiri/kanan, Q/E yaw kiri/kanan, R/F naik/turun, Space deadman, dan Escape Stop. Mapping ini harus diuji di mockup, termasuk konflik shortcut browser. Ketika fokus berada pada input teks/angka, shortcut gerak dinonaktifkan. Key repeat tidak menjadi satu-satunya sumber refresh command.

Mapping controller mengikuti fungsi yang sudah diuji melalui teleop, tetapi indeks Gamepad API tidak diasumsikan sama dengan `/joy`. GUI menyediakan halaman pemeriksaan axes/buttons, deadzone, arah dan deadman, tanpa mengirim gerak pada mode pemeriksaan. Model controller final dan mapping browser belum dikonfirmasi.

Semua browser boleh mengakses fungsi yang sama. Sumber input manual global dipilih Keyboard atau Controller. Backend menerima satu aliran manual dari satu koneksi yang sedang di-enable; koneksi lain tetap dapat memantau serta melakukan Stop. Identitas koneksi ini hanya mencegah dua keyboard/controller bercampur, bukan akun/peran atau pemisahan GUI. Perpindahan sumber menetralkan input lama dan meminta enable baru. Perintah diskret diproses berurutan dan hasilnya dibagikan ke semua browser.

Keyboard/controller mengirim input berkala selama enable aktif. Lepas tombol gerak dengan enable tetap aktif mengirim input netral; heave/yaw netral mengikuti hold yang memang disediakan firmware. Lepas deadman, kehilangan fokus, controller terputus, halaman disembunyikan, atau socket terputus mengakhiri stream manual. Browser mengirim netral jika masih tersambung; backend tidak mengulang input lama agar terlihat fresh.

Teensy saat ini mempunyai timeout ManualCommand 250 ms dari command terakhir. Target gateway awal adalah input 20 Hz dan TTL 150 ms; angka gateway merupakan usulan untuk diuji pada tether. Batas waktu total dari kehilangan browser ke netral harus diukur, bukan disebut otomatis 250 ms karena ada TTL gateway dan antrean jaringan. Reconnect tidak menghidupkan kembali deadman lama.

### 9.3 Editor mission planner

Editor berbentuk daftar langkah yang dapat ditambah, diurutkan, diduplikasi dan dihapus. Maksimum sekarang 100 langkah host; kapasitas antrean firmware 16 bukan berarti keseluruhan misi host dibatasi 16, karena host mengirim per segmen. Rencana aktif dibuat sebagai snapshot immutable; penyuntingan berikutnya menjadi rencana berbeda dan tidak mengubah misi yang sedang berjalan.

| Jenis langkah | Isian utama |
|---|---|
| WAIT | Durasi, timeout, sampling opsional |
| SURGE | Effort bertanda, durasi, timeout, sampling opsional |
| SWAY | Effort bertanda, durasi, timeout, sampling opsional |
| DIVE | Target depth, effort, toleransi, timeout, opsi sampling |
| HEADING | Heading asli/relatif yang dikonversi ke asli, effort, toleransi sudut, timeout, sampling opsional |
| SURFACE | Target depth, effort, toleransi, timeout, opsi sampling |

GUI menampilkan effort sebagai persentase input ternormalisasi dan arah, bukan persentase gaya dorong fisik. Kontrak Teensy saat ini menerima heading absolut. GUI dapat memakai yaw misi relatif melalui offset yang dibekukan di snapshot rencana; contoh nol pada heading asli 37° membuat target relatif 90° menjadi heading asli 127°. Ini heading relatif terhadap acuan, bukan perintah rotasi incremental 90° dari posisi setiap langkah. Planned XY bersifat opsional dan diberi label rencana; tidak ada estimasi actual XY dari effort/durasi.

Keputusan pengguna revisi 03: sampling dapat ON/OFF pada semua jenis langkah, dengan waktu `during` (selama langkah) atau `after` (sesudah gerakan selesai). Depth tidak wajib stabil untuk mencatat sampel. Rekaman memisahkan validity sensor, validity/freshness depth, penanda stabilitas, jenis langkah dan phase pengambilan. Sampel dengan depth berubah tetap dicatat serta diberi penanda; tidak disamakan dengan sampel titik stabil. Depth invalid/stale tidak dipaksakan sebagai nilai depth valid; aturan failsafe kendaraan tetap berlaku terpisah dari kualitas sampling.

Toleransi depth tetap digunakan untuk pencapaian target DIVE/SURFACE. Jendela/rentang stabilitas dipakai untuk penanda kualitas, bukan selalu sebagai penghalang sampling. Preset pengukuran titik stabil lama boleh tetap tersedia secara eksplisit. Kuota sampel tidak boleh memperpanjang gerakan secara diam-diam pada mode `during`; kuota yang kurang dilaporkan tidak lengkap. Mode `after` dapat mengambil sampel ketika kendaraan belum stabil sambil menandainya. Kebijakan daya `throughout` tetap berarti menyala sepanjang perjalanan; `at_point` perlu diperluas menjadi jendela sampling per langkah agar mendukung sampling selama gerak.

Host saat ini masih membatasi sample=true ke DIVE/SURFACE dan mewajibkan depth berada dalam target serta stabil untuk qualified samples. Validator/state machine host, perekam dan schema plan perlu diperbarui sebelum opsi revisi 03 dapat dipakai pada board. Firmware ESP sudah mempublikasikan telemetry tanpa mengetahui jenis langkah; keputusan sampling berada di host. Teensy tetap bertanggung jawab atas eksekusi gerakan. Perubahan microcontroller tidak dinyatakan sudah dilakukan atau diperlukan hanya karena checkbox GUI tersedia.

Contoh HIL yang sudah berhasil memakai toleransi depth 0,2 m, stabilisasi 3 s, rentang perubahan 0,05 m, tiga sampel/sensor, freshness depth 0,5 s, umur sampel maksimum 6,5 s, dan timeout sampling 40 s. Nilai ini preset HIL yang dapat diubah, bukan default tuning kendaraan riil. Rentang target depth yang saat ini divalidasi host adalah 0–10 m; firmware baru harus melaporkan capability jika rentang berubah.

### 9.4 Eksekusi dan hasil misi

Start melakukan validasi server terhadap rencana dan readiness terbaru. `autonomy_ready=false` sebelum antrean disiapkan tidak boleh sendirian menjadi alasan GUI menolak start, karena gate firmware diperiksa lagi setelah host mengonfigurasi segmen. Start yang ditolak menampilkan alasan host/board; tombol tidak menjadi running hanya karena HTTP sukses.

Progres menampilkan mission/session ID, langkah aktif, phase host, target/aktual depth atau heading, timer, serta jumlah sampel per sensor. Status akhir membedakan COMPLETE dengan semua titik lengkap, COMPLETE dengan titik tidak lengkap, FAILED, dan STOPPED. Nilai `all_sampling_points_complete=null` tidak ditafsirkan sebagai berhasil.

Payload gagal dapat membuat titik timeout/tidak lengkap lalu misi lanjut sesuai kebijakan host. State Teensy invalid/stale atau estimator tidak siap menghentikan misi dengan FAILED dan STOP/SAFE. Saat browser/tether operator terputus, AUTO tetap dapat berjalan di host selama komunikasi onboard dan syarat state tetap terpenuhi. Browser yang kembali mengambil snapshot aktual; tidak melakukan replay perintah lama.

Pause/resume misi belum tersedia dan tidak dimasukkan ke versi pertama. Tombol Save menyimpan rencana; tombol Start menjalankan snapshot tertentu. Reload browser tidak menghentikan AUTO maupun membuka rekaman baru.

## 10 Window Grafik dan Rekaman

Grafik utama adalah empat sensor kualitas air terhadap waktu, depth aktual versus target jika tersedia, dan tegangan/arus/daya kedua INA. Sumbu mempunyai satuan; pH/EC/DO/suhu tidak digabung pada satu sumbu tanpa skala yang jelas. Sensor invalid/stale menghasilkan celah, bukan nilai nol atau garis interpolasi panjang.

Pilihan tampilan adalah Live dan Sesi Tersimpan. Live menyediakan rentang 1, 5 dan 15 menit dengan buffer/decimation terbatas. Grafik tidak menulis sampel buatan karena refresh UI lebih cepat dari sensor; timestamp dan sequence membedakan pembacaan baru dari state yang ditampilkan berulang.

Sesi tersimpan memuat metadata, hasil misi, tabel titik kedalaman, sampel per sensor, serta ekspor CSV dan unduhan bundle sesi bila ukuran memungkinkan. Rosbag tetap data asli untuk analisis teknis. Grafik historis memerlukan reader/index baru; browser tidak membaca SQLite rosbag secara langsung.

Rekaman manual bisa dimulai tanpa misi dan tidak otomatis menyalakan sensor atau mengubah mode. Misi menggunakan recorder host yang sama. Start manual ditolak ketika recorder dikendalikan misi aktif; GUI tidak membuka recorder kedua. Indikator REC baru aktif setelah konfirmasi sesi benar-benar dibuka, dan berhenti setelah file ditutup.

Backend menyediakan ruang disk, durasi, nama sesi, kondisi finalisasi, dan error recorder. Free-space gate 512 MiB yang sudah ada tetap dipertahankan. Tidak ada penghapusan rekaman otomatis. Fitur hapus sesi tidak masuk versi pertama. CSV menyimpan validity, fase, device uptime, host receive time, target/rencana dan penanda simulasi; waktu perangkat tidak dianggap clock UTC tersinkron presisi.

## 11 Window Diagnostik dan Tuning

### 11.1 Diagnostik yang tersedia

Panel menampilkan SystemHealth, status estimator, freshness state, mode/reject reason, diagnostik agent Teensy/ESP, status actuator, delapan command thruster, saturasi allocator, residual, dan status mock/physical output. Command yang dilaporkan backend adalah output software, bukan measured thrust atau RPM.

Fault/reconnect counter ditampilkan bersama perubahan terhadap baseline sesi GUI. Counter besar yang tidak bertambah tidak otomatis dilabeli gangguan aktif. Detail INA, I2C, sensor serta heartbeat timeout berada di sini; dashboard hanya memuat ringkasannya. Status SysID dapat dibaca, tetapi start/stop eksperimen tetap lewat terminal.

### 11.2 Tuning controller sementara

Parameter awal yang relevan adalah depth Kp, roll/pitch/yaw Kp dan Kd, batas rate depth/yaw, batas sudut roll/pitch, serta deadzone. Nilai sekarang ditetapkan firmware; belum tersedia request/status runtime. GUI menampilkan read-only atau belum tersedia sampai board benar-benar melaporkan parameter/capability.

Pengubahan memakai alur edit, validasi, Apply, ACK, lalu nilai aktif. Backend harus membedakan draft dari active snapshot. Apply awal hanya di IDLE dan tidak ada misi/SysID aktif. NaN, infinity, tipe yang salah, field tidak dikenal, dan nilai di luar rentang ditolak di backend dan firmware. Tidak ada Apply otomatis saat slider digeser.

Profil konfigurasi berisi ID/revisi, jenis controller, versi firmware, nilai dan satuan, waktu apply serta hasil ACK. Profil disimpan di Jetson dan dapat diekspor/diimpor dengan validasi kompatibilitas. Simpan profil tidak sama dengan apply. Default firmware tidak ditimpa tanpa kontrak persistence yang eksplisit; GUI setelah reconnect/boot membaca kembali nilai board, bukan menganggap profil terakhir pasti aktif.

### 11.3 Pembatasan thruster

Skala manual adalah pengali input operator; batas output adalah ceiling perintah akhir yang berlaku untuk MANUAL, AUTO dan jalur keluaran lain yang disepakati. Pengaturan awal berupa satu batas seragam untuk delapan thruster, tanpa delapan slider individual. Nilai dinyatakan 0–100% rentang normalized command. Nol berarti tidak ada output propulsion, bukan menggantikan STOP/SAFE atau menghapus latch emergency.

Allocator sudah memiliki konfigurasi `max_abs_command`, tetapi batas yang dapat diubah dan dibaca lewat ROS/GUI belum tersedia. Batas harus ditegakkan di Teensy setelah allocation dan pada setiap jalur actuator yang relevan, tidak hanya dipakai untuk mengecilkan input browser. Firmware memverifikasi semua sumber mode, termasuk controlled-surface recovery; GUI tidak boleh menjadi satu-satunya enforcement.

Baseline dari firmware, batas yang diajukan, dan batas aktif ditampilkan terpisah. Tidak ada nilai awal baru yang diklaim aman untuk kendaraan riil sebelum karakterisasi. Validasi menguji clipping/skala, arah negatif, saturasi, dan transisi batas nol. Persentase perintah tidak disebut persentase daya listrik atau gaya dorong nyata.

### 11.4 LMPC di tahap berikutnya

Panel LMPC menampilkan status tersedia/tidak tersedia, identitas model, controller aktif, tracking error, solve time, hasil solver, pelanggaran constraint dan fallback. Bobot tracking/perubahan input serta bounds dapat disetel hanya jika implementasi mendukung runtime update yang atomik dan tervalidasi.

Horizon, model dan konfigurasi solver tidak otomatis menjadi slider runtime. Perubahan yang memerlukan synthesis/build diberi status membutuhkan build dan tidak menghasilkan ACK palsu. LMPC baru diaktifkan setelah geometri, karakterisasi thruster, wet SysID, identifikasi, validasi model independen, serta controller tersedia. Model HIL bukan model hidrodinamika tervalidasi.

Tidak ada parameter EA-DSRA di panel ini. SysID tidak menjadi tombol pengujian otomatis di GUI versi pertama.

## 12 Kamera dan streaming

Kebutuhan awal satu webcam USB pada Jetson. Operator dapat memilih kamera yang terdeteksi dan melihat stream tanpa plugin browser. Identitas kamera harus tahan perubahan `/dev/videoN`; format capture/encoding disesuaikan kemampuan perangkat. Backend tidak membaca kamera HP.

Spike menentukan jalur stream yang kompatibel dengan Pixel, browser laptop, Jetson dan tether FullDepth. Kandidat adalah WebRTC untuk latency rendah; alternatif sederhana hanya dipilih jika hasil uji CPU/bandwidth memenuhi target. Codec dan akselerasi tidak diasumsikan tersedia hanya karena perangkat adalah Jetson.

Target usulan awal 720p, 15 fps, satu stream, dengan latency tampilan maksimal 500 ms pada link yang diuji. Bitrate ditentukan setelah pengukuran tether. Dua browser tidak menggandakan proses capture/encode tanpa kebutuhan. Jika bandwidth turun, video menurunkan kualitas atau berhenti dengan status jelas; telemetry dan Stop tetap diprioritaskan. Perekaman video dan multi-kamera ditunda.

## 13 Kontrak data dan perintah yang sudah tersedia

| Fungsi | ROS yang ada | Catatan |
|---|---|---|
| State kendaraan | `/tyrant/simple_state` | Roll/pitch/yaw/depth dan validity |
| Kesiapan | `/tyrant/system/health` | Komunikasi, estimator, mode, propulsion |
| Mode | `/tyrant/mode/request` dan `/tyrant/mode/status` | Request ID, ACK/reject |
| Input manual | `/tyrant/manual/command` | Enam input normalized; tanpa absolute setpoint |
| Nol depth | `/tyrant/depth/reference/request` dan `/tyrant/depth/reference/status` | ACK dan referensi tekanan permukaan |
| Misi host | `/tyrant/host/mission/status` | String JSON; perlu parsing/version contract |
| Start/stop misi | `/tyrant/host/mission/start` dan `/stop` | Trigger service |
| Rekaman manual | `/tyrant/host/recording/start` dan `/stop` | Trigger service |
| Air | `<payload_ns>/water_quality` | Empat sensor dan age/validity |
| Daya | `<payload_ns>/power/sensors` dan `/power/thruster` | Dua INA, voltage/current/power |
| Sensor power | `<payload_ns>/sensor_power/request` dan `/status` | Request ID dan ACK GPIO |
| Thruster | `/tyrant/control/thruster_command` | Delapan applied software command |
| Actuator | `/tyrant/actuation/status` | Backend, physical output, PWM command |
| Diagnostik | `/tyrant/communication/diagnostics` dan `<payload_ns>/communication/diagnostics` | Counter dan status komunikasi |

Namespace ESP produksi adalah `/tyrant/payload`; HIL adalah `/tyrant/payload_sim`. Backend mempunyai satu konfigurasi namespace aktif dan menyajikan label profil. Tidak mencampur kedua namespace menjadi satu seri data atau menyembunyikan provenance SIM.

## 14 Interface dan perubahan yang masih dibutuhkan

Kebutuhan baru berikut adalah pekerjaan implementasi, bukan endpoint yang sudah aktif.

| Kebutuhan baru | Komponen yang berubah | Hasil yang diperlukan |
|---|---|---|
| Gateway GUI | Backend Jetson dan frontend | API state, event, command dan input manual |
| Load/save rencana | Host misi dan backend | Validasi dan pemilihan plan saat idle tanpa restart service |
| Status recorder | Host misi dan backend | Active session, finalized/error, duration dan disk |
| Absolute setpoint | Interface/firmware Teensy | Depth/heading target, mode gate, ACK dan target aktif |
| Tuning kontrol | Interface/firmware Teensy | Request/status, revision, bounds dan active values |
| Batas thruster | Interface/firmware Teensy | Enforcement lintas mode serta active ceiling |
| Riwayat grafik | Backend dan reader sesi | Query rentang waktu, decimation dan CSV asli |
| Webcam | Layanan Jetson dan frontend | Discovery, capture, stream dan video health |
| Capability | Teensy/host/backend | Fitur, versi schema, controller/profil dan batas dukungan |

Host saat ini membaca rencana dari parameter saat startup; mengubah file YAML saja tidak dijanjikan memperbarui rencana in-memory. Load plan baru harus atomik, idle-only, memakai validator yang sama, dan mengembalikan plan revision. Interface langsung untuk telemetry target depth/heading juga belum tersedia; GUI tidak menganggap target misi sama dengan held reference controller.

Skema Teensy tetap di paket Teensy, skema ESP tetap di paket payload. Tidak perlu perubahan firmware ESP untuk editor EA-DSRA. Metadata GUI/control event disimpan bersama rekaman atau sidecar yang terkait session ID, sehingga parameter/batas aktif dan perubahan operator dapat ditelusuri.

## 15 API backend yang diusulkan

HTTP dipakai untuk snapshot, daftar sesi, unduhan dan perintah diskret; satu kanal WebSocket untuk telemetry/event serta input manual. Naming endpoint final dapat berubah, tetapi kontrak perilaku berikut wajib tersedia.

State memuat schema version, waktu server, umur data, provenance, state board, capability, source input, plan revision, recording state, dan last command result. Perintah membawa client command ID, request ID ROS bila ada, payload tervalidasi, dan revision aktif yang diharapkan untuk konfigurasi.

Status perintah dibedakan menjadi diterima backend, menunggu board, diterima board, ditolak dan timeout. Untuk Start misi, service sukses berarti sesi start diterima; keberhasilan misi baru berasal dari hasil akhir host. Apply parameter tidak menampilkan aktif sebelum ACK dan readback board sesuai revision.

Retries perintah diskret memakai ID yang sama dan tidak mengulang start misi/rekaman. Backend membatasi satu perubahan konfigurasi in-flight; browser lain melihat status pending. Saat koneksi kembali, browser mengambil snapshot; tidak mengirim ulang queue lama. Stop dapat diterima dari semua browser dan memiliki prioritas di atas konfigurasi/input gerak.

Unduhan hanya menerima session ID yang diindeks, bukan path bebas dari browser. Akses web dibatasi jaringan operasional; pengaturan origin dan payload validation diterapkan. Tidak ada terminal shell atau endpoint arbitrary ROS publish di GUI produk. Tidak diperlukan sistem akun/peran pada versi awal.

## 16 Freshness dan keadaan terputus

State UI menggunakan waktu penerimaan monotonic backend serta age/validity sumber. Timestamp uptime ESP/Teensy tidak dikurangkan langsung dari UTC. Counter yang mundur menandai sesi perangkat baru jika tidak ada boot ID eksplisit.

Target refresh state navigasi UI 10 Hz, diagnostik 1 Hz, dan nilai air ketika pembacaan baru tersedia. Freshness keselamatan memakai aturan host/firmware yang sudah ada; refresh grafis bukan heartbeat. Data air tidak dianggap stale hanya karena tidak berubah selama satu detik, sebab EA-DSRA dapat memberi interval 5 detik dan stale threshold sekarang 6,5 detik.

Jika browser–backend putus, GUI menampilkan offline, menghentikan input manual, dan tidak menampilkan perintah sebagai diterima. Jika Teensy terputus/state invalid, readiness dan kontrol mengikuti host/firmware. Jika ESP terputus, navigasi tetap tampil dan sensor ditandai terputus; sampling mengikuti kebijakan timeout. Jika kamera terputus, telemetry tetap berjalan. Jika backend mati tetapi host masih hidup, AUTO dapat berlanjut; setelah backend hidup ia merekonstruksi state, bukan memulai misi baru.

## 17 Kebutuhan nonfungsional

| Aspek | Target awal untuk pengujian |
|---|---|
| Perangkat | Chrome laptop dan Chrome Pixel 7 Pro diuji pada versi aktual |
| Pengguna bersamaan | Minimal dua browser; state dan hasil perintah konsisten |
| Offline | UI, grafik dan kontrol lokal tanpa internet/CDN |
| Kontrol manual | 20 Hz usulan; TTL gateway 150 ms; timeout Teensy tetap 250 ms |
| Navigasi UI | Target 10 Hz; tidak membuat data sensor baru |
| Kamera | Target 720p 15 fps; latency ≤500 ms pada konfigurasi uji |
| Perintah diskret | Status pending terlihat segera; ACK/timeout menurut perangkat |
| Stabilitas | Uji dua browser selama 60 menit tanpa pertumbuhan buffer tak terbatas |
| Resource | Ukur CPU/RAM Jetson 4 GB; ROS/heartbeat tidak terganggu render/video |
| Penyimpanan | Recorder menjaga gate 512 MiB; tidak menghapus sesi otomatis |
| Konfigurasi | Draft/active/revision jelas dan readback setelah reconnect |

Target performa adalah sasaran validasi, bukan hasil benchmark yang sudah dicapai. Video tidak boleh mengorbankan freshness manual/state. Telemetry dikirim dengan buffer terbaru; data realtime lama tidak menumpuk saat koneksi lambat. Grafik historis dipaginasi atau didecimate di backend.

## 18 Kebutuhan perangkat dan bahan pengerjaan

Perangkat yang dibutuhkan adalah Jetson dan container ARM64 yang ada, Teensy HIL/produksi sesuai tahap, ESP-S3 SIM/produksi sesuai tahap, laptop, Pixel 7 Pro, controller Bluetooth, hub/adaptor USB-C LAN, kabel Ethernet, dan dua modul powerline FullDepth beserta tether/catu daya yang sesuai. Switch diperlukan jika laptop dan HP tersambung kabel bersamaan. Webcam USB dibutuhkan untuk kualifikasi streaming.

Bahan yang perlu dilengkapi adalah model controller dan mapping browser, merek/chipset hub Pixel, model/pinout FullDepth, model dan format webcam, model 3D atau orientasi sumbu kendaraan, parameter kontrol yang benar-benar didukung, baseline batas thruster, serta nama/version schema capability dan tuning. Kalibrasi suhu dan konfigurasi thruster riil tetap prasyarat pengukuran/actuation hardware.

Data HIL yang sudah ada dipakai untuk mockup dan uji integrasi. Tampilan data contoh harus selalu berlabel SIM. Nilai contoh tidak menjadi default parameter operasi hardware. Tidak diperlukan hardware sensor riil untuk menyelesaikan mockup, parser telemetry, recorder view, atau pengujian alur GUI HIL.

## 19 Tahapan pengerjaan dan dependensi

### 19.1 Tahap pertama mockup empat window

Bangun empat window responsif dengan data contoh, state valid/invalid/pending, mode SIM, grafik, placeholder kamera, dan panel parameter read-only. Review laptop serta Pixel landscape/portrait. Hasil tahap ini adalah tampilan/alur, tanpa klaim koneksi board.

### 19.2 Tahap kedua spike perangkat dan jaringan

Uji Gamepad API pada Pixel/controller, axes/deadman/disconnect, keyboard focus, HTTPS lokal, adaptor Ethernet, dua browser dan link FullDepth. Uji webcam capture/codec CPU. Tahap ini menyelesaikan ketidakpastian perangkat sebelum kontrol hardware GUI.

### 19.3 Tahap ketiga backend monitoring dan rekaman

Hubungkan telemetry yang sudah ada, validity/freshness, status koneksi, INA, power ACK, log, mission status, recording state, daftar sesi dan CSV. Integrasi mengikuti supervisor Jetson tanpa publisher/agent duplikat. Tambahkan load plan dan recorder status pada host dengan tes kontrak.

### 19.4 Tahap keempat kontrol dan planner

Implementasikan input keyboard/controller, source selection, deadman/TTL, mode/Stop, editor plan dan start/stop misi. Absolute setpoint serta readback target memerlukan diskusi desain interface dan firmware Teensy sebelum implementasi. Uji seluruh jalur pada HIL terlebih dahulu.

### 19.5 Tahap kelima tuning dan batas thruster

Tambahkan kontrak parameter, revision/ACK/readback, batas output firmware, penyimpanan profil dan event recording. Uji IDLE-only apply dan enforcement lintas sumber/mode. LMPC tetap belum tersedia sampai pipeline identifikasi/controller selesai.

### 19.6 Tahap keenam kualifikasi lapangan

Uji GUI end-to-end lewat tether, controller Pixel, dua perangkat dan webcam. Kemudian gunakan profil hardware yang sesuai setelah sensor, geometri, ESC/thruster, referensi depth dan kalibrasi tervalidasi. Uji HIL tidak menggantikan pengujian hardware tersebut.

## 20 Kriteria penerimaan

| ID | Skenario | Hasil yang wajib dibuktikan |
|---|---|---|
| UI01 | Laptop dan Pixel landscape/portrait | Empat tab terbaca; tidak ada overflow horizontal halaman |
| UI02 | Kamera fullscreen | Depth, mode, koneksi dan Stop tetap dapat diakses |
| UI03 | Invalid/stale sensor | Label dan umur jelas; bukan angka nol atau data live palsu |
| NAV01 | Injeksi roll/pitch/yaw/depth HIL | Model/sumbu/kompas/Z sesuai arah dan angka |
| NET01 | Dua browser membuka GUI | State bersama; tidak ada host/agent/heartbeat duplikat |
| CMD01 | Mode/power ditolak board | UI kembali ke actual state dan menampilkan alasan |
| CMD02 | Dua start atau retry ID sama | Satu sesi, tidak ada misi/rekaman duplikat |
| MAN01 | Keyboard/controller dan deadman | Gerak hanya MANUAL dengan stream yang fresh |
| MAN02 | Blur, background, BT/socket putus | Input lama tidak diperbarui; latensi netral diukur |
| MAN03 | Dua sumber/perangkat mencoba manual | Satu stream aktif; perubahan sumber menetralkan input |
| MAN04 | Stop saat deadman masih ditahan | SAFE diminta; enable baru diperlukan sebelum gerak lagi |
| DEP01 | Set Surface dan Naik ke Permukaan | Tindakan berbeda; reject/precondition board ditampilkan |
| MIS01 | Dua titik sampling HIL | Counts per sensor dan hasil akhir sesuai bag/CSV |
| MIS02 | Sensor gagal | Titik incomplete terlihat; kelanjutan sesuai kebijakan host |
| MIS03 | Plant/state Teensy hilang | FAILED dan STOP/SAFE; tidak menyatakan motion selesai |
| MIS04 | Browser putus saat AUTO | Host melanjutkan sesuai kondisi onboard; reconnect membaca state |
| REC01 | Manual record dan misi | Satu recorder; file finalized dan dapat dibaca |
| REC02 | UTC/WIB dan uptime | Tampilan waktu benar; tidak mengklaim presisi sync perangkat |
| TUN01 | Apply saat aktif/invalid/out of bounds | Ditolak tanpa mengubah konfigurasi aktif |
| TUN02 | Apply diterima dan reconnect | Revision/nilai aktif mengikuti ACK serta readback board |
| THR01 | Batas output lintas mode | Seluruh applied command mematuhi ceiling Teensy |
| THR02 | Batas nol dan input negatif | Output netral/bounded; saturasi tampil; tidak menghapus fault latch |
| CAM01 | Webcam dan dua browser | Stream sesuai target terukur; heartbeat/control tidak terganggu |
| SYS01 | SysID/EA-DSRA | Tidak ada start SysID atau editor EA-DSRA GUI |
| BOOT01 | Restart/reboot Jetson | GUI dapat diakses lagi, host IDLE, tidak replay command atau resume misi |

Nilai latency, load dan bitrate yang diukur disimpan bersama versi frontend/backend/firmware, perangkat, profil SIM/real serta konfigurasi tether. Fitur yang belum memenuhi kriterianya tetap tidak tersedia/read-only, bukan disamarkan oleh data contoh.

## 21 Keputusan teknis yang masih perlu ditutup

Detail mapping keyboard/controller, model FullDepth/hub/webcam, address/DHCP jaringan tether, sertifikat HTTPS, codec video, format API parameter dan capability, persistence board, serta daftar parameter LMPC belum final. Semua ini dicatat sebagai pekerjaan spike/desain; tidak menghalangi mockup empat window.

Nilai TTL gateway, refresh, viewport dan video dalam dokumen merupakan usulan implementasi untuk diuji. Nilai controller/batas thruster hardware harus ditetapkan dari capability dan karakterisasi, bukan dipilih dari layout GUI. Perubahan firmware Teensy untuk setpoint/tuning/ceiling perlu dibahas secara konkret sebelum pengerjaan.

## 22 Dokumen dan source pendukung

Mockup review 10 Oktober 2026 tersedia di `gui/mockup/index.html`, dengan petunjuk dan batas preview pada `gui/mockup/README.md`. Mockup memakai data sintetis, model orientasi skematis, kamera placeholder, misi dipercepat dan CSV dalam memori. Toleransi/waktu stabil/jumlah sampel menunjukkan bentuk konfigurasi; belum memakai validator maupun recorder host riil. Browser controller masih tahap pemeriksaan axes, bukan teleop yang telah dikualifikasi. Mockup tidak mengirim ROS/serial/perintah ke hardware.

Revisi visual 02 menambahkan kamera dominan dengan overlay navigasi, panel navigasi gabungan, baris sensor ringkas, mode global, log yang dapat diperluas, fullscreen kamera dalam area browser, alasan kesiapan, umur data, serta ringkasan misi pada Operasi. Fullscreen tetap menyediakan Stop; Escape di dialog hanya menutup kamera, sedangkan Escape di luar dialog melakukan Stop contoh. Jumlah sampel dan progress tetap sintetis. Revisi ini merupakan percobaan desain untuk review pengguna, belum persetujuan final tampilan atau implementasi kontrol backend.

Dokumen internal: `docs/architecture.md`, `docs/coordinate_convention.md`, `docs/teleop.md`, `docs/payload_mission_host.md`, `docs/sysid.md`, `docs/jetson_autostart.md`, serta laporan deployment/HIL 10 Oktober 2026. Source kontrak: `ros2_ws/src/tyrant_interfaces/msg`, `ros2_ws/src/tyrant_payload_interfaces/msg`, host `core.py`/`node.py`, konfigurasi kontrol Teensy dan `firmware/esp/src/ea_dsra.cpp`.

Referensi tampilan: [Cockpit usage](https://blueos.cloud/cockpit/docs/stable/usage/getting-started/). Referensi input browser: [Gamepad specification](https://w3c.github.io/gamepad/). Referensi ini memandu desain dan pengujian; tidak membuktikan kompatibilitas controller atau powerline FullDepth yang belum diidentifikasi.

Markdown menjadi sumber spesifikasi yang mudah diperbarui. Salinan Word dapat diterbitkan setelah berhasil dirender dan diperiksa tampilannya; pada revisi ini pemeriksaan tersebut terhalang kompatibilitas pustaka Linux renderer. Revisi berikutnya mencatat keputusan baru tanpa menimpa PRD kendaraan versi sebelumnya.

## 23 Revisi GUI 03 dan pekerjaan integrasi berikutnya

Pada revisi 03 preview mendukung pilihan navigasi Terpadu/Panel (dihapus pada revisi 04), attitude indicator transparan pada kamera dan fullscreen, panah urutan atas/bawah, sampling ON/OFF pada keenam jenis langkah dengan waktu selama/sesudah, serta nol yaw misi dan bantuan yang hanya muncul saat tombol ? ditekan. Layout mengikuti lebar perangkat; viewport tidak melarang zoom browser/pinch. Dukungan gesture pada Pixel tetap harus diuji di perangkat riil. Video riil harus mempertahankan aspect ratio sumber, bukan diregangkan mengikuti rasio layar.

Pada preview, penanda stabilitas memakai riwayat depth sintetis pada jendela yang dipilih dan rentang 0,05 m. Tidak ada riwayat cukup atau perubahan melebihi rentang menghasilkan BELUM STABIL; ini tidak menghentikan pengambilan contoh. CSV simulasi menyimpan heading asli, yaw misi, flag referensi, offset dan depth_stable. Heading referensi dikunci selama misi aktif. Semua ini belum integrasi ROS.

Pekerjaan sebelum menghubungkan revisi 03 ke Jetson: (1) perluas validator dan engine host untuk sampling selama/sesudah semua tipe; (2) pertahankan raw recording dengan association depth dan penanda kualitas terpisah; (3) simpan frame yaw dan offset dalam metadata rencana/sesi, konversi target di satu pemilik backend, serta ACK/readback acuan aktif; (4) uji schema baru, kuota yang tidak terpenuhi, OFF sensor, payload reboot dan koneksi terputus tanpa merusak preset HIL lama. Evaluasi firmware Teensy/ESP dilakukan setelah kontrak host tersebut disusun; jangan mengubah yaw estimator untuk membuat nol misi.

Hal yang masih kurang pada preview: sumber input global/ownership antar-browser belum aktif; fullscreen menampilkan ringkasan link dan REC, sementara diagnostik per-board tetap di window utama; association sensor menggunakan data sintetis yang serempak, bukan age/clock board sebenarnya; toleransi target misi belum dikontrol secara fisik; preset, export/import rencana dan actual video belum tersedia. Fokus implementasi berikutnya adalah kontrak backend dan kelengkapan penanda data, bukan menambah panel baru.


## 24 Revisi GUI 04 · 10 Oktober 2026

Keputusan tampilan terkini adalah navigasi terpadu saja pada kamera, tanpa mode Panel dan tanpa sekat card antar-instrumen. Latar overlay dibuat tipis/transparan dan boleh diblur; visualisasi orientasi, kompas, indikator dan teks tidak boleh diblur. Attitude indicator dan akses Stop tetap tersedia pada fullscreen.

Grafik menampilkan titik pembacaan, skala nilai adaptif, waktu dan detail titik (nilai/unit, sequence, depth, validity dan penanda stabilitas). Mouse, sentuh dan keyboard dapat memilih titik. Rentang 1/5/15 menit serta pembekuan tampilan tidak menghentikan pencatatan. OFF/invalid membentuk celah dan tidak menghapus histori. Tidak ada interpolasi menjadi nol atau pengisian periode tanpa data. Preview menyimpan maksimal 900 titik/kanal dengan data sintetis; backend kelak menggunakan waktu penerimaan/acquisition serta age per kanal sesuai kontrak payload.

Planner preview menambahkan effort persen, timeout detik dan toleransi per langkah dalam meter atau derajat. Effort gerakan nol dan timeout ≤ durasi langkah berwaktu ditolak. ID langkah tetap ketika urutan berubah dan konfigurasi dikunci selama misi. Backend wajib melakukan konversi effort persen ke [-1,1], derajat ke radian dan durasi ke milidetik sesuai MissionCommand, memakai validator host, serta menyimpan snapshot rencana. Parameter ini belum mengontrol simulasi plant atau controller board dari browser.

Daya sensor memakai pending/request_id/ACK sebelum mengganti status terkonfirmasi. Sesuai ESP, heartbeat host tidak sehat menolak ON dengan reason 5 tetapi tidak menghalangi OFF selama transport dapat menerima perintah. Actual enabled berarti GPIO yang diperintahkan, bukan feedback listrik. Pembacaan ON tidak langsung valid sebelum sampel baru. Dua monitor daya menampilkan voltage/current/power_w; INA rail sensor tidak menyediakan arus setiap sensor secara individual.

CSV preview kini 21 kolom dengan heading_valid, step_id, sampling_timing dan phase selain penanda revisi 03. Heading invalid dikosongkan. Data masih sintetis dan serempak; association acquisition per kanal pada recorder host tetap harus dipertahankan saat integrasi.

Pemeriksaan browser revisi 04 lulus: overlay tunggal/blur latar saja, pending dan aturan ON/OFF heartbeat ESP, grafik titik/detail/rentang/bekukan, validasi effort/timeout, misi contoh dan CSV 21 kolom, serta empat window dan fullscreen pada 840×390, 390×840 dan 320×720 tanpa overflow horizontal halaman atau error JavaScript. Belum merupakan uji hardware atau Jetson. Rincian perubahan, acuan source serta pekerjaan tersisa terdapat pada `docs/gui_mockup_review_2026-10-10.md`. Revisi ini hanya mengubah frontend dan dokumentasi; tidak mengubah firmware atau node ROS.


## 25 Review lanjutan dan gateway telemetry awal

Pengguna meminta sekat tipis antara orientasi 3D, kedalaman dan yaw/kompas. Ini menggantikan keputusan tanpa sekat pada bagian 24; tetap satu navigasi terpadu dengan latar transparan dan blur latar saja. Garis mengikuti layout desktop/HP, tanpa card terpisah.

Gateway tahap pertama tersedia di `gui/backend/server.py`: GET `/api/state` membawa 15 stream telemetry ROS dengan source, namespace/profil payload, data asli, reception age dan status missing/stale. Capability kontrol/manual/kamera belum tersedia; POST ditolak. Gateway tidak membuat publisher heartbeat, agent atau recorder. Frontend mockup belum membaca gateway dan tetap SIM. Clock umur penerimaan tidak menggunakan uptime board; float nonfinite menjadi null dan validity asli tetap disimpan.

Empat pengujian snapshot, pemuatan 15 interface ROS dan uji HTTP startup/snapshot/penolakan POST berhasil pada laptop. Telemetry board riil dan deployment gateway Jetson belum diuji. Petunjuk menjalankan dan batas kontrak ada di `gui/backend/README.md`. Integrasi frontend live dan kontrak command/ACK merupakan tahap berikutnya; perluasan sampling host tetap belum diterapkan.


## 26 Panduan kesiapan hardware dan kontrol — 13 Oktober 2026

Alur setup menyeluruh tersedia pada `docs/PANDUAN_SETUP_KONTROL_SYSID_LMPC.md`: port tetap, sumber proses/heartbeat, profil firmware, sensor, gerbang PWM/geometri, manual wet, tuning P/PD, SysID dan pekerjaan implementasi LMPC. Hardware belum cukup dengan perubahan pin: geometri produksi, karakterisasi actuator, kalibrasi sensor dan LMPC tetap belum selesai. Depth controller sekarang P; roll/pitch/yaw PD.

GUI read-only dapat diuji sebelum LMPC, sedangkan kontrol riil memerlukan actuator/manual/failsafe dan kontrak command/ACK. Panduan tersebut tidak mengesahkan hardware atau LMPC dan tidak mengubah firmware.

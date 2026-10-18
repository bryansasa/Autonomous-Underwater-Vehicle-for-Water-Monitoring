# -*- coding: utf-8 -*-
"""
Script Generator PDF Buku Panduan Pengoperasian GCS Tyrant-AQ AUV v2.0
Menggunakan ReportLab Platypus dengan Standar Dokumentasi Teknik & Tugas Akhir.
"""
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas yang otomatis menghitung total halaman dan menggambar header/footer profesional."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Halaman sampul tanpa header/footer
        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#475569"))
        # Running Header
        self.drawString(54, 804, "TYRANT-AQ AUV GROUND CONTROL STATION (GCS) v2.0")
        self.setFont("Helvetica", 7.5)
        self.drawRightString(541, 804, "PANDUAN OPERASIONAL & KENDALI SISTEM")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(54, 798, 541, 798)

        # Running Footer
        self.line(54, 44, 541, 44)
        self.drawString(54, 32, "Tugas Akhir: Sistem Pemantauan Kualitas Air Waduk Saguling & Wahana Selam AUV")
        page_text = f"Halaman {self._pageNumber} dari {page_count}"
        self.setFont("Helvetica-Bold", 7.5)
        self.drawRightString(541, 32, page_text)
        self.restoreState()


def create_manual_pdf(output_pdf_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Warna Palet Desain
    C_PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    C_ACCENT = colors.HexColor("#0284C7")     # Sky 600
    C_SUCCESS = colors.HexColor("#16A34A")    # Green 600
    C_WARNING = colors.HexColor("#D97706")    # Amber 600
    C_DANGER = colors.HexColor("#DC2626")     # Red 600
    C_MUTED = colors.HexColor("#475569")      # Slate 600
    C_LIGHT_BG = colors.HexColor("#F8FAFC")   # Slate 50
    C_BORDER = colors.HexColor("#E2E8F0")     # Slate 200

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=C_PRIMARY,
        alignment=0,
        spaceAfter=8
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=C_ACCENT,
        spaceAfter=15
    )
    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=C_MUTED
    )
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=C_PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=C_ACCENT,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )
    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=C_MUTED,
        alignment=1,
        spaceAfter=8
    )
    callout_text = ParagraphStyle(
        'CalloutText',
        parent=body_style,
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F172A")
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=8,
        leading=11,
        spaceAfter=0
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=C_PRIMARY,
        spaceAfter=0
    )
    table_hdr = ParagraphStyle(
        'TableHdr',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.white,
        spaceAfter=0
    )

    story = []

    # =========================================================================
    # 1. HALAMAN SAMPUL (COVER PAGE)
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("BUKU PANDUAN PENGOPERASIAN", ParagraphStyle('Badge', fontName='Helvetica-Bold', fontSize=10, textColor=C_ACCENT, spaceAfter=4)))
    story.append(Paragraph("Ground Control Station (GCS) Wahana Selam Tyrant-AQ AUV", title_style))
    story.append(Paragraph("Sistem Telemetri Real-Time, Kendali 6-DOF, Manajemen Daya Ganda (Dual INA226), dan Penghematan Energi Adaptif (EA-DSRA)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=C_ACCENT, spaceAfter=15))

    # Info Box Metadata
    meta_data = [
        [Paragraph("<b>Status Sistem:</b>", table_cell), Paragraph("Versi 2.0 (Dual Battery & EA-DSRA Ready)", table_cell),
         Paragraph("<b>Target Hardware:</b>", table_cell), Paragraph("ESP32-S3 micro-ROS & Teensy 4.1 LMPC", table_cell)],
        [Paragraph("<b>Paket Distribusi:</b>", table_cell), Paragraph("Standalone Portable (Tyrant-AQ_GCS.exe)", table_cell),
         Paragraph("<b>Lokasi Observasi:</b>", table_cell), Paragraph("Waduk Saguling, Jawa Barat", table_cell)],
        [Paragraph("<b>Arsitektur Daya:</b>", table_cell), Paragraph("2x Baterai Fisik Terpisah (Thruster & Sensor)", table_cell),
         Paragraph("<b>Standar Baku Mutu:</b>", table_cell), Paragraph("PP No. 22 Tahun 2021 (Kelas 2)", table_cell)],
    ]
    t_meta = Table(meta_data, colWidths=[90, 150, 95, 152])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # Gambar Cuplikan Layar Utama Sampul (Dark Mode)
    img_dark = os.path.join("docs", "manual_images", "tab1_navigasi_dark.png")
    if os.path.exists(img_dark):
        story.append(Image(img_dark, width=485, height=272))
        story.append(Paragraph("Gambar 1. Tampilan Utama Ground Control Station (GCS) Tyrant-AQ AUV v2.0 (Dark Mode)", caption_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Dokumentasi Resmi Pasca-Integrasi:</b> Panduan ini dirancang untuk operator lapangan, peneliti, dan penguji perangkat keras guna mengoperasikan antarmuka kendali dan diagnostik wahana selam Tyrant-AQ secara aman dan terstandar.", meta_style))
    story.append(PageBreak())

    # =========================================================================
    # 2. BAB 1: PENDAHULUAN & ARSITEKTUR SISTEM
    # =========================================================================
    story.append(Paragraph("1. Pendahuluan & Arsitektur Sistem", h1_style))
    story.append(Paragraph(
        "Ground Control Station (GCS) Tyrant-AQ AUV merupakan stasiun kendali permukaan berbasis desktop yang dikembangkan menggunakan Python 3 dan framework PyQt5. GCS bertugas menerima telemetri frekuensi tinggi (10 Hz), memvisualisasikan orientasi 3D dan matriks 6 pendorong (thruster), memantau parameter kualitas air danau/waduk, serta mengirimkan setpoint navigasi dan perintah kendali darurat.",
        body_style
    ))
    story.append(Paragraph(
        "Pada versi 2.0 ini, GCS telah diintegrasikan secara penuh dengan firmware micro-ROS pada ESP32-S3 milik Charisto serta pengendali Teensy 4.1. Fitur utama yang telah terintegrasi mencakup <b>Manajemen Dua Baterai Fisik Terpisah (Dual INA226)</b>, <b>Modulasi Interval Sampling Dinamis EA-DSRA</b>, dan <b>Dukungan Tema Ganda (Dark Mode & Light Mode)</b>.",
        body_style
    ))

    story.append(Paragraph("1.1 Arsitektur Baterai Ganda (Dual Battery System)", h2_style))
    story.append(Paragraph(
        "Untuk mencegah penurunan tegangan (voltage drop/brownout) pada sensor mikro dan mikrokontroler akibat lonjakan arus pendorong, wahana menggunakan 2 paket baterai fisik yang terisolasi:",
        body_style
    ))

    batt_table_data = [
        [Paragraph("Parameter", table_hdr), Paragraph("Baterai 1: Bus Thruster", table_hdr), Paragraph("Baterai 2: Sensor & Mikrokontroler", table_hdr)],
        [
            Paragraph("<b>Fungsi Beban</b>", table_cell_bold),
            Paragraph("Menyalakan 6 unit Electronic Speed Controller (ESC) & Brushless Thruster T200", table_cell),
            Paragraph("Menyalakan mikrokontroler (ESP32-S3, Teensy 4.1) & sensor kualitas air (pH, DO, EC, Suhu)", table_cell)
        ],
        [
            Paragraph("<b>Sensor Pengukur</b>", table_cell_bold),
            Paragraph("<b>INA226 #1</b> (Topik: <code>/tyrant/payload/power/thruster</code>)", table_cell),
            Paragraph("<b>INA226 #2</b> (Topik: <code>/tyrant/payload/power/sensors</code>, Shunt R100)", table_cell)
        ],
        [
            Paragraph("<b>Rentang Tegangan</b>", table_cell_bold),
            Paragraph("6S LiPo: 19.8 V (Min) s/d 25.2 V (Maks), Nominal 22.2 V", table_cell),
            Paragraph("3S LiPo / Rel Elektronik: 9.9 V s/d 12.6 V, Nominal 11.1 V - 12.0 V", table_cell)
        ],
        [
            Paragraph("<b>Karakter Arus</b>", table_cell_bold),
            Paragraph("Arus tinggi (2.0 A s/d 25.0 A bergantung manuver pendorong)", table_cell),
            Paragraph("Arus rendah presisi (0.15 A s/d 0.35 A dengan power gating MOSFET)", table_cell)
        ],
        [
            Paragraph("<b>Estimasi State of Charge</b>", table_cell_bold),
            Paragraph("1D Kalman Filter pada tegangan baterai (mengabaikan ripple noise)", table_cell),
            Paragraph("Kalkulasi linear rasio tegangan rel terhadap batas proteksi 3S", table_cell)
        ],
    ]
    t_batt = Table(batt_table_data, colWidths=[100, 193, 194])
    t_batt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_batt)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1.2 Menjalankan Aplikasi Portable Tanpa Python", h2_style))
    story.append(Paragraph(
        "Aplikasi GCS telah dikompilasi menjadi paket Windows Standalone yang tidak membutuhkan instalasi Python maupun library eksternal di laptop operator. Langkah peluncuran:",
        body_style
    ))
    story.append(Paragraph("1. Ekstrak file <code>Tyrant-AQ_GCS_v2.0_Windows.zip</code> ke direktori laptop (misal: <code>C:\\Tyrant-AQ_GCS\\</code>).", bullet_style))
    story.append(Paragraph("2. Buka folder hasil ekstrak dan jalankan <code>Tyrant-AQ_GCS.exe</code> dengan klik ganda.", bullet_style))
    story.append(Paragraph("3. Window stasiun kendali akan terbuka seketika dengan mode default <b>SIMULASI (DUMMY)</b> aktif, siap diuji coba tanpa hardware fisik.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # 3. BAB 2: PANDUAN HEADER & QUICK ACTION BAR
    # =========================================================================
    story.append(Paragraph("2. Panduan Header & Quick Action Bar", h1_style))
    story.append(Paragraph(
        "Quick Action Bar terletak di bagian paling atas jendela aplikasi dan dapat diakses dari tab mana pun. Bagian ini menyediakan tombol kontrol krusial dan indikator keselamatan yang harus dipantau operator selama misi.",
        body_style
    ))

    # Tabel Penjelasan Action Bar
    act_data = [
        [Paragraph("Komponen", table_hdr), Paragraph("Fungsi & Operasi", table_hdr), Paragraph("Status / Perilaku", table_hdr)],
        [
            Paragraph("<b>MODE (Simulator/Hardware)</b>", table_cell_bold),
            Paragraph("Mengalihkan antara mode simulasi internal (dummy 6-DOF) dan komunikasi hardware riil.", table_cell),
            Paragraph("Merah: Mode Simulasi Aktif<br/>Biru: Siap Terhubung ke Hardware", table_cell)
        ],
        [
            Paragraph("<b>CONNECT / DISCONNECT</b>", table_cell_bold),
            Paragraph("Membuka koneksi Ethernet TCP (default: <code>192.168.1.170:9000</code>) atau Serial USB ke wahana.", table_cell),
            Paragraph("Biru: CONNECT (Terputus)<br/>Hijau: CONNECTED (Terhubung)", table_cell)
        ],
        [
            Paragraph("<b>FOXGLOVE BRIDGE</b>", table_cell_bold),
            Paragraph("Mengaktifkan server WebSocket internal pada port 8765 untuk visualisasi 3D di Foxglove Studio.", table_cell),
            Paragraph("OFF (Abu-abu): Nonaktif<br/>ON (Hijau): Menyiarkan data WS", table_cell)
        ],
        [
            Paragraph("<b>NAV MODE SELECTOR</b>", table_cell_bold),
            Paragraph("Memilih mode navigasi wahana (LMPC AUTO, PID HOLD, MANUAL 6-DOF).", table_cell),
            Paragraph("Mengirimkan perintah mode ke Teensy 4.1 secara instan", table_cell)
        ],
        [
            Paragraph("<b>ARM / DISARM</b>", table_cell_bold),
            Paragraph("Tombol keselamatan daya ESC pendorong. Saat DISARM, pendorong terkunci aman pada PWM 1500 µs.", table_cell),
            Paragraph("Merah: ARMED (Pendorong Aktif!)<br/>Abu-abu: DISARMED (Aman)", table_cell)
        ],
        [
            Paragraph("<b>BATT READOUT (Ganda)</b>", table_cell_bold),
            Paragraph("Menampilkan tegangan dan persentase kedua baterai fisik secara berdampingan: <code>BATT [T: 24.8V (95%) | S: 12.1V]</code>.", table_cell),
            Paragraph("T = Baterai Thruster (6S)<br/>S = Baterai Sensor & MCU (3S)", table_cell)
        ],
        [
            Paragraph("<b>EMERGENCY KILL</b>", table_cell_bold),
            Paragraph("Tombol pemutus darurat seketika. Menetralkan seluruh 6 pendorong ke PWM 1500 µs dan mematikan perintah gerak.", table_cell),
            Paragraph("Dapat ditekan langsung atau melalui tombol <b>[SPASI]</b> pada keyboard", table_cell)
        ],
    ]
    t_act = Table(act_data, colWidths=[120, 247, 120])
    t_act.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_act)
    story.append(Spacer(1, 10))

    # Callout Box Peringatan Keselamatan
    alert_box = [
        [Paragraph("<b>PERINGATAN KESELAMATAN (SAFETY PROTOCOL):</b><br/>Jangan pernah menekan tombol <b>ARMED</b> sebelum wahana berada di dalam air atau sebelum seluruh personil berada pada jarak aman dari baling-baling pendorong. Pendorong T200 memiliki torsi tinggi yang dapat mencederai operator jika terpicu di udara.", callout_text)]
    ]
    t_alert = Table(alert_box, colWidths=[487])
    t_alert.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ('BOX', (0, 0), (-1, -1), 1.5, C_DANGER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_alert)

    story.append(Spacer(1, 15))
    story.append(Paragraph("2.1 Opsi Tema Tampilan (Dark Mode vs Light Mode)", h2_style))
    story.append(Paragraph(
        "GCS dilengkapi dengan switch tema tampilan untuk mengoptimalkan kenyamanan pandangan operator pada kondisi pencahayaan berbeda:",
        body_style
    ))
    story.append(Paragraph("• <b>Dark Mode (Default):</b> Ideal untuk pengoperasian malam hari atau di dalam posko indoor bertenda untuk meminimalkan kelelahan mata.", bullet_style))
    story.append(Paragraph("• <b>Light Mode:</b> Didesain dengan latar belakang kontras tinggi (#FFFFFF dan #F8FAFC) khusus saat pengoperasian di lapangan terbuka (outdoor) di bawah terik sinar matahari Waduk Saguling.", bullet_style))

    img_light = os.path.join("docs", "manual_images", "tab1_navigasi_light.png")
    if os.path.exists(img_light):
        story.append(Spacer(1, 5))
        story.append(Image(img_light, width=485, height=272))
        story.append(Paragraph("Gambar 2. Tampilan GCS Tyrant-AQ pada Light Mode (Kontras Tinggi Lapangan Outdoor)", caption_style))

    story.append(PageBreak())

    # =========================================================================
    # 4. BAB 3: TAB 1 — NAVIGASI & KONTROL UTAMA
    # =========================================================================
    story.append(Paragraph("3. Tab 1 — Navigasi & Kontrol Utama", h1_style))
    story.append(Paragraph(
        "Tab Navigasi & Kontrol merupakan dashboard operasi harian wahana. Layar terbagi menjadi 3 kolom terstruktur:",
        body_style
    ))

    story.append(Paragraph("3.1 Kolom Kiri: Visualisasi Orientasi 3D & Matriks Pendorong", h2_style))
    story.append(Paragraph(
        "Kolom kiri menyajikan model wahana twin-hull dalam ruang 3D interaktif berbasis OpenGL. Model ini berputar secara real-time mengikuti sudut Roll, Pitch, dan Yaw dari sensor IMU. Di bagian bawah terdapat:",
        body_style
    ))
    story.append(Paragraph("• <b>Status Pendorong PWM (T1 s/d T6):</b> Bar indikator dinamis dengan rentang 1100 µs (mundur/turun) hingga 1900 µs (maju/naik), dengan titik netral 1500 µs.", bullet_style))
    story.append(Paragraph("• <b>Gaya Kontrol Virtual (4-DOF):</b> Menampilkan total gaya dorong terhitung (Surge Fx, Sway Fy, Heave Fz, dan Yaw Tz) serta margin headroom daya (misal: 79% Aman).", bullet_style))

    story.append(Paragraph("3.2 Kolom Tengah: Data Sensor Real-Time & Kontrol Gerak 6-DOF", h2_style))
    story.append(Paragraph(
        "Kolom tengah menampilkan 10 kapsul sensor (sensor pills) yang mencakup telemetri kualitas air dan daya baterai ganda:",
        body_style
    ))

    pill_data = [
        [Paragraph("Label Kapsul", table_hdr), Paragraph("Satuan / Format", table_hdr), Paragraph("Keterangan & Sumber Sensor", table_hdr)],
        [Paragraph("<b>DEPTH</b>", table_cell_bold), Paragraph("0.00 m", table_cell), Paragraph("Kedalaman wahana dari sensor tekanan MS5837 Teensy", table_cell)],
        [Paragraph("<b>Deviasi Z</b>", table_cell_bold), Paragraph("0.00 m", table_cell), Paragraph("Selisih antara kedalaman aktual dengan setpoint auto hold", table_cell)],
        [Paragraph("<b>BATT THRUSTER</b>", table_cell_bold), Paragraph("0.00 V (100%)", table_cell), Paragraph("Tegangan baterai 6S LiPo dari INA226 #1 (Kalman 1D)", table_cell)],
        [Paragraph("<b>ARUS THRUSTER</b>", table_cell_bold), Paragraph("0.00 A", table_cell), Paragraph("Total penarikan arus seluruh 6 pendorong (INA226 #1)", table_cell)],
        [Paragraph("<b>BATT SENSOR</b>", table_cell_bold), Paragraph("0.00 V (100%)", table_cell), Paragraph("Tegangan rel sistem elektronik & sensor (INA226 #2)", table_cell)],
        [Paragraph("<b>ARUS SENSOR</b>", table_cell_bold), Paragraph("0.00 A", table_cell), Paragraph("Arus konsumsi modul ESP32-S3 & probe (INA226 #2, R100)", table_cell)],
        [Paragraph("<b>DO</b>", table_cell_bold), Paragraph("0.00 mg/L", table_cell), Paragraph("Dissolved Oxygen (Oksigen Terlarut) dari modul EZO-DO", table_cell)],
        [Paragraph("<b>pH</b>", table_cell_bold), Paragraph("0.00", table_cell), Paragraph("Tingkat keasaman air dari modul probe EZO-pH", table_cell)],
        [Paragraph("<b>Temperature</b>", table_cell_bold), Paragraph("0.00 °C", table_cell), Paragraph("Suhu air waduk aktual dari sensor digital PT1000", table_cell)],
        [Paragraph("<b>Conductivity</b>", table_cell_bold), Paragraph("0.0 µS/cm", table_cell), Paragraph("Konduktivitas listrik / salinitas dari probe EZO-EC", table_cell)],
    ]
    t_pill = Table(pill_data, colWidths=[105, 95, 287])
    t_pill.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_pill)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3.3 Kontrol Manual Keyboard (Deadman Switch 6-DOF)", h2_style))
    story.append(Paragraph(
        "Untuk mengemudikan wahana secara manual, centang kotak <b>Aktifkan Kontrol Keyboard</b>. Sistem menggunakan pengaman <i>Deadman Switch</i>: wahana hanya bergerak selama tombol ditekan, dan otomatis berhenti (PWM 1500) saat tombol dilepas.",
        body_style
    ))

    key_data = [
        [Paragraph("Tombol Keyboard", table_hdr), Paragraph("Sumbu Gerak (DOF)", table_hdr), Paragraph("Aksi Wahana", table_hdr)],
        [Paragraph("<b>[W] / [S]</b>", table_cell_bold), Paragraph("Surge (Translasi X)", table_cell), Paragraph("W: Bergerak Maju | S: Bergerak Mundur", table_cell)],
        [Paragraph("<b>[A] / [D]</b>", table_cell_bold), Paragraph("Sway (Translasi Y)", table_cell), Paragraph("A: Geser Lateral Kiri | D: Geser Lateral Kanan", table_cell)],
        [Paragraph("<b>[R] / [F]</b>", table_cell_bold), Paragraph("Heave (Translasi Z)", table_cell), Paragraph("R: Naik ke Permukaan | F: Menyelam Turun", table_cell)],
        [Paragraph("<b>[Q] / [E]</b>", table_cell_bold), Paragraph("Yaw (Rotasi Z)", table_cell), Paragraph("Q: Belok Hadap Kiri | E: Belok Hadap Kanan", table_cell)],
        [Paragraph("<b>[I] / [K]</b>", table_cell_bold), Paragraph("Pitch (Rotasi Y)", table_cell), Paragraph("I: Pitch Menunduk (Nose Down) | K: Pitch Menengadah", table_cell)],
        [Paragraph("<b>[J] / [L]</b>", table_cell_bold), Paragraph("Roll (Rotasi X)", table_cell), Paragraph("J: Miring Kiri | L: Miring Kanan", table_cell)],
        [Paragraph("<b>[SPASI]</b>", table_cell_bold), Paragraph("STOP TOTAL (All Axes)", table_cell), Paragraph("Menghentikan seketika seluruh gerak translasi & rotasi", table_cell)],
    ]
    t_key = Table(key_data, colWidths=[110, 137, 240])
    t_key.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_key)

    story.append(PageBreak())

    # =========================================================================
    # 5. BAB 3 (LANJUTAN): EA-DSRA & PEREKAMAN CSV
    # =========================================================================
    story.append(Paragraph("3.4 Modulasi Penghematan Daya Dinamis (EA-DSRA)", h1_style))
    story.append(Paragraph(
        "Di bawah kontrol gerak, terdapat panel <b>SISTEM ADAPTIF EA-DSRA</b> (Energy-Aware Dynamic Sampling Rate Adaptation). Panel ini memodulasi laju sampling masing-masing sensor secara independen berdasarkan laju perubahan kondisi air dan kapasitas baterai:",
        body_style
    ))
    story.append(Paragraph("• <b>Penalti Wea:</b> Saat kapasitas baterai normal (>30%), faktor penalti bernilai 1.00x. Jika kapasitas baterai turun di bawah ambang batas (default: 30%), penalti Wea aktif untuk memperpanjang interval sensor secara otomatis.", bullet_style))
    story.append(Paragraph("• <b>Interval Sampling Live (T_BM):</b> Menampilkan interval waktu aktif sensor secara real-time untuk Suhu (3.0s), DO (2.0s), pH (5.0s), dan EC (4.0s).", bullet_style))
    story.append(Paragraph("• <b>Estimasi Hemat Daya:</b> Menghitung persentase energi yang berhasil dihemat (hingga 40% - 70%) dibandingkan pengukuran kontinu 1 Hz standar.", bullet_style))

    story.append(Paragraph("3.5 Kolom Kanan: Perekaman Data Misi ke Format CSV", h2_style))
    story.append(Paragraph(
        "GCS dilengkapi logger data berkecepatan tinggi yang menyimpan 36 kolom telemetri lengkap ke file CSV lokal:",
        body_style
    ))
    story.append(Paragraph("1. Masukkan direktori penyimpanan pada kotak <b>Folder</b> (default: <code>./data_logs</code>).", bullet_style))
    story.append(Paragraph("2. Masukkan nama identifikasi misi pada kotak <b>File</b> (misal: <code>record_saguling_titik1</code>).", bullet_style))
    story.append(Paragraph("3. Pilih frekuensi sampling melalui dropdown <b>Preset Interval</b> (100ms, 200ms, 500ms, 1.0s, 2.0s, atau Semua Data 10Hz).", bullet_style))
    story.append(Paragraph("4. Klik <b>START RECORD</b>. Timer digital berwarna amber akan mulai menghitung durasi perekaman.", bullet_style))
    story.append(Paragraph("5. Klik <b>STOP RECORD</b> setelah penyelaman usai. Dialog konfirmasi akan menampilkan jumlah baris dan lokasi file CSV.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # 6. BAB 4: TAB 2 — MISI OTONOM & PARAMETER TUNING
    # =========================================================================
    story.append(Paragraph("4. Tab 2 — Misi Otonom & Parameter Tuning", h1_style))
    story.append(Paragraph(
        "Tab ini digunakan untuk merencanakan misi penyelaman bertahap (profil kedalaman) dan menyetel parameter algoritma pengendali LMPC secara online tanpa mengompilasi ulang firmware mikrokontroler.",
        body_style
    ))

    img_misi = os.path.join("docs", "manual_images", "tab2_misi.png")
    if os.path.exists(img_misi):
        story.append(Image(img_misi, width=450, height=230))
        story.append(Paragraph("Gambar 3. Tab Perencanaan Misi Otonom & Penyetelan Parameter Pengendali LMPC & EA-DSRA", caption_style))

    story.append(Paragraph("Fitur Utama Tab Misi:", h2_style))
    story.append(Paragraph("• <b>Target Posisi & Hadap:</b> Mengatur setpoint kedalaman target (m) dan orientasi haluan yaw (derajat).", bullet_style))
    story.append(Paragraph("• <b>Tabel Profil Kedalaman (Depth Profiling):</b> Memprogram sekuens penyelaman bertingkat (misal: 0.5m selama 60s, lalu 1.5m selama 120s, lalu 2.5m) untuk merekam stratifikasi air waduk.", bullet_style))
    story.append(Paragraph("• <b>Online Tuning LMPC:</b> Mengubah horizon prediksi (Np), horizon kontrol (Nc), serta bobot penalti kedalaman (Qz) dan penalti pendorong (R) secara langsung.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # 7. BAB 5: TAB 3 — VISUALISASI MULTI-GRAFIK SENSOR
    # =========================================================================
    story.append(Paragraph("5. Tab 3 — Visualisasi Multi-Grafik Sensor", h1_style))
    story.append(Paragraph(
        "Tab Grafik Sensor menyediakan 4 slot grafik independen berbasis PyQtGraph untuk menganalisis tren perubahan parameter secara langsung selama penyelaman berlangsung.",
        body_style
    ))

    img_grafik = os.path.join("docs", "manual_images", "tab3_grafik.png")
    if os.path.exists(img_grafik):
        story.append(Image(img_grafik, width=450, height=230))
        story.append(Paragraph("Gambar 4. Tab Visualisasi Multi-Plot PyQtGraph dengan Pilihan Kanal Daya Ganda & Sensor Kualitas Air", caption_style))

    story.append(Paragraph("Panduan Penggunaan Grafik Multi-Slot:", h2_style))
    story.append(Paragraph("1. Di panel atas, centang kotak kanal yang ingin diamati (maksimal 4 kanal aktif sekaligus).", bullet_style))
    story.append(Paragraph("2. <b>Pilihan Kanal Lengkap:</b> pH, DO, Depth, Current Thruster, TBM Suhu, TBM DO, Raw Suhu, Raw DO, Konduktivitas, Suhu, Error Depth, Battery Thruster (6S), <b>BATT_SENSOR</b> (Baterai 2), dan <b>CURRENT_SENSOR</b> (Arus Baterai 2).", bullet_style))
    story.append(Paragraph("3. Untuk mengganti parameter pada suatu slot, hapus centang pada kanal lama, lalu centang kanal baru yang diinginkan.", bullet_style))
    story.append(Paragraph("4. Grafik otomatis menggeser sumbu horizontal (buffer 150 data poin terakhir) dan menyesuaikan rentang nilai vertikal secara dinamis.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # 8. BAB 6: TAB 4 — ANALISIS & PLAYBACK LOG CSV
    # =========================================================================
    story.append(Paragraph("6. Tab 4 — Analisis & Playback Log CSV", h1_style))
    story.append(Paragraph(
        "Tab Analisis CSV memungkinkan operator dan peneliti untuk membuka kembali file log hasil penyelaman sebelumnya tanpa harus terhubung ke wahana fisik.",
        body_style
    ))

    img_csv = os.path.join("docs", "manual_images", "tab4_csv.png")
    if os.path.exists(img_csv):
        story.append(Image(img_csv, width=450, height=230))
        story.append(Paragraph("Gambar 5. Tab Pengimpor dan Analisis Statistik File Log CSV Misi Lapangan", caption_style))

    story.append(Paragraph("Langkah Analisis File CSV:", h2_style))
    story.append(Paragraph("1. Klik tombol <b>Buka File CSV</b> dan pilih file rekaman di folder <code>data_logs/</code>.", bullet_style))
    story.append(Paragraph("2. Pilih parameter yang ingin divisualisasikan pada daftar checkbox (misal: Kedalaman vs DO).", bullet_style))
    story.append(Paragraph("3. Panel statistik di sebelah kanan akan menghitung metrik agregat secara otomatis: Nilai Rata-rata (Mean), Nilai Minimum, Nilai Maksimum, dan Standar Deviasi.", bullet_style))
    story.append(Paragraph("4. Klik <b>Export Grafik</b> untuk menyimpan kurva analitik ke format gambar PNG berkualitas tinggi untuk keperluan laporan Tugas Akhir.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # 9. BAB 7: TAB 5 — KONFIGURASI PARAMETER SISTEM
    # =========================================================================
    story.append(Paragraph("7. Tab 5 — Konfigurasi Parameter Sistem", h1_style))
    story.append(Paragraph(
        "Tab Konfigurasi Parameter digunakan untuk mengelola batasan operasional wahana yang disimpan permanen ke dalam file konfigurasi JSON (<code>gcs_config.json</code>).",
        body_style
    ))

    img_settings = os.path.join("docs", "manual_images", "tab5_settings.png")
    if os.path.exists(img_settings):
        story.append(Image(img_settings, width=450, height=230))
        story.append(Paragraph("Gambar 6. Tab Konfigurasi Parameter Sistem, Ambang Baku Mutu Air, dan Batas Proteksi Baterai", caption_style))

    story.append(Paragraph("Daftar Modul Konfigurasi:", h2_style))
    story.append(Paragraph("• <b>Baku Mutu Air (PP 22/2021 Kelas 2):</b> Menentukan rentang toleransi pH (6.0 - 9.0), DO minimum (> 4.0 mg/L), suhu deviasi (±3°C), dan konduktivitas maksimum (1000 µS/cm). Nilai di luar batas akan memicu indikator peringatan visual.", bullet_style))
    story.append(Paragraph("• <b>Batas Proteksi Baterai:</b> Menentukan tegangan proteksi maksimal 6S LiPo (25.2V), cut-off darurat minimal (19.8V), serta ambang peringatan SoC (30.0%) dan kritis (20.0%).", bullet_style))
    story.append(Paragraph("• <b>Komunikasi Jaringan:</b> Menyimpan IP target Ethernet wahana (default: <code>192.168.1.170</code>), port TCP (9000), dan opsi port USB Serial.", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # 10. BAB 8: PROSEDUR OPERASIONAL & TROUBLESHOOTING
    # =========================================================================
    story.append(Paragraph("8. Prosedur Lapangan & Troubleshooting", h1_style))
    story.append(Paragraph(
        "Untuk menjamin keselamatan wahana selam dan keberhasilan pengambilan data, ikuti prosedur standar operasi (SOP) berikut:",
        body_style
    ))

    sop_data = [
        [Paragraph("Fase Misi", table_hdr), Paragraph("Langkah Prosedur Wajib", table_hdr), Paragraph("Kriteria Sukses", table_hdr)],
        [
            Paragraph("<b>Pra-Peluncuran (Pre-Dive)</b>", table_cell_bold),
            Paragraph("1. Pasang kedua baterai fisik pada kompartemen terisolasi.<br/>2. Nyalakan sistem dan hubungkan kabel tether Ethernet.<br/>3. Buka GCS, pastikan terbaca <code>BATT [T: >24V | S: >11.5V]</code>.<br/>4. Cek sensor MS5837 pada kedalaman 0.00 m di permukaan.<br/>5. Lakukan uji gerak pendorong singkat saat wahana masih dipegang.", table_cell),
            Paragraph("Kedua baterai sehat (>90%), telemetri 10 Hz mengalir, tidak ada alarm kebocoran.", table_cell)
        ],
        [
            Paragraph("<b>Penyelaman Aktif (Active Dive)</b>", table_cell_bold),
            Paragraph("1. Tempatkan wahana di air waduk, tekan tombol <b>ARMED</b>.<br/>2. Aktifkan perekaman CSV (<b>START RECORD</b>).<br/>3. Masukkan target kedalaman (Auto Hold) atau kendalikan keyboard manual.<br/>4. Pantau kestabilan nilai DO dan status penalti EA-DSRA.", table_cell),
            Paragraph("Wahana mempertahankan kedalaman dengan deviasi < 0.2 m, log CSV merekam normal.", table_cell)
        ],
        [
            Paragraph("<b>Pasca-Penyelaman (Post-Dive)</b>", table_cell_bold),
            Paragraph("1. Tekan tombol <b>DISARMED</b> sebelum mengangkat wahana.<br/>2. Hentikan perekaman CSV (<b>STOP RECORD</b>).<br/>3. Putuskan koneksi (<b>DISCONNECT</b>).<br/>4. Keringkan wahana dan simpan data CSV untuk analisis.", table_cell),
            Paragraph("Pendorong terkunci aman, file CSV tersimpan utuh di folder <code>./data_logs</code>.", table_cell)
        ],
    ]
    t_sop = Table(sop_data, colWidths=[110, 247, 130])
    t_sop.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_sop)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Tabel Troubleshooting Lapangan Cepat:", h2_style))
    trouble_data = [
        [Paragraph("Gejala / Permasalahan", table_hdr), Paragraph("Kemungkinan Penyebab", table_hdr), Paragraph("Tindakan Solusi", table_hdr)],
        [
            Paragraph("GCS tidak bisa Connect (Connection Refused)", table_cell),
            Paragraph("IP laptop belum satu subnet dengan wahana (192.168.1.xxx) atau bridge ROS 2 belum aktif.", table_cell),
            Paragraph("Set IP statis LAN laptop ke <code>192.168.1.100</code> (Subnet 255.255.255.0). Pastikan script jembatan <code>gcs_ros2_bridge.py</code> berjalan.", table_cell)
        ],
        [
            Paragraph("Pendorong tidak berputar saat tombol keyboard ditekan", table_cell),
            Paragraph("Status wahana masih DISARMED atau kotak 'Aktifkan Kontrol Keyboard' belum dicentang.", table_cell),
            Paragraph("Pastikan tombol berubah warna merah (ARMED) dan checkbox kendali keyboard aktif.", table_cell)
        ],
        [
            Paragraph("Tegangan Baterai Sensor terbaca 0.0 V", table_cell),
            Paragraph("Kabel I2C sensor INA226 kedua longgar atau topik <code>/power/sensors</code> tidak memancarkan data.", table_cell),
            Paragraph("Periksa wiring modul INA226 R100 pada bus I2C ESP32-S3 dan cek diagnosa topik micro-ROS.", table_cell)
        ],
        [
            Paragraph("Wahana overshooting saat menuju kedalaman target", table_cell),
            Paragraph("Gain LMPC Qz terlalu agresif atau ballast wahana terlalu positif.", table_cell),
            Paragraph("Buka Tab Misi, turunkan nilai Qz dari 100 ke 60, dan tambahkan sedikit pemberat ballast.", table_cell)
        ],
    ]
    t_tr = Table(trouble_data, colWidths=[120, 160, 207])
    t_tr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, C_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_tr)

    # Bangun PDF dokumen
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUKSES] File panduan PDF berhasil dibuat: {output_pdf_path}")


if __name__ == "__main__":
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Panduan_Pengoperasian_GCS_Tyrant-AQ.pdf")
    create_manual_pdf(target)

# -*- coding: utf-8 -*-
"""
Script Generator PDF: Panduan Teknis & SOP Kalibrasi Komponen
Wahana Submersible Pemantau Kualitas Air (Tyrant-AQ)
Menggunakan ReportLab untuk menghasilkan dokumen profesional berkualitas cetak.
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas yang menghitung total halaman secara otomatis untuk header dan footer."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running Header (Halaman > 1)
        if self._pageNumber > 1:
            self.drawString(45, 802, "SOP KALIBRASI KOMPONEN SENSOR — WAHANA SUBMERSIBLE (TYRANT-AQ)")
            self.drawRightString(550, 802, "SPELL LABORATORY — TELKOM UNIVERSITY")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(45, 794, 550, 794)

        # Running Footer
        page_text = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(550, 32, page_text)
        self.drawString(45, 32, "SPELL Laboratory | Dokumen Prosedur Standar Kalibrasi Sensor Tyrant-AQ")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(45, 42, 550, 42)

        self.restoreState()


def make_callout(text, title="CATATAN TEKNIS", bg_color="#F8FAFC", border_color="#3B82F6"):
    """Fungsi helper untuk membuat kotak catatan atau peringatan yang rapi."""
    title_p = Paragraph(f"<b><font color='{border_color}'>{title}</font></b>", ParagraphStyle(
        'CalloutTitle', fontName='Helvetica-Bold', fontSize=9, leading=12
    ))
    body_p = Paragraph(text, ParagraphStyle(
        'CalloutBody', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor("#1E293B"), alignment=TA_JUSTIFY
    ))
    tbl = Table([[title_p], [body_p]], colWidths=[505])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg_color)),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor(border_color)),
        ('LINELEFT', (0, 0), (-1, -1), 3.0, colors.HexColor(border_color)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return tbl


def generate_tutorial_pdf(output_pdf_path):
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=45,
        rightMargin=45,
        topMargin=48,
        bottomMargin=48
    )

    story = []

    # ==================== PALET WARNA ====================
    PRIMARY = colors.HexColor("#1E3A8A")     # Navy Blue
    SECONDARY = colors.HexColor("#0284C7")   # Sky Blue
    DARK_TEXT = colors.HexColor("#0F172A")   # Slate 900
    BODY_TEXT = colors.HexColor("#334155")   # Slate 700
    BG_HEAD = colors.HexColor("#F1F5F9")     # Light Slate Header
    BORDER_CLR = colors.HexColor("#94A3B8")  # Slate 400

    # ==================== GAYA TIPOGRAFI ====================
    styles = getSampleStyleSheet()

    doc_title = ParagraphStyle(
        'DocTitle', fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=PRIMARY, alignment=TA_LEFT, spaceAfter=4
    )
    doc_subtitle = ParagraphStyle(
        'DocSubtitle', fontName='Helvetica', fontSize=10, leading=14, textColor=SECONDARY, alignment=TA_LEFT, spaceAfter=8
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=PRIMARY,
        spaceBefore=14, spaceAfter=6, keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom', fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=SECONDARY,
        spaceBefore=10, spaceAfter=4, keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom', fontName='Helvetica', fontSize=8.5, leading=12.5, textColor=BODY_TEXT,
        alignment=TA_JUSTIFY, spaceAfter=5
    )
    body_bold = ParagraphStyle(
        'Body_Bold', fontName='Helvetica-Bold', fontSize=8.5, leading=12.5, textColor=DARK_TEXT, spaceAfter=5
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom', fontName='Helvetica', fontSize=8.5, leading=12, textColor=BODY_TEXT,
        leftIndent=14, spaceAfter=3, alignment=TA_JUSTIFY
    )
    table_cell = ParagraphStyle(
        'TableCell', fontName='Helvetica', fontSize=8, leading=10.5, textColor=DARK_TEXT
    )
    table_cell_center = ParagraphStyle(
        'TableCellCenter', fontName='Helvetica', fontSize=8, leading=10.5, textColor=DARK_TEXT, alignment=TA_CENTER
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold', fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=DARK_TEXT
    )
    table_head = ParagraphStyle(
        'TableHead', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.white, alignment=TA_CENTER
    )

    # ==================== DOKUMEN HEADER ====================
    story.append(Paragraph("STANDAR OPERASIONAL PROSEDUR (SOP) KALIBRASI SENSOR", doc_title))
    story.append(Paragraph("Wahana Submersible Otonom Tyrant-AQ — Sensor Kualitas Air & Navigasi Inersia", doc_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceBefore=2, spaceAfter=10))

    # Meta Table
    meta_data = [
        [
            Paragraph("<b>Target Sistem:</b> Tyrant-AQ AUV (Twin-Hull 6 Thruster)", table_cell),
            Paragraph("<b>Laboratorium:</b> SPELL Laboratory", table_cell),
            Paragraph("<b>Tanggal Rilis:</b> September 2026", table_cell)
        ],
        [
            Paragraph("<b>Antarmuka Kalibrasi:</b> Submersible Calibration Suite", table_cell),
            Paragraph("<b>Protokol Komunikasi:</b> Ethernet TCP (Port 9001)", table_cell),
            Paragraph("<b>Mikrokontroler:</b> Teensy 4.1 ARM Cortex-M7", table_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[185, 175, 145])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 1. PENDAHULUAN & PERSIAPAN ALAT
    # =========================================================================
    story.append(Paragraph("1. PENDAHULUAN & ALAT BAHAN YANG DIBUTUHKAN", h1_style))
    story.append(Paragraph(
        "Kalibrasi merupakan proses penyesuaian kurva transfer sensor terhadap standar acuan fisik atau kimia yang telah diketahui nilainya. "
        "Pada wahana submersible <i>Tyrant-AQ</i>, kalibrasi dibagi menjadi dua pilar utama: <b>Pilar Kualitas Air</b> (pH, EC, DO, Suhu) untuk akurasi data limnologi, "
        "serta <b>Pilar Navigasi & Gerak</b> (IMU Gyroscope, Accelerometer Leveling, Magnetometer, Depth) untuk kestabilan kendali LMPC dan estimasi state EKF.",
        body_style
    ))

    # Tabel Alat & Bahan
    tools_data = [
        [Paragraph("No", table_head), Paragraph("Nama Alat / Bahan", table_head), Paragraph("Fungsi & Peruntukan", table_head), Paragraph("Spesifikasi Acuan", table_head)],
        [Paragraph("1", table_cell_center), Paragraph("Larutan Buffer pH Standar", table_cell_bold), Paragraph("Kalibrasi 3-titik elektroda pH (Mid, Low, High)", table_cell), Paragraph("pH 7.00, pH 4.00, pH 10.00 (NIST Traceable)", table_cell)],
        [Paragraph("2", table_cell_center), Paragraph("Larutan Standar Konduktivitas", table_cell_bold), Paragraph("Kalibrasi cell constant konstanta K probe EC", table_cell), Paragraph("1413 µS/cm (Air Tawar), 12880 µS/cm (Air Payau)", table_cell)],
        [Paragraph("3", table_cell_center), Paragraph("Sodium Sulfit (Na2SO3 5%)", table_cell_bold), Paragraph("Kalibrasi titik nol (0 mg/L) Dissolved Oxygen", table_cell), Paragraph("Larutan Na2SO3 teknis terlarut akuades", table_cell)],
        [Paragraph("4", table_cell_center), Paragraph("Air Akuades Demineralisasi", table_cell_bold), Paragraph("Pembilasan elektroda antar larutan buffer", table_cell), Paragraph("Air deionisasi (TDS < 2 ppm, EC < 5 µS/cm)", table_cell)],
        [Paragraph("5", table_cell_center), Paragraph("Tisu Mikrofiber Bebas Serat", table_cell_bold), Paragraph("Menyerap sisa cairan probe tanpa menggores kaca", table_cell), Paragraph("Kimwipes / Tisu lensa bebas partikel debu", table_cell)],
        [Paragraph("6", table_cell_center), Paragraph("Dudukan Uji Datar (Leveling Rig)", table_cell_bold), Paragraph("Tatakan diam bebas getaran untuk kalibrasi inersia", table_cell), Paragraph("Waterpass presisi, bebas logam feromagnetik", table_cell)],
        [Paragraph("7", table_cell_center), Paragraph("Kabel Tether Ethernet & Laptop", table_cell_bold), Paragraph("Jalur komunikasi TCP/IP ke GUI Kalibrasi", table_cell), Paragraph("Kabel UTP Cat5e/Cat6, IP Static 192.168.1.xxx", table_cell)],
    ]
    tools_table = Table(tools_data, colWidths=[22, 145, 175, 163])
    tools_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(tools_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 2. TUTORIAL KALIBRASI SENSOR KUALITAS AIR
    # =========================================================================
    story.append(Paragraph("2. TUTORIAL KALIBRASI SENSOR KUALITAS AIR", h1_style))
    story.append(Paragraph(
        "Sensor elektrokimia air bekerja dengan mendeteksi beda potensial atau konduktivitas ionik cairan. "
        "Sebelum pengujian lapangan di Waduk Saguling, seluruh probe wajib melalui prosedur kalibrasi berikut secara berurutan.",
        body_style
    ))

    # 2.1 Sensor pH
    story.append(Paragraph("2.1 Sensor pH (Atlas Scientific EZO pH)", h2_style))
    story.append(Paragraph(
        "Sensor pH mengubah potensial milivolt (mV) dari membran kaca menjadi nilai pH berdasar Persamaan Nernst: "
        "<i>E = E0 - (2.303·R·T / F)·pH</i>. Kalibrasi dilakukan dengan metode <b>3-Titik</b>.",
        body_style
    ))
    story.append(Paragraph("<b>Langkah Kerja Kalibrasi pH:</b>", body_bold))
    story.append(Paragraph("1. <b>Bilas Elektroda:</b> Bilas probe pH menggunakan air akuades, kemudian keringkan perlahan dengan menempelkan tisu mikrofiber (jangan digosok agar tidak menimbulkan muatan elektrostatik).", bullet_style))
    story.append(Paragraph("2. <b>Kalibrasi Titik Tengah (Mid-Point pH 7.00):</b> Celupkan probe ke larutan buffer pH 7.00. Pastikan bohlam kaca dan sambungan referensi terendam minimal 3 cm. Amati pembacaan pada GUI hingga nilai stabil selama minimal 60 detik. Klik tombol <b>[Cal Mid (pH 7.00)]</b>. Tunggu hingga terminal log menampilkan respon <code>CAL_RESP,PH,*OK</code>.", bullet_style))
    story.append(Paragraph("3. <b>Kalibrasi Titik Rendah (Low-Point pH 4.00):</b> Angkat probe, bilas kembali dengan akuades hingga bersih. Masukkan probe ke larutan buffer pH 4.00. Tunggu pembacaan stabil selama 60 detik. Klik tombol <b>[Cal Low (pH 4.00)]</b>. Respon <code>CAL_RESP,PH,*OK</code> menandakan kemiringan kurva asam (acid slope) telah tersimpan.", bullet_style))
    story.append(Paragraph("4. <b>Kalibrasi Titik Tinggi (High-Point pH 10.00):</b> Bilas probe kembali. Celupkan ke larutan buffer pH 10.00. Tunggu nilai stabil. Klik tombol <b>[Cal High (pH 10.00)]</b> untuk mengunci kemiringan basa (base slope).", bullet_style))
    story.append(Paragraph("5. <b>Verifikasi Status:</b> Klik tombol <b>[Check Status]</b>. Mikrokontroler akan merespon status kalibrasi (misal <code>?CAL,3</code> yang berarti kalibrasi 3-titik telah aktif dan tersimpan).", bullet_style))

    story.append(make_callout(
        "<b>PENTING:</b> Urutan kalibrasi pH <b>WAJIB dimulai dari pH 7.00 terlebih dahulu</b> untuk menentukan tegangan offset nol. "
        "Jika pH 7.00 belum dikalibrasikan, kalibrasi pH 4.00 dan pH 10.00 tidak akan valid pada modul EZO. "
        "Sensor suhu DS18B20 harus aktif karena perubahan suhu air mempengaruhi kemiringan Nernst.",
        title="PERINGATAN KALIBRASI pH", bg_color="#FEF2F2", border_color="#EF4444"
    ))
    story.append(Spacer(1, 8))

    # 2.2 Sensor Konduktivitas Listrik (EC)
    story.append(Paragraph("2.2 Sensor Konduktivitas Listrik / EC (Atlas Scientific EZO EC)", h2_style))
    story.append(Paragraph(
        "Sensor konduktivitas listrik mengukur kemampuan air menghantarkan arus listrik (µS/cm). Kalibrasi menentukan konstanta sel elektroda (K).",
        body_style
    ))
    story.append(Paragraph("<b>Langkah Kerja Kalibrasi EC:</b>", body_bold))
    story.append(Paragraph("1. <b>Kalibrasi Udara Kering (Dry Calibration):</b> Bersihkan probe dengan akuades dan keringkan total di udara terbuka. Pastikan tidak ada sisa tetesan air di antara elektroda platinum. Klik tombol <b>[Cal Dry (Wajib Pertama)]</b>. Perintah ini menghapus kapasitansi parasitik rangkaian.", bullet_style))
    story.append(Paragraph("2. <b>Kalibrasi Larutan Standar (1-Point Calibration):</b> Masukkan probe ke dalam larutan standar konduktivitas <b>1413 µS/cm</b> (standar air tawar). Goyangkan probe perlahan untuk melepas gelembung udara yang menempel pada celah elektroda. Masukkan angka <code>1413</code> pada kotak teks, lalu klik tombol <b>[Cal One Point]</b>.", bullet_style))
    story.append(Paragraph("3. <b>Kalibrasi Rentang Lebar (Opsional 2-Point):</b> Jika wahana digunakan di air payau/muara, gunakan larutan Low (<code>12880 µS/cm</code>) dan High (<code>80000 µS/cm</code>) dengan tombol <b>[Cal Low]</b> dan <b>[Cal High]</b>.", bullet_style))
    story.append(Paragraph("4. <b>Konfirmasi:</b> Klik <b>[Check Status]</b>. Respon sukses akan menampilkan status kalibrasi aktif (misal <code>?CAL,2</code> untuk Dry + Single Point).", bullet_style))

    story.append(make_callout(
        "Gelembung udara mikroskopis yang terjebak pada elektroda platinum merupakan sumber galat terbesar pembacaan EC (menghasilkan nilai 30-50% lebih rendah). "
        "Selalu ketuk perlahan badan probe di dalam larutan untuk membebaskan gelembung sebelum menekan tombol kalibrasi.",
        title="TIPS OPERASIONAL EC", bg_color="#FFFBEB", border_color="#F59E0B"
    ))
    story.append(Spacer(1, 8))

    # 2.3 Sensor Dissolved Oxygen (DO)
    story.append(Paragraph("2.3 Sensor Dissolved Oxygen / DO (DFRobot Analog SEN0237)", h2_style))
    story.append(Paragraph(
        "Sensor oksigen terlarut tipe galvanik menghasilkan arus sebanding dengan tekanan parsial molekul oksigen yang menembus membran teflon. "
        "Sinyal tegangan analog dikonversi menggunakan tabel saturasi kelarutan air jenuh terhadap suhu.",
        body_style
    ))
    story.append(Paragraph("<b>Langkah Kerja Kalibrasi DO:</b>", body_bold))
    story.append(Paragraph("1. <b>Kalibrasi 100% Saturasi (Air Calibration):</b> Siapkan botol kalibrasi yang berisi spons lembap dengan sedikit air (jangan sampai elektroda menyentuh air, hanya udara jenuh kelembaban 100%). Biarkan probe beradaptasi selama 3-5 menit hingga pembacaan tegangan ADC stabil. Klik tombol <b>[Cal 100% Saturation]</b>. Mikrokontroler akan mencatat nilai tegangan ini sebagai <code>DO_CAL_V</code> pada suhu saat itu.", bullet_style))
    story.append(Paragraph("2. <b>Kalibrasi Titik Nol (Zero DO Calibration):</b> Larutkan serbuk Sodium Sulfit (Na2SO3) ke dalam air akuades hingga konsentrasi 5%. Celupkan probe ke larutan tersebut. Oksigen terlarut akan bereaksi habis membentuk Na2SO4 sehingga DO terukur 0.0 mg/L. Setelah tegangan turun dan stabil di dekat nol (< 50 mV), klik tombol <b>[Cal Zero DO]</b>.", bullet_style))
    story.append(Paragraph("3. <b>Bilas Tuntas:</b> Bilas probe dengan akuades berulang kali untuk menghilangkan sisa larutan sulfit sebelum probe dimasukkan ke air waduk.", bullet_style))

    story.append(Spacer(1, 10))

    # =========================================================================
    # 3. TUTORIAL KALIBRASI SENSOR ORIENTASI GERAK & KEDALAMAN (IMU & DEPTH)
    # =========================================================================
    story.append(Paragraph("3. TUTORIAL KALIBRASI SENSOR ORIENTASI GERAK & KEDALAMAN", h1_style))
    story.append(Paragraph(
        "Keberhasilan algoritma kendali posisi dan kedalaman (Decoupled LMPC) serta pengamat gangguan (EKF) "
        "sangat bergantung pada integritas data orientasi 6-DOF wahana. Prosedur kalibrasi berikut wajib dilakukan di darat sebelum peluncuran.",
        body_style
    ))

    # 3.1 Gyroscope Zero-Rate Bias
    story.append(Paragraph("3.1 Kalibrasi Zero-Rate Bias Gyroscope (IMU)", h2_style))
    story.append(Paragraph(
        "Sensor gyroscope MEMS secara alami memiliki bias nol (kecepatan sudut terbaca tidak nol saat wahana diam). "
        "Jika bias tidak dikompensasi, integrasi sudut Roll, Pitch, dan Yaw akan mengalami drift kumulatif yang signifikan.",
        body_style
    ))
    story.append(Paragraph("<b>Langkah Kerja Kalibrasi Gyro:</b>", body_bold))
    story.append(Paragraph("1. Letakkan wahana <i>Tyrant-AQ</i> pada dudukan uji datar yang kokoh.", bullet_style))
    story.append(Paragraph("2. Pastikan wahana <b>diam sempurna tanpa getaran</b> (matikan seluruh thruster dan hindari menyentuh wahana).", bullet_style))
    story.append(Paragraph("3. Klik tombol <b>[Calibrate Gyro Bias (Wahana Diam)]</b>.", bullet_style))
    story.append(Paragraph("4. GUI akan memerintahkan Teensy mengambil 100–500 sampel kecepatan sudut (deg/s) pada sumbu X, Y, dan Z. Nilai rata-rata bias akan dihitung dan disimpan otomatis ke memori non-volatile EEPROM.", bullet_style))

    # 3.2 Horizon Leveling Tare
    story.append(Paragraph("3.2 Horizon Leveling Tare (Roll & Pitch = 0.0°)", h2_style))
    story.append(Paragraph(
        "Penentuan titik netral horizon wahana bertujuan memastikan bahwa saat wahana berada pada kondisi trim datar, "
        "pembacaan sudut Roll dan Pitch tepat 0.00°. Ini mencegah LMPC memicu thruster koreksi saat robot sebenarnya sudah seimbang.",
        body_style
    ))
    story.append(Paragraph("<b>Langkah Kerja Leveling Tare:</b>", body_bold))
    story.append(Paragraph("1. Atur posisi wahana di dudukan uji dengan bantuan alat waterpass presisi di bagian lambung atas.", bullet_style))
    story.append(Paragraph("2. Setelah wahana rata air, klik tombol <b>[Tare Horizon (Roll & Pitch = 0°)]</b>.", bullet_style))
    story.append(Paragraph("3. Label Roll dan Pitch pada baris Real-Time Sensor Data akan langsung menunjukkan nilai <code>0.0°</code>.", bullet_style))

    # 3.3 Magnetometer Hard-Iron & Soft-Iron
    story.append(Paragraph("3.3 Kalibrasi Magnetometer / Kompas Digital (Hard & Soft Iron)", h2_style))
    story.append(Paragraph(
        "Motor thruster, kabel baterai berarus tinggi, dan baut stainless steel pada lambung wahana menimbulkan medan magnet statis "
        "(<i>Hard-Iron Distortion</i>) serta membelokkan garis gaya magnet bumi (<i>Soft-Iron Distortion</i>). "
        "Hal ini menyebabkan pembacaan arah haluan (Heading/Yaw) melenceng jika wahana berputar.",
        body_style
    ))
    story.append(Paragraph("<b>Langkah Kerja Kalibrasi Magnetometer:</b>", body_bold))
    story.append(Paragraph("1. Angkat wahana di area terbuka yang bebas dari struktur beton bertulang masif atau kabel listrik tegangan tinggi.", bullet_style))
    story.append(Paragraph("2. Klik tombol <b>[Mulai Putar 360°]</b> pada kolom Orientasi & Gerak Wahana.", bullet_style))
    story.append(Paragraph("3. Putar wahana secara perlahan mengelilingi sumbu Yaw sebesar 360 derajat penuh, lalu lakukan gerakan rotasi meliuk membentuk angka 8 (*figure-8 motion*) selama 30–60 detik.", bullet_style))
    story.append(Paragraph("4. Setelah putaran selesai, klik tombol <b>[Simpan EEPROM]</b>. Mikrokontroler akan menghitung matriks transformasi elipsoid menjadi bola sferis sempurna dan menyimpan offset hard-iron ke EEPROM.", bullet_style))

    # 3.4 Sensor Kedalaman
    story.append(Paragraph("3.4 Sensor Kedalaman Tekanan (MS5837 / Bar30)", h2_style))
    story.append(Paragraph(
        "Sensor tekanan bawah air membaca tekanan absolut (tekanan atmosfer permukaan + tekanan hidrostatis kolom air). "
        "Kedalaman $Z$ dihitung dengan rumus: <i>Z = (P_sensor - P_permukaan) / (rho * g)</i>.",
        body_style
    ))
    story.append(Paragraph("<b>Langkah Kerja Kalibrasi Kedalaman:</b>", body_bold))
    story.append(Paragraph("1. Masukkan nilai densitas air waduk pada kotak teks densitas: <code>997.0</code> kg/m³ (nilai standar air tawar Waduk Saguling, suhu ~27°C). Klik tombol <b>[Set]</b>.", bullet_style))
    story.append(Paragraph("2. Saat wahana diletakkan mengapung di permukaan air waduk (sebelum perintah selam diberikan), klik tombol <b>[Tare Kedalaman Permukaan (Z = 0.0 m)]</b>.", bullet_style))
    story.append(Paragraph("3. Tekanan atmosfer lokal saat itu dikunci sebagai $P_{\\text{permukaan}}$, sehingga kedalaman $Z$ langsung terbaca <code>0.00 m</code>.", bullet_style))

    story.append(Spacer(1, 10))

    # =========================================================================
    # 4. PANDUAN PENGOPERASIAN GUI KALIBRASI
    # =========================================================================
    story.append(Paragraph("4. PANDUAN OPERASIONAL APLIKASI GUI KALIBRASI", h1_style))
    story.append(Paragraph(
        "Aplikasi <i>Submersible Calibration Suite</i> dirancang ringkas dengan tata letak satu halaman utuh "
        "yang memadukan kontrol koneksi, pembacaan real-time, panel kalibrasi 3 kolom, terminal log, dan perekam data CSV.",
        body_style
    ))

    gui_steps = [
        [Paragraph("Langkah", table_head), Paragraph("Tindakan Operator", table_head), Paragraph("Indikasi Keberhasilan pada GUI", table_head)],
        [Paragraph("1", table_cell_center), Paragraph("Jalankan berkas <code>run_gui_kalibrasi.bat</code>", table_cell), Paragraph("Jendela aplikasi terbuka dengan tema Catppuccin Dark.", table_cell)],
        [Paragraph("2", table_cell_center), Paragraph("Pilih Mode: <b>Real Hardware</b> atau <b>Simulasi</b>. Masukkan IP <code>192.168.1.177</code> dan Port <code>9001</code>. Klik <b>[Connect]</b>.", table_cell), Paragraph("Label status berubah hijau <b>● Connected</b>. Nilai pada baris Real-Time mulai terisi data hidup.", table_cell)],
        [Paragraph("3", table_cell_center), Paragraph("Pantau nilai sensor dan kestabilannya sebelum menekan tombol kalibrasi.", table_cell), Paragraph("Nilai pH, EC, DO, Temp, Roll, Pitch, Yaw, dan Kedalaman berkedip halus sesuai sampling rate.", table_cell)],
        [Paragraph("4", table_cell_center), Paragraph("Lakukan kalibrasi sesuai panduan Bab 2 dan Bab 3.", table_cell), Paragraph("Terminal log menampilkan paket <code>TX -> ...</code> diikuti respon konfirmasi <code>RX <- CAL_RESP,...</code>.", table_cell)],
        [Paragraph("5", table_cell_center), Paragraph("Atur <b>Interval Rekam</b> (misal <code>1.0 s</code>), klik <b>[● Record]</b> untuk menyimpan data pengujian.", table_cell), Paragraph("Tombol berubah menjadi merah <b>■ Stop</b> dan label menampilkan durasi serta jumlah sampel CSV.", table_cell)],
        [Paragraph("6", table_cell_center), Paragraph("Gunakan pintasan <code>Ctrl + Scroll Roda Mouse</code> untuk memperbesar teks jika diperlukan.", table_cell), Paragraph("Seluruh elemen teks dan tombol membesar/mengecil secara responsif.", table_cell)],
    ]
    gui_table = Table(gui_steps, colWidths=[38, 225, 242])
    gui_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(gui_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 5. PANDUAN PERAWATAN & TROUBLESHOOTING
    # =========================================================================
    story.append(Paragraph("5. PANDUAN PERAWATAN SENSOR & PEMECAHAN MASALAH", h1_style))
    story.append(Paragraph(
        "Kinerja sensor kimia dan inersia sangat dipengaruhi oleh cara penyimpanan dan pemeliharaan fisik. "
        "Ikuti pedoman pemeliharaan berikut guna mencegah kerusakan permanen instrumen:",
        body_style
    ))

    story.append(Paragraph("<b>Aturan Emas Pemeliharaan Sensor:</b>", body_bold))
    story.append(Paragraph("• <b>Penyimpanan Elektroda pH:</b> Bohlam kaca sensor pH <b>JANGAN PERNAH DIBIARKAN KERING</b> atau direndam dalam air murni/akuades dalam waktu lama (ion referensi akan tersedot keluar). Selalu simpan probe di dalam botol pelindung berisi <b>Larutan KCl 3.0 Molar</b>.", bullet_style))
    story.append(Paragraph("• <b>Perawatan Membran DO:</b> Periksa secara berkala cairan elektrolit internal sensor DO. Jika terdapat gelembung udara besar di dalam tudung membran atau membran berkerut/sobek, ganti tudung membran dan isi ulang cairan elektrolit KOH/NaOH khusus.", bullet_style))
    story.append(Paragraph("• <b>Pembersihan Elektroda EC:</b> Jika elektroda platinum EC terkena minyak atau lumut waduk, bersihkan perlahan menggunakan alkohol isopropil 70% dan sikat berbulu halus, kemudian bilas dengan air akuades.", bullet_style))
    story.append(Paragraph("• <b>Proteksi Magnetik IMU:</b> Jaga jarak fisik minimal 8–10 cm antara modul IMU dengan motor DC thruster dan kabel baterai utama untuk meminimalkan induksi elektromagnetik liar.", bullet_style))
    story.append(Spacer(1, 6))

    # Tabel Troubleshooting
    trouble_data = [
        [Paragraph("Gejala Masalah", table_head), Paragraph("Kemungkinan Penyebab", table_head), Paragraph("Solusi Tindakan Korektif", table_head)],
        [Paragraph("Nilai pH lambat stabil / melompat liar", table_cell_bold), Paragraph("Bohlam kaca kotor, ada gelembung di sambungan referensi, atau kabel terinduksi.", table_cell), Paragraph("Rendam probe di larutan KCl hangat selama 30 menit. Pastikan konektor BNC terpasang rapat dan terlindung dari cipratan air.", table_cell)],
        [Paragraph("Nilai EC terbaca 0 atau jauh di bawah standar", table_cell_bold), Paragraph("Gelembung udara terjebak di celah probe, atau belum dilakukan kalibrasi kering.", table_cell), Paragraph("Keringkan probe total lalu lakukan <b>Cal Dry</b>. Celupkan ke larutan dan ketuk badan probe perlahan untuk membuang gelembung udara.", table_cell)],
        [Paragraph("Nilai DO tidak merespon di larutan sulfit", table_cell_bold), Paragraph("Cairan elektrolit membran habis atau membran teroksidasi/tersumbat endapan lumut.", table_cell), Paragraph("Buka tudung membran, bilas katoda dengan air deionisasi, isi cairan elektrolit baru, pasang tudung baru tanpa ada gelembung.", table_cell)],
        [Paragraph("Heading (Yaw) berputar sendiri saat diam", table_cell_bold), Paragraph("Distorsi hard-iron belum terkompensasi atau ada obyek besi di dekat dudukan uji.", table_cell), Paragraph("Jauhkan obyek logam dari sekitar wahana, ulangi kalibrasi 360° dan figure-8 hingga matriks koreksi tersimpan ke EEPROM.", table_cell)],
        [Paragraph("GUI menampilkan status Disconnected", table_cell_bold), Paragraph("IP laptop tidak satu subnet (192.168.1.xxx) atau kabel Ethernet longgar.", table_cell), Paragraph("Atur static IP adapter laptop ke <code>192.168.1.100</code> subnet <code>255.255.255.0</code>. Uji ping ke <code>192.168.1.177</code> di Command Prompt.", table_cell)],
    ]
    trouble_table = Table(trouble_data, colWidths=[135, 170, 200])
    trouble_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(trouble_table)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 6. RINGKASAN PERINTAH PROTOKOL TEKNIS
    # =========================================================================
    story.append(Paragraph("6. RINGKASAN PROTOKOL PERINTAH SERIAL / ETHERNET", h1_style))
    story.append(Paragraph(
        "Berikut adalah referensi cepat format string ASCII perintah (TX) dari GUI ke Teensy 4.1 "
        "beserta format balasan respon (RX) yang ditampilkan pada Communication Log:",
        body_style
    ))

    protocol_data = [
        [Paragraph("Parameter Sensor", table_head), Paragraph("Format Perintah (TX)", table_head), Paragraph("Format Respon Sukses (RX)", table_head), Paragraph("Aksi Mikrokontroler", table_head)],
        [Paragraph("pH Mid-Point", table_cell_bold), Paragraph("<code>CAL_PH,mid,7.00</code>", table_cell), Paragraph("<code>CAL_RESP,PH,*OK,...</code>", table_cell), Paragraph("Kunci tegangan offset netral (E0)", table_cell)],
        [Paragraph("pH Low-Point", table_cell_bold), Paragraph("<code>CAL_PH,low,4.00</code>", table_cell), Paragraph("<code>CAL_RESP,PH,*OK,...</code>", table_cell), Paragraph("Kalkulasi slope asam (acid slope)", table_cell)],
        [Paragraph("pH High-Point", table_cell_bold), Paragraph("<code>CAL_PH,high,10.00</code>", table_cell), Paragraph("<code>CAL_RESP,PH,*OK,...</code>", table_cell), Paragraph("Kalkulasi slope basa (base slope)", table_cell)],
        [Paragraph("pH Reset Pabrik", table_cell_bold), Paragraph("<code>CAL_PH,clear</code>", table_cell), Paragraph("<code>CAL_RESP,PH,*OK</code>", table_cell), Paragraph("Hapus offset kalibrasi di modul EZO", table_cell)],
        [Paragraph("EC Udara Kering", table_cell_bold), Paragraph("<code>CAL_EC,dry</code>", table_cell), Paragraph("<code>CAL_RESP,EC,*OK</code>", table_cell), Paragraph("Kompensasi kapasitansi parasitik", table_cell)],
        [Paragraph("EC 1-Point", table_cell_bold), Paragraph("<code>CAL_EC,one,1413</code>", table_cell), Paragraph("<code>CAL_RESP,EC,*OK</code>", table_cell), Paragraph("Hitung konstanta sel K elektroda", table_cell)],
        [Paragraph("DO 100% Udara", table_cell_bold), Paragraph("<code>CAL_DO,sat,100</code>", table_cell), Paragraph("<code>CAL_RESP,DO,*OK,...</code>", table_cell), Paragraph("Rekam tegangan jenuh DO_CAL_V", table_cell)],
        [Paragraph("DO 0% Zero Sulfit", table_cell_bold), Paragraph("<code>CAL_DO,zero</code>", table_cell), Paragraph("<code>CAL_RESP,DO,*OK,...</code>", table_cell), Paragraph("Kunci tegangan offset nol cairan", table_cell)],
        [Paragraph("Gyro Zero-Bias", table_cell_bold), Paragraph("<code>CAL_IMU,gyro</code>", table_cell), Paragraph("<code>CAL_RESP,IMU,*OK,...</code>", table_cell), Paragraph("Rata-rata 1000 sampel bias diam", table_cell)],
        [Paragraph("Horizon Leveling", table_cell_bold), Paragraph("<code>CAL_IMU,level</code>", table_cell), Paragraph("<code>CAL_RESP,IMU,*OK,...</code>", table_cell), Paragraph("Set Roll & Pitch = 0.00° trim", table_cell)],
        [Paragraph("Magnetometer", table_cell_bold), Paragraph("<code>CAL_MAG,start / save</code>", table_cell), Paragraph("<code>CAL_RESP,MAG,*OK,...</code>", table_cell), Paragraph("Streaming titik & fit matriks 3D", table_cell)],
        [Paragraph("Depth Tare", table_cell_bold), Paragraph("<code>CAL_DEPTH,tare</code>", table_cell), Paragraph("<code>CAL_RESP,DEPTH,*OK,...</code>", table_cell), Paragraph("Kunci P_atmosfer di permukaan air", table_cell)],
        [Paragraph("Densitas Fluida", table_cell_bold), Paragraph("<code>CAL_DEPTH,density,997.0</code>", table_cell), Paragraph("<code>CAL_RESP,DEPTH,*OK,...</code>", table_cell), Paragraph("Update konstanta massa jenis air", table_cell)],
    ]
    protocol_table = Table(protocol_data, colWidths=[80, 130, 140, 155])
    protocol_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(protocol_table)
    story.append(Spacer(1, 14))

    # Sign-off box
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_CLR, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "<b>DOKUMEN TEKNIS TERSTANDARISASI</b><br/>"
        "SPELL Laboratory | Program Studi S1 Teknik Elektro, Fakultas Teknik Elektro, Telkom University.<br/>"
        "Dokumen ini diperuntukkan sebagai acuan baku prosedur kalibrasi wahana submersible <i>Tyrant-AQ</i>.",
        ParagraphStyle('FooterNotice', fontName='Helvetica', fontSize=8, leading=11, textColor=BODY_TEXT, alignment=TA_CENTER)
    ))

    # Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Berkas PDF Tutorial Kalibrasi berhasil dibuat: {output_pdf_path}")


if __name__ == "__main__":
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PANDUAN_KALIBRASI_KOMPONEN.pdf")
    generate_tutorial_pdf(output_path)

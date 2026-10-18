# -*- coding: utf-8 -*-
"""
Generate Professional PDF Implementation Plan & Feature Roadmap
for Tyrant-AQ AUV Ground Control Station.
Styled in pure black typography with justified text alignment.
"""
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas for adding page numbers and running header/footer in black font."""
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
        self.setFillColor(colors.black)

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 800, "Tyrant-AQ AUV | Ground Control Station (GCS) — Dokumen Rencana Implementasi")
            self.setStrokeColor(colors.black)
            self.setLineWidth(0.5)
            self.line(54, 792, 558, 792)

        # Running Footer
        page_text = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, "S1 Teknik Elektro - Telkom University | Kerahasiaan: Internal Penelitian Tugas Akhir")
        self.setStrokeColor(colors.black)
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)

        self.restoreState()


def create_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    # Pure Black Color System
    BLACK = colors.HexColor("#000000")
    BG_HEADER = colors.HexColor("#EAEAEA")
    BG_LIGHT = colors.HexColor("#F8F8F8")
    BORDER_CLR = colors.HexColor("#444444")

    # Typography Styles with Black Font & Justified Alignment
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=BLACK,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    h1_style = ParagraphStyle(
        'Header1',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyJustify',
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=BLACK,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    body_bold = ParagraphStyle(
        'BodyBoldJustify',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13.5,
        textColor=BLACK,
        alignment=TA_JUSTIFY
    )
    table_cell = ParagraphStyle(
        'TableCellJustify',
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=BLACK,
        alignment=TA_JUSTIFY
    )
    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=BLACK,
        alignment=TA_CENTER
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11.5,
        textColor=BLACK,
        alignment=TA_LEFT
    )
    table_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=BLACK,
        alignment=TA_CENTER
    )

    story = []

    # ============================================================
    # COVER / HEADER BLOCK
    # ============================================================
    story.append(Paragraph("DOKUMEN RENCANA IMPLEMENTASI & ROADMAP GCS", title_style))
    story.append(Paragraph("<b>Wahana Submersible Otonom Pemantau Kualitas Air Waduk Saguling (Tyrant-AQ)</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLACK, spaceBefore=0, spaceAfter=8))

    # Authors & Metadata Box
    meta_data = [
        [
            Paragraph("<b>Pengembang GCS:</b>", table_cell_bold),
            Paragraph("1. Bryan Gabriel Izaac Sasabone (NIM: 101022300195)<br/>2. Charisto Brilliant R.P (NIM: 101022330187)", table_cell),
            Paragraph("<b>Institusi:</b>", table_cell_bold),
            Paragraph("S1 Teknik Elektro, Fakultas Teknik Elektro<br/>Telkom University", table_cell)
        ],
        [
            Paragraph("<b>Fokus Riset:</b>", table_cell_bold),
            Paragraph("Decoupled LMPC + EKF & Adaptif EA-DSRA pada Arsitektur Twin-Hull 6 Thruster", table_cell),
            Paragraph("<b>Versi Dokumen:</b>", table_cell_bold),
            Paragraph("v2.0 (Format Standar Hitam & Justified)", table_cell)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[80, 170, 70, 184])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.75, BORDER_CLR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    # ============================================================
    # 1. RINGKASAN ARSITEKTUR GCS
    # ============================================================
    story.append(Paragraph("1. Ringkasan Eksekutif & Struktur 3 Tab Utama", h1_style))
    story.append(Paragraph(
        "Aplikasi <b>Ground Control Station (GCS) Tyrant-AQ</b> dirancang dengan arsitektur komprehensif berbasis Python PyQt5 dan akselerasi PyQtGraph pada frame rate 60 FPS bebas lag. GCS ini memfasilitasi pengoperasian penuh wahana submersible dalam memantau parameter kualitas air Waduk Saguling secara real-time. Fungsionalitas sistem mencakup kontrol manual Deadman Switch keyboard W/S, pemantauan kestabilan kedalaman berbasis Decoupled LMPC, visualisasi orientasi 3D navigasi, streaming live camera feed bawah air, perekaman data CSV/MCAP dengan live timer, serta modul ekspor bridge ke Foxglove Studio.",
        body_style
    ))

    # Tab Overview Table
    tab_data = [
        [Paragraph("Tab Antarmuka", table_header), Paragraph("Fokus & Fungsionalitas Utama", table_header), Paragraph("Komponen Kunci", table_header)],
        [
            Paragraph("<b>Tab 1: Kontrol & Rekam</b>", table_cell_bold),
            Paragraph("Dashboard terpadu untuk pengoperasian wahana, monitoring 8 kartu sensor, kendali LMPC & Deadman W/S, visualisasi orientasi 3D / PFD 2D / Kamera feed, dan perekaman CSV.", table_cell),
            Paragraph("• 3D Attitude & PFD HUD<br/>• 6-Thruster Matrix<br/>• Live Timer CSV Logger<br/>• Mode Real / Dummy Switch", table_cell)
        ],
        [
            Paragraph("<b>Tab 2: Grafik Realtime</b>", table_cell_bold),
            Paragraph("Visualisasi data dinamis 4 slot interaktif berkecepatan 60 FPS bebas lag berbasis PyQtGraph dengan pilihan kanal sensor via checkbox secara real-time.", table_cell),
            Paragraph("• Multi-kanal Kualitas Air<br/>• Parameter Adaptif TBM<br/>• Sinyal RAW & Tekanan<br/>• Status Baterai & Arus", table_cell)
        ],
        [
            Paragraph("<b>Tab 3: Import & Analisis</b>", table_cell_bold),
            Paragraph("Modul evaluasi data offline untuk memuat file CSV hasil penyelaman lapangan, menampilkan tabel pratinjau, dan menghitung statistik otomatis (Min, Max, Mean, Std).", table_cell),
            Paragraph("• Multi-kurva Interaktif<br/>• Ringkasan Statistik Misi<br/>• Pratinjau Tabel Log CSV", table_cell)
        ]
    ]
    t_tabs = Table(tab_data, colWidths=[120, 240, 144])
    t_tabs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_HEADER),
        ('BOX', (0, 0), (-1, -1), 0.75, BORDER_CLR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_CLR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_tabs)
    story.append(Spacer(1, 8))

    # ============================================================
    # 2. CHECKLIST MATRIKS FITUR
    # ============================================================
    story.append(Paragraph("2. Matriks Checklist Fitur Sistem GCS", h1_style))
    story.append(Paragraph(
        "Tabel berikut merangkum status implementasi seluruh modul dan fungsionalitas sistem wahana submersible Tyrant-AQ secara lengkap:",
        body_style
    ))

    feat_data = [
        [Paragraph("Kategori", table_header), Paragraph("Nama Fitur", table_header), Paragraph("Deskripsi Teknis", table_header), Paragraph("Status", table_header)],
        # Tab 1
        [Paragraph("Dashboard & Kontrol", table_cell_bold), Paragraph("Kontrol Manual 6-DOF", table_cell), Paragraph("Kontrol gerak 6 derajat kebebasan: Translasi (Surge, Sway, Heave) dan Rotasi (Roll, Pitch, Yaw) via GUI dan keyboard dengan safety deadman release.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Dashboard & Kontrol", table_cell_bold), Paragraph("LMPC Station-Keeping", table_cell), Paragraph("Kontrol kedalaman otomatis dengan target setpoint, konfigurasi horizon Np & Nc, dan bobot kendali.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Dashboard & Kontrol", table_cell_bold), Paragraph("8 Sensor Metric Cards", table_cell), Paragraph("Pembacaan real-time: Kedalaman, DO, pH, Suhu, Konduktivitas, Baterai INA226, Arus, dan Error Z.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Dashboard & Kontrol", table_cell_bold), Paragraph("6-Thruster Matrix", table_cell), Paragraph("Bar grafis PWM real-time untuk 4 thruster bidang horizontal dan 2 thruster bidang vertikal.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Dashboard & Kontrol", table_cell_bold), Paragraph("Perekam CSV & Live Timer", table_cell), Paragraph("Penyimpanan file CSV otomatis dengan indikator timer digital aktif berformat HH:MM:SS.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        
        # New Features
        [Paragraph("Navigasi Visual", table_cell_bold), Paragraph("Orientasi 3D Navigasi", table_cell), Paragraph("Model 3D Twin-Hull AUV 6-DOF rotasi real-time (Roll/Pitch/Yaw) dengan kontrol mouse orbit & zoom.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Navigasi Visual", table_cell_bold), Paragraph("PFD Horizon HUD 2D", table_cell), Paragraph("Artificial Horizon, depth ladder tape, heading compass tape, serta estimasi vektor arus EKF.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Vision & Kamera", table_cell_bold), Paragraph("Input Live Camera Feed", table_cell), Paragraph("Streaming video kamera USB / RTSP / Simulasi Bawah Air dengan Tactical HUD dan Snapshot 1-klik.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Simulasi & Hardware", table_cell_bold), Paragraph("Mode Real vs Dummy", table_cell), Paragraph("Switch 1-klik antara Hardware Real (Ethernet TCP/UDP atau USB) dan Simulator Internal built-in.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Observabilitas", table_cell_bold), Paragraph("Foxglove Studio Bridge", table_cell), Paragraph("WebSocket server ws://localhost:8765 broadcast telemetri 5-channel, export MCAP, dan layout preset.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Desain Antarmuka", table_cell_bold), Paragraph("Auto-Scalable Layout", table_cell), Paragraph("Tata letak adaptif auto-scaling terhadap DPI tinggi dan berbagai resolusi layar tanpa teks terpotong.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        
        # Tab 2 & 3
        [Paragraph("Grafik Sensor", table_cell_bold), Paragraph("4-Slot Dynamic Plots", table_cell), Paragraph("Visualisasi multi-kanal 60 FPS bebas lag berbasis PyQtGraph dengan pilihan kanal via checkbox.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
        [Paragraph("Analisis Offline", table_cell_bold), Paragraph("CSV Importer & Stats", table_cell), Paragraph("Plot kurva riwayat misi, kalkulasi statistik instan Min/Max/Mean/Std, dan tabel pratinjau data.", table_cell), Paragraph("<b>[✓] Selesai</b>", table_cell_center)],
    ]
    t_feat = Table(feat_data, colWidths=[95, 115, 224, 70])
    t_feat.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_HEADER),
        ('BOX', (0, 0), (-1, -1), 0.75, BORDER_CLR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_CLR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_feat)
    story.append(Spacer(1, 10))

    # ============================================================
    # 3. INTEGRASI FOXGLOVE STUDIO & ARSITEKTUR
    # ============================================================
    story.append(Paragraph("3. Integrasi Foxglove Studio (Robotics Observability Platform)", h1_style))
    story.append(Paragraph(
        "Foxglove Studio diintegrasikan ke dalam sistem GCS Tyrant-AQ menggunakan pola <i>Companion Architecture</i>. Modul server WebSocket ringan berjalan di port <code>8765</code> secara non-blocking. Ketika GCS beroperasi dalam mode Real maupun Simulasi Dummy, data telemetri otomatis dialirkan ke Foxglove Studio tanpa membebani thread rendering antarmuka utama PyQt5.",
        body_style
    ))

    fox_points = [
        "<b>Channel Siaran Realtime:</b> <code>/auv/attitude</code> (Pose 6-DOF), <code>/auv/water_quality</code> (pH, DO, Suhu, Konduktivitas), <code>/auv/thrusters</code> (PWM 1-6), <code>/auv/power</code> (Tegangan, Arus, SoC), dan <code>/auv/diagnostics</code> (LMPC WCET, disturbance).",
        "<b>Koneksi Cepat:</b> Buka Foxglove Studio (Desktop / Web di <code>https://studio.foxglove.dev</code>) -> Pilih <i>Open Connection</i> -> <i>Foxglove WebSocket</i> -> Hubungkan ke <code>ws://localhost:8765</code>.",
        "<b>Perekaman Standar MCAP:</b> Mendukung pencatatan log standar MCAP berkecepatan tinggi untuk evaluasi misi dan playback interaktif dengan timeline scrubbing.",
        "<b>Preset Konfigurasi:</b> Disediakan berkas template <code>config/foxglove_preset.json</code> untuk import tata letak visual instan."
    ]
    for pt in fox_points:
        story.append(Paragraph(f"• {pt}", body_style))

    story.append(Spacer(1, 8))

    # ============================================================
    # 4. ROADMAP UPGRADE FITUR MASA DEPAN (IN FUTURE UPGRADES)
    # ============================================================
    story.append(Paragraph("4. Roadmap Upgrade Fitur Masa Depan (In Future Upgrades)", h1_style))
    story.append(Paragraph(
        "Berikut adalah rencana roadmap pengembangan lanjutan untuk meningkatkan otonomi, kecerdasan buatan, dan keandalan wahana submersible Tyrant-AQ pada iterasi mendatang:",
        body_style
    ))

    future_data = [
        [Paragraph("Fase / Fitur", table_header), Paragraph("Fokus Inovasi", table_header), Paragraph("Spesifikasi & Rencana Implementasi", table_header), Paragraph("Prioritas", table_header)],
        [
            Paragraph("<b>1. Autonomous Mission Planner</b>", table_cell_bold),
            Paragraph("Navigasi Waypoint 3D & Acoustic Tracking", table_cell),
            Paragraph("Perancangan rute misi otomatis berbasis peta waduk satelit (QGIS / Leaflet), integrasi sensor akustik USBL / DVL untuk estimasi posisi bawah air tanpa GPS.", table_cell),
            Paragraph("<b>Tinggi (P1)</b>", table_cell_center)
        ],
        [
            Paragraph("<b>2. AI Underwater Computer Vision</b>", table_cell_bold),
            Paragraph("Deteksi Objek & Kekeruhan Air (YOLOv8/11)", table_cell),
            Paragraph("Pemrosesan citra kamera bawah air real-time untuk deteksi sampah plastik, eceng gondok, sedimentasi, dan estimasi kekeruhan air (*turbidity index*) berbasis AI on-edge.", table_cell),
            Paragraph("<b>Tinggi (P1)</b>", table_cell_center)
        ],
        [
            Paragraph("<b>3. 3D Bathymetric Heatmap</b>", table_cell_bold),
            Paragraph("Pemetaan Batimetri & Kontur Kualitas Air", table_cell),
            Paragraph("Interpolasi spasial data kualitas air (Kriging / IDW) untuk menghasilkan peta kontur sebaran pH, DO, dan suhu 3D sepanjang kedalaman waduk.", table_cell),
            Paragraph("<b>Sedang (P2)</b>", table_cell_center)
        ],
        [
            Paragraph("<b>4. Smart Failsafe & Geo-Fencing</b>", table_cell_bold),
            Paragraph("Prosedur Darurat Otonom", table_cell),
            Paragraph("Sistem pengaman otomatis: Pengapungan darurat (*Auto Surface Blow*) saat baterai kritis (<15%), kehilangan sinyal heartbeat >5 detik, atau kebocoran kompartemen.", table_cell),
            Paragraph("<b>Tinggi (P1)</b>", table_cell_center)
        ],
        [
            Paragraph("<b>5. Cloud IoT Sync & MQTT Bridge</b>", table_cell_bold),
            Paragraph("Sinkronisasi Cloud & Dashboard Web", table_cell),
            Paragraph("Pengunggahan data telemetri otomatis ke cloud server (MQTT / Firebase / InfluxDB) untuk pemantauan jarak jauh melalui web dashboard multi-user.", table_cell),
            Paragraph("<b>Sedang (P2)</b>", table_cell_center)
        ],
        [
            Paragraph("<b>6. Wireless Optical / Acoustic Telemetry</b>", table_cell_bold),
            Paragraph("Komunikasi Nirkabel Bawah Air", table_cell),
            Paragraph("Pengembangan transreceiver optik nirkabel (Blue-Green LED) berkecepatan tinggi untuk transfer data saat wahana menyelam tanpa kabel tethering.", table_cell),
            Paragraph("<b>Eksplorasi (P3)</b>", table_cell_center)
        ]
    ]
    t_future = Table(future_data, colWidths=[120, 110, 204, 70])
    t_future.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_HEADER),
        ('BOX', (0, 0), (-1, -1), 0.75, BORDER_CLR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_CLR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_future)
    story.append(Spacer(1, 10))

    # ============================================================
    # 5. KESIMPULAN & TANDA TANGAN
    # ============================================================
    story.append(Paragraph("5. Pengesahan Dokumen", h1_style))
    story.append(Paragraph(
        "Dokumen rencana implementasi ini menjadi acuan baku dalam pengujian fungsional dan pengembangan bertahap sistem Ground Control Station (GCS) wahana submersible Tyrant-AQ.",
        body_style
    ))
    story.append(Spacer(1, 8))

    sign_data = [
        [
            Paragraph("Bandung, September 2026<br/><b>Pengembang 1,</b><br/><br/><br/><br/><b><u>Bryan Gabriel Izaac Sasabone</u></b><br/>NIM: 101022300195", table_cell_center),
            Paragraph("Bandung, September 2026<br/><b>Pengembang 2,</b><br/><br/><br/><br/><b><u>Charisto Brilliant R.P</u></b><br/>NIM: 101022330187", table_cell_center),
        ]
    ]
    t_sign = Table(sign_data, colWidths=[250, 254])
    t_sign.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(t_sign)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF GEN] PDF successfully generated at: {output_path}")


if __name__ == "__main__":
    out_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IMPLEMENTATION_PLAN.pdf")
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    create_pdf(out_pdf)

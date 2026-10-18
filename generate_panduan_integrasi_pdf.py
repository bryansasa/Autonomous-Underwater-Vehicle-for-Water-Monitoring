# -*- coding: utf-8 -*-
"""
Generate Comprehensive Integration & GCS Deployment Guide PDF
for Tyrant-AQ AUV (Teensy 4.1, ESP32-S3, Jetson, and GCS Desktop/Web).
Designed for academic clarity and professional engineering reference.
"""
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether, PageBreak
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Adds running headers and page numbers to every page."""
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
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 802, "Tyrant-AQ AUV | SPELL Laboratory — Panduan Integrasi Hardware & GCS")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(54, 794, 558, 794)

        # Running Footer
        page_text = f"Halaman {self._pageNumber} dari {page_count}"
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, "S1 Teknik Elektro - Telkom University | Kerahasiaan: Internal Penelitian Tugas Akhir")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
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

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0F172A")
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#475569")
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1E293B"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )
    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#F8FAFC"),
        leftIndent=8,
        rightIndent=8,
        spaceBefore=3,
        spaceAfter=3
    )
    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F766E")
    )

    story = []

    # =========================================================
    # HEADER / COVER BLOCK
    # =========================================================
    story.append(Paragraph("PANDUAN INTEGRASI SISTEM & IMPLEMENTASI GCS", title_style))
    story.append(Paragraph(
        "Wahana Selam Nirawak (AUV) Tyrant-AQ — Waduk Saguling<br/>"
        "<b>SPELL Laboratory (Signal Processing & Embedded Logic Laboratory)</b><br/>"
        "S1 Teknik Elektro, Fakultas Teknik Elektro, Telkom University",
        subtitle_style
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=10))

    # Meta Info Card
    meta_data = [
        [
            Paragraph("<b>Target Hardware:</b> Teensy 4.1, ESP32-S3, Jetson Nano/Orin", body_style),
            Paragraph("<b>Versi Dokumen:</b> v1.2 (Oktober 2026)", body_style)
        ],
        [
            Paragraph("<b>Protokol Komunikasi:</b> micro-ROS (Humble) + HTTP Gateway", body_style),
            Paragraph("<b>Status Validasi:</b> HIL & Plant Sim Passed", body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[270, 234])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # =========================================================
    # 1. RINGKASAN EKSEKUTIF & ARSITEKTUR ALIRAN DATA
    # =========================================================
    story.append(Paragraph("1. Ringkasan Eksekutif & Peta Arsitektur Sistem", h1_style))
    story.append(Paragraph(
        "Sistem kendali dan telemetri Tyrant-AQ AUV mengintegrasikan dua mikrokontroler "
        "independen dengan sebuah komputer pendamping (Companion Computer) Nvidia Jetson, yang "
        "dihubungkan ke Ground Control Station (GCS) di permukaan melalui kabel tether Ethernet.",
        body_style
    ))

    # Architecture Box Diagram in Table Form
    arch_data = [
        [
            Paragraph("<b>Node Hardware & Firmware</b>", ParagraphStyle('TH', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#1E3A8A"))),
            Paragraph("<b>Transport & Protokol</b>", ParagraphStyle('TH', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#1E3A8A"))),
            Paragraph("<b>Peran, Tugas & Topik Utama</b>", ParagraphStyle('TH', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#1E3A8A")))
        ],
        [
            Paragraph("<b>ESP32-S3</b><br/>(Payload Controller)", body_style),
            Paragraph("USB CDC Serial<br/>(115200 bps)<br/>micro-ROS Humble", body_style),
            Paragraph("• Akuisisi 4 parameter air (pH, DO, EC via I2C, Suhu analog).<br/>"
                      "• Monitoring daya 2 rel (INA226 6S & Rel 4 Sensor).<br/>"
                      "• Penjadwalan adaptif <b>EA-DSRA</b> (1–5 s).<br/>"
                      "• 4 MOSFET saklar sensor (GPIO 4, 5, 6, 15).<br/>"
                      "<i>Topik: /tyrant/payload/water_quality, .../power/*</i>", body_style)
        ],
        [
            Paragraph("<b>Teensy 4.1</b><br/>(Propulsion Controller)", body_style),
            Paragraph("USB CDC Serial<br/>(115200 bps)<br/>micro-ROS Humble", body_style),
            Paragraph("• Estimasi sikap 3D (Roll, Pitch, Yaw) dari IMU.<br/>"
                      "• Estimasi kedalaman dari sensor tekanan Keller/Bar30.<br/>"
                      "• Alokasi kendali 6 thruster (T1–T6 PWM).<br/>"
                      "• Kontrol loop LMPC / PID depth hold & deadman.<br/>"
                      "<i>Topik: /tyrant/simple_state, /tyrant/control/*</i>", body_style)
        ],
        [
            Paragraph("<b>Nvidia Jetson</b><br/>(Companion Computer)", body_style),
            Paragraph("ROS 2 Native<br/>(FastDDS Domain 0)<br/>Python 3 / C++", body_style),
            Paragraph("• <b>micro-ROS Agent:</b> Menjembatani Teensy & ESP32-S3.<br/>"
                      "• <b>tyrant_mission_host:</b> Heartbeat 10 Hz & rosbag2 recorder.<br/>"
                      "• <b>GUI Gateway (server.py):</b> HTTP REST API @ port 8090.<br/>"
                      "• <b>Video Streamer:</b> Webcam USB 720p 15 fps via WebRTC/MJPEG.", body_style)
        ],
        [
            Paragraph("<b>GCS Desktop & Web</b><br/>(Surface Operator)", body_style),
            Paragraph("Tether Ethernet<br/>(TCP/HTTP 8090)<br/>PyQt5 & Web Three.js", body_style),
            Paragraph("• <b>01 Operasi:</b> Video kamera, 3D STL Model, data sensor, daya.<br/>"
                      "• <b>02 Kontrol & Misi:</b> Kendali manual, Set Surface, Mission Planner.<br/>"
                      "• <b>03 Grafik & Rekaman:</b> Multi-channel oscilloscope, export CSV.<br/>"
                      "• <b>04 Diagnostik & Tuning:</b> Health status, LMPC & EA-DSRA.", body_style)
        ]
    ]
    t_arch = Table(arch_data, colWidths=[110, 110, 284])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EFF6FF")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    # =========================================================
    # 2. STATUS INTEGRASI TERBARU (OKTOBER 2026)
    # =========================================================
    story.append(Paragraph("2. Status Integrasi & Verifikasi Komponen", h1_style))
    story.append(Paragraph(
        "Berdasarkan tinjauan menyeluruh terhadap repositori <code>Tyrant-simple-main</code> dan firmware:",
        body_style
    ))
    story.append(Paragraph("• <b>Firmware ESP32-S3 (firmware/esp):</b> Kode telah divalidasi melalui 28 pengujian native unit test dengan ASAN/UBSAN. Skema 6 pesan custom terletak pada <code>tyrant_payload_interfaces</code>. Kalibrasi shunt INA226 telah dikonfirmasi (Thruster: 200A/75mV = 0.000375 ohm, Rel Sensor: 0.1 ohm). Heartbeat timeout host diatur 1000 ms.", bullet_style))
    story.append(Paragraph("• <b>Firmware Teensy 4.1 (firmware/teensy):</b> Kontrak status kendaraan dipublikasikan pada topik <code>/tyrant/simple_state</code> mencakup roll, pitch, yaw, depth, dan status validitas. Timeout perintah manual adalah 250 ms (jika koneksi terputus >250 ms, pendorong otomatis netral).", bullet_style))
    story.append(Paragraph("• <b>Mission Host & HIL (ros2_ws):</b> Berhasil diuji pada simulasi Hardware-in-the-Loop (HIL) 9 Oktober 2026. Supervisor mengirimkan heartbeat otomatis 10 Hz ke kedua mikrokontroler dan merekam rosbag terpadu.", bullet_style))
    story.append(Paragraph("• <b>GUI Gateway (gui/backend/server.py):</b> Gateway HTTP tahap 1 telah selesai dibuat. Menyajikan snapshot JSON lengkap pada endpoint <code>GET /api/state</code> di port 8090 dengan pembersihan NaN/Infinity dan tracking freshness usia data.", bullet_style))
    story.append(Paragraph("• <b>Desktop GCS (GCS-Submersible):</b> Telah direstrukturisasi total. Panel matriks pendorong telah dibersihkan dari Tab 1 untuk memberi ruang lega pada visualisasi 3D STL. Tab 2 telah diselaraskan dengan PRD Charisto (Kendali manual, Set Surface, dan Tactical Mission Planner 9 kolom). Logo SPELL Laboratory telah disematkan pada action bar.", bullet_style))
    story.append(Paragraph("• <b>Web Console (gui/mockup):</b> Tampilan 4-window responsif dengan visualisasi model 3D STL (Three.js) yang dapat dirotasi interaktif dan memiliki goyangan air alami. Memiliki aset lokal mandiri tanpa ketergantungan CDN internet.", bullet_style))
    story.append(Spacer(1, 10))

    # =========================================================
    # 3. PANDUAN LANGKAH DEMI LANGKAH DEPLOYMENT HARDWARE
    # =========================================================
    story.append(Paragraph("3. Panduan Langkah demi Langkah Menuju Uji Nyata (Next Steps)", h1_style))

    story.append(Paragraph("Langkah 1: Flash Firmware ke Mikrokontroler Fisik", h2_style))
    story.append(Paragraph(
        "Gunakan PlatformIO untuk mem-build dan mengunggah kode firmware ke kedua mikrokontroler:",
        body_style
    ))
    code_box1 = [
        [Paragraph(
            "<font color=\"#94A3B8\"># 1. Upload Firmware ESP32-S3 (Sensor Kualitas Air &amp; Daya)</font><br/>"
            "<font color=\"#38BDF8\"><b>cd</b></font> /home/charisto/tyrant-simple/firmware/esp<br/>"
            "<font color=\"#38BDF8\"><b>bash</b></font> scripts/build.sh                <font color=\"#64748B\"># Build micro-ROS library &amp; firmware</font><br/>"
            "<font color=\"#38BDF8\"><b>pio</b></font> run -t upload                    <font color=\"#64748B\"># Flash ke board ESP32-S3 fisik</font><br/><br/>"
            "<font color=\"#94A3B8\"># 2. Upload Firmware Teensy 4.1 (Navigasi &amp; Thruster 6-DOF)</font><br/>"
            "<font color=\"#38BDF8\"><b>cd</b></font> /home/charisto/tyrant-simple/firmware/teensy<br/>"
            "<font color=\"#38BDF8\"><b>pio</b></font> run -t upload                    <font color=\"#64748B\"># Flash ke board Teensy 4.1</font>",
            code_style
        )]
    ]
    t_c1 = Table(code_box1, colWidths=[504])
    t_c1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#334155")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_c1)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Langkah 2: Konfigurasi Udev Rules USB di Jetson", h2_style))
    story.append(Paragraph(
        "Agar port USB Teensy dan ESP32-S3 tidak tertukar saat reboot atau saat dicolokkan ke port USB Jetson yang berbeda, pasang aturan udev statis:",
        body_style
    ))
    code_box2 = [
        [Paragraph(
            "<font color=\"#94A3B8\"># Buat file /etc/udev/rules.d/99-tyrant.rules di Jetson:</font><br/>"
            "SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"16c0\", ATTRS{idProduct}==\"0483\", SYMLINK+=\"<font color=\"#38BDF8\">tyrant-teensy</font>\"<br/>"
            "SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"303a\", ATTRS{idProduct}==\"1001\", SYMLINK+=\"<font color=\"#38BDF8\">tyrant-esp</font>\"<br/><br/>"
            "<font color=\"#94A3B8\"># Reload aturan udev:</font><br/>"
            "<font color=\"#38BDF8\"><b>sudo</b></font> udevadm control --reload-rules &amp;&amp; <font color=\"#38BDF8\"><b>sudo</b></font> udevadm trigger",
            code_style
        )]
    ]
    t_c2 = Table(code_box2, colWidths=[504])
    t_c2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#334155")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_c2)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Langkah 3: Jalankan Micro-ROS Agent & Mission Host di Jetson", h2_style))
    story.append(Paragraph(
        "Mission Host bertindak sebagai koordinator keselamatan, supervisor heartbeat 10 Hz, serta pencatat rosbag data rekaman ilmiah:",
        body_style
    ))
    code_box3 = [
        [Paragraph(
            "<font color=\"#94A3B8\"># Terminal 1: Eksekusi Mission Host Launcher di Jetson</font><br/>"
            "<font color=\"#38BDF8\"><b>source</b></font> /opt/ros/humble/setup.bash<br/>"
            "<font color=\"#38BDF8\"><b>source</b></font> /home/charisto/tyrant-simple/ros2_ws/install/setup.bash<br/>"
            "<font color=\"#38BDF8\"><b>ros2</b></font> launch tyrant_mission_host mission_host.launch.py start_agents:=true",
            code_style
        )]
    ]
    t_c3 = Table(code_box3, colWidths=[504])
    t_c3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#334155")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_c3)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Langkah 4: Jalankan Backend Gateway GUI Telemetri", h2_style))
    story.append(Paragraph(
        "Gateway ini mengonversi seluruh topik ROS 2 menjadi API JSON REST berlatensi rendah untuk dibaca oleh browser:",
        body_style
    ))
    code_box4 = [
        [Paragraph(
            "<font color=\"#94A3B8\"># Terminal 2: Jalankan HTTP Server Gateway di Jetson</font><br/>"
            "<font color=\"#38BDF8\"><b>cd</b></font> /home/charisto/tyrant-simple/gui/backend<br/>"
            "<font color=\"#38BDF8\"><b>python3</b></font> server.py --bind 0.0.0.0 --port 8090 --payload-namespace /tyrant/payload",
            code_style
        )]
    ]
    t_c4 = Table(code_box4, colWidths=[504])
    t_c4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0F172A")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#334155")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_c4)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Langkah 5: Buka GCS Desktop & Web Console di Laptop Permukaan", h2_style))
    story.append(Paragraph(
        "Hubungkan laptop operator ke Jetson melalui kabel tether Ethernet (IP Jetson default <code>192.168.1.170</code> atau subnet tether <code>10.42.0.246</code>):",
        body_style
    ))
    story.append(Paragraph("• <b>Desktop GCS:</b> Buka <code>BUKA_GCS_SUBMERSIBLE.bat</code>. Masukkan IP Jetson dan Port 9000, lalu klik <b>CONNECT</b>.", bullet_style))
    story.append(Paragraph("• <b>Web Console:</b> Buka browser Chrome di alamat <code>http://127.0.0.1:8088</code>. Data telemetri, kedalaman, dan kualitas air akan diperbarui secara real-time.", bullet_style))
    story.append(Spacer(1, 10))

    # =========================================================
    # 4. PROSEDUR KESELAMATAN & FAILSAFE
    # =========================================================
    story.append(Paragraph("4. Prosedur Keselamatan & Failsafe Operasi", h1_style))
    story.append(Paragraph(
        "Penelitian lapangan di Waduk Saguling menuntut kepatuhan ketat terhadap protokol failsafe:",
        body_style
    ))
    story.append(Paragraph("1. <b>Deadman Switch (Spacebar):</b> Pada kendali manual, motor thruster hanya berputar jika tombol Spacebar ditahan bersamaan dengan tombol arah (W/S/A/D/Q/E/R/F). Begitu Spacebar dilepas atau jendela GCS kehilangan fokus (window blur), seluruh pendorong otomatis seketika netral.", bullet_style))
    story.append(Paragraph("2. <b>Kalibrasi Nol Permukaan (Set Surface):</b> Sebelum wahana ditenggelamkan, operator wajib melakukan kalibrasi nol kedalaman (Set Surface) saat mode IDLE di permukaan air untuk menetapkan acuan tekanan atmosfer lokal.", bullet_style))
    story.append(Paragraph("3. <b>Ambang Daya Baterai Kritis (EA-DSRA):</b> Jika tegangan baterai thruster 6S turun di bawah 21.0 V (atau SoC < 30%), sistem EA-DSRA otomatis beralih ke interval sampling penghematan daya (1–5 s) dan GCS akan menyalakan alarm visual amber/merah.", bullet_style))
    story.append(Paragraph("4. <b>Emergency Surface:</b> Tombol 'Naik ke Permukaan' di Tab 2 memerintahkan wahana untuk menetapkan target depth 0.0 m dengan prioritas daya dorong vertikal penuh menuju permukaan.", bullet_style))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#CBD5E1"), spaceAfter=8))
    story.append(Paragraph(
        "<b>SPELL Laboratory — Telkom University</b> | Dokumen diterbitkan secara otomatis untuk mendukung keselarasan integrasi hardware & software Tugas Akhir Tyrant-AQ AUV.",
        ParagraphStyle('FooterNote', parent=body_style, fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF berhasil dibuat di: {output_path}")


if __name__ == '__main__':
    out_dir = r"d:\Tugas Akhir\Tugas-Akhir-YEN\Program-YEN"
    pdf_filename = os.path.join(out_dir, "PANDUAN_INTEGRASI_HARDWARE_DAN_GCS.pdf")
    create_pdf(pdf_filename)

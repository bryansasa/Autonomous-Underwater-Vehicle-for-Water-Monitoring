#!/usr/bin/env bash
# ========================================================
# Instalasi Dependensi GCS Submersible Tyrant-AQ di Ubuntu / Debian
# ========================================================

set -e

echo "========================================================"
echo "  Menginstall Dependensi Tyrant-AQ GCS di Ubuntu/Debian"
echo "========================================================"

# Update & install library sistem dan Python Qt
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-pyqt5 \
    python3-pyqt5.qtopengl \
    python3-pyqtgraph \
    python3-serial \
    python3-numpy \
    python3-reportlab \
    python3-websockets \
    libxcb-cursor0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxkbcommon-x11-0 \
    libgl1 \
    libglib2.0-0

echo ""
echo "========================================================"
echo "  Instalasi dependensi sistem selesai!"
echo "  Memastikan paket pip (opencv-python-headless, dll)..."
echo "========================================================"

cd "$(dirname "$0")"

# Hapus opencv-python berkonten GUI jika pernah terinstall karena sering merusak xcb plugin Qt
pip3 uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true

pip3 install -r requirements.txt

echo ""
echo "========================================================"
echo "  Semua dependensi siap!"
echo "  Jalankan GCS dengan: bash run_gcs.sh"
echo "========================================================"

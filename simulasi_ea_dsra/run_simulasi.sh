#!/usr/bin/env bash
# ========================================================
# Simulasi EA-DSRA Bab 4 - Tyrant-AQ AUV (Ubuntu / Linux)
# ========================================================
set -e

cd "$(dirname "$0")"

echo "========================================================"
echo "  Menjalankan Simulasi EA-DSRA Bab 4 (Python Opsi A)"
echo "  Wahana Submersible Otonom - Telkom University"
echo "========================================================"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan!"
    exit 1
fi

python3 simulasi_ea_dsra.py

echo ""
echo "========================================================"
echo "  Simulasi Selesai!"
echo "  Hasil grafik & tabel tersimpan di: output_bab4/"
echo "========================================================"

@echo off
title Simulasi EA-DSRA Bab 4 - Tyrant-AQ AUV
echo ========================================================
echo   Menjalankan Simulasi EA-DSRA Bab 4 (Python Opsi A)
echo   Wahana Submersible Otonom - Telkom University
echo ========================================================
cd /d "%~dp0"
python simulasi_ea_dsra.py
echo.
echo ========================================================
echo   Simulasi Selesai!
echo   Buka folder 'output_bab4' untuk melihat grafik & tabel.
echo ========================================================
pause

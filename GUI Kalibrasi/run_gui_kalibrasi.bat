@echo off
title Submersible Calibration - Tyrant-AQ
echo ========================================================
echo Membuka Submersible Calibration - Tyrant-AQ
echo ========================================================
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Aplikasi tertutup dengan error atau Python belum terinstall.
    pause
)

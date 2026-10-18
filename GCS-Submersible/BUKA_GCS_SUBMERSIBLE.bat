@echo off
title Tyrant-AQ AUV Ground Control Station
echo ========================================================
echo Membuka Tyrant-AQ AUV Ground Control Station (GCS)...
echo ========================================================
if exist "%~dp0dist\Tyrant-AQ_GCS\Tyrant-AQ_GCS.exe" (
    start "" "%~dp0dist\Tyrant-AQ_GCS\Tyrant-AQ_GCS.exe"
    exit
) else (
    echo Binary .exe tidak ditemukan di folder dist, menjalankan via Python...
    python "%~dp0main.py"
    pause
)

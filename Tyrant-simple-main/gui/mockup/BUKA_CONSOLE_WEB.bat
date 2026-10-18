@echo off
title Tyrant Web Console Mockup
echo ========================================================
echo Membuka Tyrant Web Console Mockup...
echo URL: http://127.0.0.1:8088
echo ========================================================
start "" http://127.0.0.1:8088
python -m http.server 8088 --bind 127.0.0.1
pause

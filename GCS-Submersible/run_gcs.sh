#!/usr/bin/env bash
# ========================================================
# Tyrant-AQ AUV Ground Control Station (GCS) - Ubuntu/Linux
# ========================================================

echo "========================================================"
echo "Launching Tyrant-AQ AUV Tactical GCS (QGC Fly View)"
echo "========================================================"

# Pastikan berada di direktori skrip ini
cd "$(dirname "$0")"

# 1. Cek ketersediaan python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan! Silakan install Python 3 terlebih dahulu."
    echo "Contoh: sudo apt update && sudo apt install -y python3 python3-pip"
    exit 1
fi

# 2. Cek dependensi sistem kritis Ubuntu (libxcb-cursor0 untuk PyQt5 di Ubuntu 22.04+)
if [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
    if ! ldconfig -p 2>/dev/null | grep -q "libxcb-cursor.so.0" && \
       ! [ -f /usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0 ] && \
       ! [ -f /usr/lib/aarch64-linux-gnu/libxcb-cursor.so.0 ]; then
        echo "[WARNING] Pustaka sistem 'libxcb-cursor.so.0' belum terpasang."
        echo "          Qt xcb membutuhkan paket libxcb-cursor0 agar GUI dapat terbuka di Ubuntu 22.04+."
        if command -v sudo &> /dev/null; then
            echo "[INFO] Mencoba menginstall otomatis libxcb-cursor0 via sudo..."
            sudo apt update -qq && sudo apt install -y libxcb-cursor0
        else
            echo "[ERROR] Silakan jalankan manual: sudo apt install -y libxcb-cursor0"
        fi
    fi
fi

# 3. Hindari konflik Qt platform plugin dari cv2/qt/plugins (opencv-python)
unset QT_QPA_PLATFORM_PLUGIN_PATH

# Jika PyQt5 terpasang via pip, arahkan langsung ke direktori plugin PyQt5
PYQT5_PLUGIN_DIR=$(python3 -c "import PyQt5, os; p = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins'); print(p if os.path.exists(p) else '')" 2>/dev/null || true)
if [ -n "$PYQT5_PLUGIN_DIR" ]; then
    export QT_QPA_PLATFORM_PLUGIN_PATH="$PYQT5_PLUGIN_DIR"
fi

# 4. Cek dan pastikan dependensi Python terpasang
if ! python3 -c "import PyQt5, pyqtgraph, cv2, serial, websockets" 2>/dev/null; then
    echo "[INFO] Beberapa dependensi Python belum terpasang."
    echo "[INFO] Memasang otomatis melalui requirements.txt..."
    pip3 install -r requirements.txt || python3 -m pip install -r requirements.txt || true
fi

# 5. Jalankan aplikasi GCS
exec python3 main.py "$@"

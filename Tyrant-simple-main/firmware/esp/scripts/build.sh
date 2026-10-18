#!/usr/bin/env bash
set -euo pipefail
esp_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PLATFORMIO_CORE_DIR="$esp_root/.pio-core"
export PLATFORMIO_CACHE_DIR="$PLATFORMIO_CORE_DIR/.cache"
export PIP_CACHE_DIR="$PLATFORMIO_CORE_DIR/pip-cache"
export PYTHONDONTWRITEBYTECODE=1
payload_python="$PLATFORMIO_CORE_DIR/penv/bin/python"
if [[ ! -x "$payload_python" ]]; then
    python3 -m venv "$PLATFORMIO_CORE_DIR/penv"
fi
if ! "$payload_python" -c 'import platformio' >/dev/null 2>&1; then
    "$payload_python" -m pip install 'platformio==6.2.0'
fi
payload_profile="${1:-esp32-s3-devkitm-1}"
case "$payload_profile" in
  esp32-s3-devkitm-1|esp32-s3-sim) ;;
  *) echo "Unknown payload profile: $payload_profile" >&2; exit 2 ;;
esac
exec "$payload_python" -m platformio run -d "$esp_root" -e "$payload_profile"

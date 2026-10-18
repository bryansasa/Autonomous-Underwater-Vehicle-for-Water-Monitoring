# Alias port ESP32-S3

Identitas dikonfirmasi pengguna 2026-10-08 di laptop:

- VID/PID: `303a:1001`
- USB serial: `28:84:85:8B:BD:38`
- Interface serial: `00`
- By-id: `/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_28:84:85:8B:BD:38-if00`
- Alias yang direncanakan: `/dev/tyrant-esp`

File `99-tyrant-esp.rules` hanya disiapkan dalam folder esp. Pemasangan pada
`/etc/udev/rules.d` dilakukan melalui terminal host; belum dipasang oleh agen.
Aturan tidak mengubah permissions/group perangkat.

Pada laptop, dengan ESP masih terhubung sebagai ttyACM0:

```bash
sudo install -m 0644 /home/charisto/tyrant-simple/firmware/esp/deployment/99-tyrant-esp.rules /etc/udev/rules.d/99-tyrant-esp.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add /sys/class/tty/ttyACM0
udevadm settle
ls -l /dev/tyrant-esp
readlink -f /dev/tyrant-esp
```

Setelah cabut/pasang dan reboot, ulangi dua perintah terakhir. Target boleh
berubah ke ttyACM1/ttyACM2; identitas ESP harus tetap sama:

```bash
udevadm info --query=property --name=/dev/tyrant-esp | grep -E '^(ID_VENDOR_ID|ID_MODEL_ID|ID_SERIAL_SHORT|ID_USB_INTERFACE_NUM)='
```

Jika firmware/bootloader mengganti descriptor USB, periksa kembali ID. Aturan
ini khusus identitas native USB Serial/JTAG yang telah dilaporkan; bukan port
USB-UART eksternal dengan identitas berbeda.

Pada Jetson, aturan perlu dipasang di host Jetson setelah properti perangkat
terverifikasi. Container deployment memakai mount `/dev:/host-dev`; alias akan
berada pada `/host-dev/tyrant-esp`. Launcher/agent/container belum diubah.

## Alias Teensy, identitas terverifikasi

Pengguna mengonfirmasi properti berikut pada 2026-10-08 di laptop:
VID/PID `16c0:0483`, serial `13843280`, interface `00`; saat verifikasi
Teensy berada di `ttyACM1` dan ESP di `ttyACM0`.
File `99-tyrant-teensy.rules` disimpan di folder esp untuk instalasi host;
firmware Teensy dan `ros2_ws` tidak diubah.

Dengan Teensy masih di ttyACM1, jalankan pada laptop:

```bash
sudo install -m 0644 /home/charisto/tyrant-simple/firmware/esp/deployment/99-tyrant-teensy.rules /etc/udev/rules.d/99-tyrant-teensy.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add /sys/class/tty/ttyACM1
udevadm settle
ls -l /dev/tyrant-esp /dev/tyrant-teensy
```

Hentikan agent yang menggunakan port sebelum uji cabut/pasang. Cabut kedua
board, pasang Teensy dahulu lalu ESP. Verifikasi identitas melalui alias:

```bash
for alias in /dev/tyrant-esp /dev/tyrant-teensy; do
  echo "ALIAS: $alias"
  readlink -f "$alias"
  udevadm info --query=property --name="$alias" | grep -E '^(ID_VENDOR_ID|ID_MODEL_ID|ID_SERIAL_SHORT|ID_USB_INTERFACE_NUM)='
done
```

Alias ESP harus tetap menunjukkan `28:84:85:8B:BD:38` dan alias Teensy
`13843280`, apa pun nomor ttyACM masing-masing. Reboot host dan ulangi
verifikasi sebagai uji berikutnya. Alias Teensy ini khusus mode USB Serial
runtime; bootloader upload yang memiliki descriptor berbeda belum dicakup.

# Rencana identifikasi port Teensy dan ESP

Status 7 Oktober 2026: dicatat untuk sesi berikutnya; belum memasang aturan udev baru atau mengintegrasikan ESP.

## Tujuan

Jetson harus dapat membedakan Teensy dan ESP walaupun urutan colok berubah. Nomor `/dev/ttyACM0` atau `/dev/ttyUSB0` tidak boleh menjadi identitas utama.

Teensy saat ini sudah dikenali melalui:

```text
Host:      /dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00
Container: /host-dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00
```

Launcher sudah memakai path itu. Serial USB yang tampak adalah `13843280`; properti udev tetap perlu dibaca sebelum membuat aturan alias. ESP belum diketahui model, bridge USB, serial, maupun protokolnya.

## Langkah sesi berikutnya

1. Hubungkan perangkat satu per satu dan catat label fisiknya.
2. Ambil path by-id, VID, PID, USB serial, dan interface setiap perangkat.
3. Pilih by-id jika unik dan stabil. Bila perlu buat alias host `/dev/tyrant-teensy` dan `/dev/tyrant-esp`.
4. Uji keduanya terpasang bersamaan, cabut/pasang dengan urutan berbeda, lalu reboot.
5. Perbarui konfigurasi aplikasi/container hanya setelah identitas terverifikasi.

Inventaris **pada host Jetson**, ganti nama port sesuai hasil deteksi:

```bash
ls -l /dev/serial/by-id/
ls -l /dev/serial/by-path/
udevadm info --query=property --name=/dev/ttyACM0
udevadm info --attribute-walk --name=/dev/ttyACM0
```

| Perangkat | USB serial | VID/PID | Port/by-id | Status |
|---|---|---|---|---|
| Teensy 4.1 | tampak `13843280` | belum dicatat | path di atas | by-id sudah digunakan |
| ESP | belum diketahui | belum diketahui | belum diketahui | pending |

USB serial tidak selalu sama dengan ID chip atau MAC ESP. Pada board dengan bridge USB-UART, identitas USB dapat berasal dari bridge tersebut. Jangan mengasumsikan VID/PID saja unik untuk tiap board. Jika serial kosong atau sama antardevice, pertimbangkan by-path (terikat port fisik) atau handshake identitas di protokol aplikasi. Pilihan akhir bergantung hardware ESP yang dibawa.

## Bentuk aturan udev, belum siap dipasang

Contoh konseptual saja; semua placeholder wajib diganti berdasarkan `udevadm`. Aturan dapat disimpan nanti pada host di `/etc/udev/rules.d/99-tyrant-serial.rules`:

```text
SUBSYSTEM=="tty", ENV{ID_VENDOR_ID}=="<VID_TEENSY>", ENV{ID_MODEL_ID}=="<PID_TEENSY>", ENV{ID_SERIAL_SHORT}=="<SERIAL_TEENSY>", SYMLINK+="tyrant-teensy"
SUBSYSTEM=="tty", ENV{ID_VENDOR_ID}=="<VID_ESP>", ENV{ID_MODEL_ID}=="<PID_ESP>", ENV{ID_SERIAL_SHORT}=="<SERIAL_ESP>", SYMLINK+="tyrant-esp"
```

Perangkat multi-interface mungkin memerlukan pencocokan interface tambahan. Aturan ini membuat symlink; tidak menjamin akses container. Referensi: [udev rules dari systemd](https://github.com/systemd/systemd/blob/main/man/udev.xml) dan [udevadm](https://www.kernel.org/pub/linux/utils/kernel/hotplug/udev/udevadm.html).

## Dampak ke Docker

Mount host `/dev` sekarang terlihat di container sebagai `/host-dev`; alias host nantinya harus diperiksa resolusinya dari dalam container. Launcher saat ini hanya menambahkan izin serial ACM major 166. Jika ESP memakai `ttyUSB` major 188, izinnya perlu ditambahkan berdasarkan perangkat yang nyata. Mengubah environment atau izin device container memerlukan pembuatan ulang container; `docker restart` tidak mengganti konfigurasi awal.

Integrasi ESP perlu menetapkan baud, format frame, arah data, reconnect, dan siapa pemilik port. Jangan menjalankan micro-ROS agent pada ESP hanya karena perangkat tersebut memiliki serial USB; harus sesuai firmware/protokol ESP.

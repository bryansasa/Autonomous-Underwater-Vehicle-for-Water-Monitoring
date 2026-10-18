# Cheatsheet terminal Jetson / Tyrant

Baseline 7 Oktober 2026. Semua perintah di bawah adalah referensi untuk sesi berikutnya; tidak perlu dijalankan sekarang.

| Label | Terminal / prompt |
|---|---|
| LAPTOP | `charisto@charisto-ubuntu` |
| JETSON | SSH host, `nvidia@nvidia-desktop` |
| CONTAINER | setelah `docker exec`, biasanya `root@nvidia-desktop:/ws#` |

`exit` keluar satu lapisan shell: dari container kembali ke host, dari SSH kembali ke laptop. Ctrl+C menghentikan perintah foreground seperti echo, heartbeat, dan log follow.

## A. SSH dan copy — LAPTOP

```bash
ssh nvidia@10.42.0.246
```

Copy script deployment ke Jetson:

```bash
scp -r /home/charisto/tyrant-simple/companion/jetson nvidia@10.42.0.246:/home/nvidia/ros2_docker/ws/
```

Ambil seluruh bag ke folder laptop (dapat besar):

```bash
mkdir -p /home/charisto/tyrant-simple/jetson_bags
scp -r nvidia@10.42.0.246:/home/nvidia/ros2_docker/ws/bags/. /home/charisto/tyrant-simple/jetson_bags/
```

## B. Container harian — JETSON

```bash
docker ps -a
docker logs --tail 80 tyrant-companion
docker logs --tail 30 -f tyrant-companion
docker inspect tyrant-companion --format 'Status={{.State.Status}} RestartCount={{.RestartCount}}'
docker inspect tyrant-companion --format 'RestartPolicy={{.HostConfig.RestartPolicy.Name}}'
docker stats --no-stream tyrant-companion
```

Start / stop / restart (pilih sesuai kebutuhan):

```bash
docker start tyrant-companion
docker stop -t 30 tyrant-companion
docker restart -t 30 tyrant-companion
```

Stop menutup agent dan recorder. `docker start` membuat sesi recorder baru. Jangan jalankan ketiga baris sekaligus jika hanya ingin start.

Masuk shell tanpa menghentikan proses container:

```bash
docker exec -it tyrant-companion bash
```

## C. ROS harian — CONTAINER

Source setiap shell baru:

```bash
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
cd /ws
```

```bash
ros2 node list
ros2 topic list
ros2 pkg list | grep -E '^(tyrant_|micro_ros_agent)'
ros2 pkg prefix micro_ros_agent
timeout 15 ros2 topic echo /tyrant/system/health --once
timeout 15 ros2 topic echo /tyrant/simple_state --once
timeout 15 ros2 topic echo /tyrant/sensors/imu --once
timeout 15 ros2 topic echo /tyrant/communication/diagnostics --once
ros2 topic info /tyrant/system/health --verbose
ros2 topic hz /tyrant/system/health
```

`timeout` berhenti jika pesan tidak tiba dalam 15 detik; `topic hz` dihentikan dengan Ctrl+C. Telemetry diterima tidak otomatis berarti sensor valid. HWT sedang dilepas pada akhir sesi sehingga estimator false adalah kondisi yang diketahui.

Perintah satu kali dari **JETSON**, tanpa masuk shell container:

```bash
docker exec tyrant-companion bash -lc 'source /opt/ros/humble/setup.bash; source /ws/install/setup.bash; timeout 15 ros2 topic echo /tyrant/system/health --once'
```

## D. Heartbeat bench — CONTAINER, hanya saat diperlukan

Gunakan hanya jika tidak ada teleop atau pemilik heartbeat lain. Hentikan dengan Ctrl+C sebelum tes kehilangan heartbeat.

```bash
ros2 topic info /tyrant/host_heartbeat --verbose
ros2 topic pub --rate 10 /tyrant/host_heartbeat std_msgs/msg/UInt32 '{data: 1}'
```

Nilai tetap cukup untuk memeriksa penerimaan heartbeat pada implementasi saat ini; perintah ini tidak meminta mode MANUAL/AUTO. Jangan jadikan heartbeat bench layanan otomatis. Tanpa heartbeat, umur `4294967295` menandakan belum pernah diterima; mode akhir sesi IDLE=1, SAFE=4.

## E. Bag dan disk

Pada **JETSON**:

```bash
df -h /home/nvidia/ros2_docker/ws
du -sh /home/nvidia/ros2_docker/ws/bags
ls -dt /home/nvidia/ros2_docker/ws/bags/jetson_* | head
```

Untuk menutup rekaman aktif dan memeriksa bag terakhir, **JETSON**:

```bash
docker stop -t 30 tyrant-companion
latest_bag=$(ls -dt /home/nvidia/ros2_docker/ws/bags/jetson_* | head -n 1)
printf '%s\n' "$latest_bag"
```

Pastikan path tercetak menunjuk sesi yang ingin diperiksa, kemudian:

```bash
docker run --rm --network none \
  --mount type=bind,src=/home/nvidia/ros2_docker/ws,dst=/ws,readonly \
  --entrypoint /bin/bash tyrant-companion:bench -lc \
  "source /opt/ros/humble/setup.bash; source /ws/install/setup.bash; ros2 bag info /ws/bags/$(basename "$latest_bag")"
docker start tyrant-companion
```

Bag baru dipecah setiap 300 detik. Tidak ada penghapusan otomatis. Hindari replay bag kontrol ke domain ROS kendaraan aktif karena dapat menerbitkan ulang pesan yang direkam.

## F. Port USB — JETSON

```bash
ls -l /dev/serial/by-id/
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
readlink -f /dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00
udevadm info --query=property --name=/dev/ttyACM0 | grep -E '^(ID_SERIAL|ID_SERIAL_SHORT|ID_VENDOR_ID|ID_MODEL_ID|ID_PATH)='
```

`ttyACM0` pada perintah inventaris harus disesuaikan dengan perangkat yang benar-benar terpasang. Path Teensy dari **container baru**:

```bash
docker exec tyrant-companion ls -l /host-dev/serial/by-id/
```

Jangan membuka serial Teensy menggunakan serial monitor saat agent sedang memakainya. Rencana alias ESP/Teensy ada di [dokumen identitas port](Jetson_Rencana_Identitas_Port_Teensy_ESP.md).

## G. Diagnosis internet

**LAPTOP**:

```bash
nmcli -f NAME,TYPE,DEVICE connection show --active
ip -4 route
getent hosts github.com
sysctl net.ipv4.ip_forward
sudo iptables -S DOCKER-USER
sudo iptables -t nat -S POSTROUTING
```

**JETSON**:

```bash
ip -4 route
ping -c 3 -W 2 10.42.0.1
ping -c 3 -W 2 1.1.1.1
getent hosts github.com
cat /run/systemd/resolve/resolv.conf
docker exec tyrant-companion getent hosts github.com
```

Ping gagal saja tidak membuktikan internet mati karena ICMP dapat diblokir. Jika host juga gagal DNS, diagnosis tidak boleh berhenti di container. Perintah pemulihan sesuai topologi sesi ada di [catatan setup](Jetson_Setup_dan_Catatan_Deployment_2026-10-07.md).

## H. Build ulang — pemeliharaan, bukan startup harian

Hentikan `tyrant-companion` terlebih dahulu pada **JETSON**, lalu gunakan container lama untuk build:

```bash
docker stop -t 30 tyrant-companion
docker start ros2
docker exec -it ros2 bash
```

Di **CONTAINER**:

```bash
source /opt/ros/humble/setup.bash
cd /ws
colcon build --packages-select tyrant_interfaces tyrant_teleop tyrant_sim --symlink-install --executor sequential
source /ws/install/setup.bash
```

Build agent hanya bila source/dependency agent memang berubah:

```bash
CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 \
colcon build --packages-up-to micro_ros_agent --executor sequential \
  --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

Kembali ke **JETSON** dengan `exit`, lalu:

```bash
docker stop -t 30 ros2
docker start tyrant-companion
```

Perubahan source/build di `/ws` terlihat kedua container. Instalasi dependency baru ke filesystem container `ros2` tidak otomatis masuk `tyrant-companion`; pembaruan image/container diperlukan jika dependency runtime berubah. Jangan menyalin hasil build x86 laptop ke ARM64.

## I. Reboot dan rollback — JETSON

```bash
systemctl is-enabled docker
```

Jika belum enabled, `sudo systemctl enable docker`. Untuk uji boot otomatis, container harus sedang berjalan sebelum `sudo reboot`. SSH terputus saat reboot. Setelah masuk lagi, periksa `docker ps`, log, dan health. Policy `unless-stopped` tidak menyalakan container yang sengaja distop.

Rollback ke agent manual:

```bash
docker stop -t 30 tyrant-companion
docker start ros2
docker exec -it ros2 bash
```

Di **CONTAINER LAMA**:

```bash
source /opt/ros/humble/setup.bash
source /ws/install/setup.bash
ros2 run micro_ros_agent micro_ros_agent serial \
  --dev /dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00 -v4
```

Container lama memakai `/dev`; container otomatis memakai `/host-dev`. Pastikan hanya satu agent membuka Teensy.

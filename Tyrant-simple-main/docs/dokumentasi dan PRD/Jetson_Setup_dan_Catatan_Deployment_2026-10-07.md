# Setup dan catatan deployment Tyrant ke Jetson

Tanggal: 7 Oktober 2026. Status: sesi dihentikan sementara atas permintaan operator.

Dokumen ini merangkum pekerjaan yang benar-benar dilaporkan selama sesi, perintah untuk mengulang setup, serta pekerjaan yang belum diuji. Perintah rekonstruksi bukan bukti bahwa setiap baris persis sama pernah dijalankan. Panduan operasional: [cheatsheet terminal](Jetson_Cheatsheet_Terminal.md). Rencana identitas perangkat: [port Teensy dan ESP](Jetson_Rencana_Identitas_Port_Teensy_ESP.md).

## 1. Hasil akhir sesi

- ROS 2 Humble berjalan dalam Docker di Jetson, dengan micro-ROS agent yang dibangun untuk ARM64.
- Package `tyrant_interfaces`, `tyrant_teleop`, dan `tyrant_sim` berhasil dibangun di Jetson.
- Container `tyrant-companion` menjalankan agent dan logger otomatis. Log menunjukkan seluruh 13 topik recorder berhasil di-subscribe.
- Pemeriksaan terakhir: `Status=running RestartCount=0`; pesan health, simple_state, dan IMU dapat diterima dari Teensy.
- Firmware Teensy sudah kembali ke profil produksi `teensy41`, bukan HIL. Operator melaporkan tes heartbeat dan gangguan koneksi berhasil sebelum migrasi launcher otomatis.
- **HWT905 saat pemeriksaan terakhir sengaja tidak dipasang kembali. FullDepth juga belum dipasang.** Data IMU nol dan estimator belum siap sesuai kondisi tersebut, bukan bukti kegagalan Docker.
- Heartbeat tidak dijalankan otomatis oleh container. Status terakhir IDLE (`current_mode: 1`), propulsion tidak diizinkan.
- Belum dikonfirmasi: penutupan dan pembacaan bag dari launcher baru, restart/reboot otomatis, reconnect serial dengan launcher baru, identitas ESP, dan integrasi kode ESP.

## 2. Topologi dan lingkungan

```text
Laptop Ubuntu -- Ethernet/SSH --> Jetson host Ubuntu 18.04 ARM64
                                   └─ Docker: tyrant-companion / ROS Humble
                                       ├─ micro_ros_agent -- USB --> Teensy 4.1
                                       └─ rosbag recorder --> /ws/bags
```

Wi-Fi laptop menyediakan internet untuk Jetson melalui Ethernet sharing. HWT905 normalnya terhubung ke UART Teensy; bukan ke port USB Jetson.

| Item | Nilai yang diamati |
|---|---|
| Host/user Jetson | `nvidia@nvidia-desktop` |
| OS/arsitektur | Ubuntu 18.04.6 LTS / aarch64 |
| Kernel | `4.9.337-tegra` |
| RAM/CPU terlihat Docker | 3.871 GiB / 2 CPU |
| Disk awal | total 59 GB, tersedia sekitar 40 GB |
| Docker | 20.10.21; plugin Compose tidak tersedia |
| Runtime default | runc; runtime nvidia tersedia |
| Keamanan Docker | profil seccomp khusus sudah ada; tidak diubah dalam sesi |
| IP Jetson saat sesi | `10.42.0.246` pada `eth0` |
| Ethernet laptop | `enp109s0`, `10.42.0.1`, profil `jetson-share` |
| Wi-Fi laptop | `wlp0s20f3`, `192.168.18.33`, gateway `192.168.18.1` |
| Container awal | `ros2`, image `ros2-humble-jetson:latest`, command `sleep infinity` |
| Image snapshot akhir | `tyrant-companion:bench` |
| Container akhir | `tyrant-companion` |
| Workspace host → container | `/home/nvidia/ros2_docker/ws` → `/ws` |
| Bag host → container | `/home/nvidia/ros2_docker/ws/bags` → `/ws/bags` |

IP di atas merupakan hasil sesi, bukan jaminan alamat DHCP permanen. Tidak ada instalasi ROS Humble native pada Ubuntu 18.04 host yang dilakukan dalam sesi ini. Konfigurasi awal image `ros2-humble-jetson` sudah tersedia sebelum sesi, sehingga cara pembuatan awalnya tidak direkonstruksi sebagai fakta.

## 3. Pemeriksaan awal

Pada host Jetson, pemeriksaan mencakup `hostname`, `cat /etc/os-release`, `uname -m`, `df -h /`, `docker --version`, `docker info`, `docker ps`, dan `docker images`.

Container awal menggunakan `Network=host` dan bind mount:

```text
/home/nvidia/ros2_docker/ws:/ws
/home/nvidia/ros2_docker/pio_cache:/root/.platformio
/dev:/dev
```

Teensy dikenali melalui `/dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00`, menunjuk `/dev/ttyACM0`. ROS Humble tersedia di `/opt/ros/humble`; package Tyrant awalnya belum ditemukan. `ros2 --version` menghasilkan error argumen: CLI ini tidak menyediakan opsi tersebut. Gunakan `echo "$ROS_DISTRO"` setelah source dan `ros2 pkg list`.

## 4. Copy source dan build Tyrant

Source ROS dari laptop disalin ke workspace Jetson. Pola perintah untuk setup ulang, dari **laptop**:

```bash
scp -r /home/charisto/tyrant-simple/ros2_ws/src/. nvidia@10.42.0.246:/home/nvidia/ros2_docker/ws/src/
```

Tujuan `src` harus sudah tersedia. Jangan salin artefak `build/install/log` laptop x86 ke Jetson ARM64.

Pada **host Jetson**, masuk container awal:

```bash
docker exec -it ros2 bash
```

Di **dalam container**:

```bash
source /opt/ros/humble/setup.bash
cd /ws
colcon build --packages-select tyrant_interfaces tyrant_teleop tyrant_sim --symlink-install
source /ws/install/setup.bash
ros2 pkg list | grep '^tyrant_'
```

Build pertama selesai untuk tiga package, tetapi ada CMake `failed to create symbolic link ... File exists` pada header `tyrant_interfaces`. Artefak install yang bertabrakan dibersihkan pada sesi sebelumnya dan operator kemudian melaporkan build serta daftar package berhasil. Ini konsisten dengan sisa artefak build/install; sumber persis setiap file yang bertabrakan tidak dibuktikan.

Jika mengulang dari source bersih, gunakan terminal baru dan pindahkan artefak lama sebagai backup sebelum build, bukan menghapus source. Jangan lakukan pembersihan workspace aktif ketika agent/logger sedang memakai hasil build-nya.

## 5. Internet sharing: masalah dan pemulihan

Awalnya `getent hosts github.com` gagal di container dan host Jetson. `/etc/resolv.conf` mengarah ke `127.0.0.53`, tetapi daftar DNS upstream systemd-resolved kosong. Ping ke `1.1.1.1` juga gagal: masalah tidak terbatas pada DNS.

Jetson sudah memiliki default route melalui laptop `10.42.0.1`. Laptop dapat mengakses GitHub, `ipv4.method=shared`, dan `net.ipv4.ip_forward=1`. Pemeriksaan iptables menunjukkan policy FORWARD DROP, chain DOCKER-USER tanpa aturan sharing, serta NAT yang terlihat hanya untuk subnet Docker. Setelah forwarding/NAT dan DNS disesuaikan, operator mengonfirmasi internet berhasil.

Perintah pemulihan sementara, **pada laptop**, khusus nama interface/topologi sesi ini (bentuk berikut memeriksa aturan sebelum menambah agar tidak duplikat):

```bash
sudo iptables -C DOCKER-USER -i enp109s0 -o wlp0s20f3 -s 10.42.0.0/24 -j ACCEPT || sudo iptables -I DOCKER-USER 1 -i enp109s0 -o wlp0s20f3 -s 10.42.0.0/24 -j ACCEPT
sudo iptables -C DOCKER-USER -i wlp0s20f3 -o enp109s0 -d 10.42.0.0/24 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT || sudo iptables -I DOCKER-USER 1 -i wlp0s20f3 -o enp109s0 -d 10.42.0.0/24 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -t nat -C POSTROUTING -s 10.42.0.0/24 -o wlp0s20f3 -j MASQUERADE || sudo iptables -t nat -A POSTROUTING -s 10.42.0.0/24 -o wlp0s20f3 -j MASQUERADE
```

Pada **host Jetson**:

```bash
sudo systemd-resolve --interface=eth0 --set-dns=1.1.1.1 --set-dns=8.8.8.8
sudo systemd-resolve --flush-caches
getent hosts github.com
docker exec ros2 getent hosts github.com
```

Aturan dan DNS ini belum dipersistenkan. Jangan mengganti nama interface berdasarkan tebakan: `eth0` ada pada Jetson, sedangkan laptop menggunakan `enp109s0`. Docker dapat mengubah forwarding host; rujukan: [Docker packet filtering](https://docs.docker.com/engine/network/packet-filtering-firewalls/).

## 6. Build micro-ROS agent

`Package not found` terjadi karena agent belum tersedia di overlay Jetson. Menyalin source diperbolehkan, tetapi hasil build laptop tidak dapat langsung dipakai pada ARM64. Setelah internet pulih, source branch Humble agent dan message dependency dibangun di workspace `/ws` yang sama; tidak wajib membuat workspace terpisah bernama `micro_ros_ws`.

Pola reproduksi pada **container**, hanya jika direktori source belum ada:

```bash
source /opt/ros/humble/setup.bash
cd /ws
git clone -b humble https://github.com/micro-ROS/micro-ROS-Agent.git src/micro-ROS-Agent
git clone -b humble https://github.com/micro-ROS/micro_ros_msgs.git src/micro_ros_msgs
rosdep update --rosdistro humble
rosdep install --from-paths src --ignore-src --rosdistro humble -y
CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 \
colcon build --packages-up-to micro_ros_agent --executor sequential \
  --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source /ws/install/setup.bash
ros2 pkg prefix micro_ros_agent
```

Tool build yang diperlukan meliputi git, CMake, compiler, rosdep, dan colcon; Dockerfile repo mencantumkan dependency untuk build bersih. Agent memakai superbuild XRCE agent v2.4.2 sebagaimana log sesi. Build serial membatasi pemakaian resource Nano.

| Package | Hasil sesi |
|---|---|
| `tyrant_interfaces` | Berhasil setelah konflik artefak diselesaikan |
| `tyrant_teleop` | Berhasil dibangun; controller di Jetson belum diuji dalam sesi ini |
| `tyrant_sim` | Berhasil dibangun; bukan plant yang dijalankan pada deployment produksi akhir |
| `micro_ros_msgs` | Berhasil, 1 menit 22 detik |
| `micro_ros_agent` | Berhasil, 15 menit 44 detik |
| Total build dua package micro-ROS | 17 menit 8 detik |

Warning `AMENT_CMAKE_SYMLINK_INSTALL` unused dan perbedaan nama `tinyxml2`/`TinyXML2` tidak menggagalkan build. Ringkasan menunjukkan dua package finished, tanpa failed. Source resmi: [micro-ROS Agent Humble](https://github.com/micro-ROS/micro-ROS-Agent/tree/humble).

## 7. Agent manual dan bag bench

Agent awal berjalan dalam container `ros2`, dengan stable serial path `/dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00`. Operator mengonfirmasi heartbeat dan tes gangguan koneksi berhasil. Jangan jalankan agent manual bersamaan dengan agent otomatis pada serial yang sama.

Bag `jetson_bench_20261007_153516`:

| Parameter/topik | Hasil |
|---|---|
| Durasi / jumlah pesan | 26.052120039 detik / 672 |
| Storage / ukuran | sqlite3 / 79.0 KiB |
| `/tyrant/system/health` | 129 pesan |
| `/tyrant/simple_state` | 129 pesan |
| `/tyrant/sensors/imu` | 129 pesan |
| `/tyrant/mode/status` | 259 pesan |
| `/tyrant/communication/diagnostics` | 26 pesan |

Jumlah tersebut setara rata-rata sekitar 5/5/5/10/1 Hz sepanjang bag; bukan pengukuran jitter atau bukti tidak ada packet loss.

## 8. Migrasi ke agent + logger otomatis

File lokal: `companion/jetson/start_container.sh`, `entrypoint.sh`, `run_companion.py`, `Dockerfile`, dan tes supervisor. Empat tes lokal dengan proses tiruan lulus: shutdown, agent gagal, serial hilang, dan ruang disk kurang. Build Dockerfile bersih belum dijalankan di Jetson.

Dari **laptop**:

```bash
scp -r /home/charisto/tyrant-simple/companion/jetson nvidia@10.42.0.246:/home/nvidia/ros2_docker/ws/
```

Pada **host Jetson**, setelah recorder manual dihentikan:

```bash
docker update --restart=no ros2
docker stop -t 30 ros2
docker commit ros2 tyrant-companion:bench
bash /home/nvidia/ros2_docker/ws/jetson/start_container.sh
```

Snapshot berhasil dengan image ID `sha256:3fceeb9de465a32bb38bacba8ad91e4f6ceea4f94ef89d3be71594570f52d61d`. Ini menghindari build ulang agent. **Snapshot tidak berisi bind mount `/ws`**; source, build, install, dan bags tetap memerlukan direktori host tersebut. Mount cache PlatformIO container lama tidak diperlukan oleh launcher agent/logger baru.

Konfigurasi launcher: host network, `--init`, restart `unless-stopped`, stop timeout 30 detik, log maksimal 3 × 10 MB, mount workspace `/ws`, script `/deployment` read-only, perangkat `/host-dev`, serta izin serial ACM major 166. Recorder membagi file tiap 300 detik dan menghentikan supervisor jika ruang kosong kurang dari 512 MiB. Bag tidak dihapus otomatis. Nama sesi memakai UTC dan ID unik.

Container baru berhasil dibuat; log menunjukkan publisher/subscriber Teensy terbentuk dan semua 13 topik logger berhasil di-subscribe. Status terakhir `running`, restart count 0. Subscribed tidak sama dengan verifikasi isi bag yang sudah ditutup.

## 9. Interpretasi telemetry terakhir

```text
communication_healthy: false
estimator_ready: false
autonomy_ready: false
propulsion_allowed: false
current_mode: 1
host_heartbeat_age_ms: 4294967295
```

Mode 1 adalah IDLE, bukan SAFE (SAFE=4). Umur heartbeat maksimum menunjukkan belum ada heartbeat host diterima. Agent mengangkut telemetry tetapi tidak otomatis menerbitkan heartbeat aplikasi. Jangan menambahkan heartbeat permanen yang dapat menyamarkan matinya teleop.

IMU menunjukkan INITIALIZING (`sensor_state=1`), `bytes_received=0`, `samples_produced=0`, dan `valid=false`. Simple state belum valid. Operator mengonfirmasi HWT905 sedang dilepas; FullDepth juga belum dipasang. Karena itu sesi ditutup tanpa menuntut estimator ready. Saat sensor dipasang kembali, firmware menggunakan HWT905 di `Serial1` pada 9600 baud.

## 10. Pekerjaan berikutnya

1. Identifikasi ESP dan Teensy berdasarkan serial USB/ID perangkat, bukan nomor `ttyACM0`/`ttyUSB0`. Teensy sudah memakai by-id; ESP belum diinventarisasi. Lihat dokumen rencana port.
2. Tutup bag dari launcher baru dan periksa metadata/jumlah pesan.
3. Uji restart container, reconnect Teensy, dan reboot Jetson; pastikan agent pulih dan muncul sesi bag baru.
4. Tentukan konfigurasi internet sharing/DNS permanen jika dibutuhkan.
5. Pasang kembali HWT dan verifikasi IMU saat melanjutkan hardware; FullDepth tetap pending.
6. Tinjau protokol dan kebutuhan port kode ESP teman sebelum integrasi.

Tidak ada klaim validasi propulsion fisik, FullDepth, dinamika kendaraan di air, atau seluruh kode ESP dari sesi ini.

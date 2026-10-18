# Deployment Jetson: agent dan logger

## Baseline 7 Oktober 2026

Host `nvidia@nvidia-desktop`: Ubuntu 18.04 ARM64, Docker 20.10.21 tanpa Compose. ROS 2 Humble berjalan dalam container `ros2`. Workspace host `/home/nvidia/ros2_docker/ws` terpasang sebagai `/ws`.

Operator sudah melaporkan build package Tyrant dan micro-ROS agent berhasil, firmware kembali ke `teensy41`, serta tes heartbeat dan gangguan koneksi berhasil. FullDepth belum dipasang.

Bag `jetson_bench_20261007_153516` merekam 672 pesan selama 26.052 detik: health, simple_state, dan IMU masing-masing 129; mode 259; diagnostics 26. Ini membuktikan perekaman kelima topik pada sesi tersebut, bukan validasi seluruh nilai sensor atau kestabilan jangka panjang.

Startup launcher telah diverifikasi pada Jetson: agent membentuk publisher/subscriber, recorder subscribe seluruh 13 topik, dan pemeriksaan terakhir menunjukkan `running`, `RestartCount=0`. Tes restart/reboot dan pembacaan bag dari launcher baru masih pending. Riwayat lengkap dan cheatsheet tersedia di [catatan sesi](dokumentasi%20dan%20PRD/Jetson_Setup_dan_Catatan_Deployment_2026-10-07.md).

Pada akhir sesi HWT905 sengaja dilepas dan FullDepth belum dipasang. IMU belum menerima byte, sehingga estimator belum siap; ini sesuai kondisi hardware yang dikonfirmasi operator.

## 1. Salin dari laptop

Jalankan pada **terminal laptop**:

```bash
scp -r /home/charisto/tyrant-simple/companion/jetson nvidia@10.42.0.246:/home/nvidia/ros2_docker/ws/
```

Sesuaikan IP jika DHCP berubah. Tidak perlu menyalin ulang workspace micro-ROS atau hasil build dari laptop.

## 2. Buat container dari lingkungan yang sudah berhasil

Hentikan recorder manual dengan Ctrl+C dahulu agar metadata selesai ditulis. Lalu pada **host Jetson melalui SSH**, prompt `nvidia@nvidia-desktop`, bukan root di container:

```bash
docker update --restart=no ros2
docker stop -t 30 ros2
docker commit ros2 tyrant-companion:bench
bash /home/nvidia/ros2_docker/ws/jetson/start_container.sh
```

Snapshot menyimpan dependency di filesystem container. **Bind mount `/ws` tidak masuk image**: source, hasil build ARM64, dan bag tetap berada di host. Pertahankan `/ws/src`, `/ws/build`, dan `/ws/install` karena build memakai symlink. Container lama tetap tersedia untuk rollback.

Container baru bernama `tyrant-companion`, memakai jaringan host dan mount `/dev` sebagai `/host-dev`. Izin cgroup serial ACM major 166 diberikan tanpa privileged mode. Path bawaan Teensy adalah `/host-dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00`. Jika agent melaporkan permission denied, periksa log dan permission perangkat sebelum mengubah privilege container.

## 3. Verifikasi

Pada **host Jetson**:

```bash
docker ps --filter name=tyrant-companion
docker logs --tail 80 tyrant-companion
docker exec tyrant-companion bash -lc 'source /opt/ros/humble/setup.bash; source /ws/install/setup.bash; ros2 node list'
docker exec tyrant-companion bash -lc 'source /opt/ros/humble/setup.bash; source /ws/install/setup.bash; timeout 15 ros2 topic echo /tyrant/system/health --once'
```

Harapan: agent membentuk sesi, `/tyrant_teensy` muncul, dan health diterima. Status container `Up` saja belum membuktikan koneksi ROS. Saat serial belum terpasang, launcher menunggu perangkat.

**Heartbeat tidak otomatis dijalankan.** Teleop atau sesi bench operator memiliki heartbeat sendiri. Tanpa heartbeat, health dapat menunjukkan komunikasi tidak sehat; kondisi terakhir yang diamati adalah IDLE (`current_mode=1`) dengan propulsion tidak diizinkan, bukan SAFE (`4`). Launcher tidak meminta mode atau mengaktifkan propulsion.

Biarkan merekam sekitar 30 detik, lalu pada **host Jetson**:

```bash
docker stop -t 30 tyrant-companion
latest_bag=$(ls -dt /home/nvidia/ros2_docker/ws/bags/jetson_* | head -n 1)
docker run --rm --network none \
  --mount type=bind,src=/home/nvidia/ros2_docker/ws,dst=/ws,readonly \
  --entrypoint /bin/bash tyrant-companion:bench -lc \
  "source /opt/ros/humble/setup.bash; source /ws/install/setup.bash; ros2 bag info /ws/bags/$(basename "$latest_bag")"
docker start tyrant-companion
```

Pastikan metadata dapat dibaca dan topik aktif memiliki pesan. Topik opsional yang belum diterbitkan tidak harus muncul. Pemeriksaan bag memakai container sementara tanpa agent.

## 4. Restart dan reboot

Pada **host Jetson**:

```bash
docker restart -t 30 tyrant-companion
docker logs --tail 80 tyrant-companion
```

Agent harus tersambung kembali dan logger membuat sesi baru. Cabut/pasang Teensy menutup sesi rekaman lama, memicu restart container, lalu menunggu serial kembali. Perilaku reconnect ini perlu dikonfirmasi pada Jetson.

Untuk uji reboot, pastikan container sedang berjalan dan Docker aktif saat boot (`systemctl is-enabled docker`; jika belum, `sudo systemctl enable docker`). Jalankan `sudo reboot` pada host Jetson. SSH terputus; setelah boot sambungkan kembali dan ulangi verifikasi.

Policy `unless-stopped` memulai kembali container yang berjalan sebelum reboot. Container yang sengaja dihentikan dengan `docker stop` tetap berhenti sampai `docker start`. Tidak perlu service systemd tambahan untuk container. Rujukan: [restart policy Docker](https://docs.docker.com/engine/containers/start-containers-automatically/).

Aturan internet sharing iptables laptop dan DNS sementara Jetson belum dipersistenkan oleh launcher. Internet mungkin perlu dipulihkan setelah reboot. Agent dan recorder yang telah terpasang tidak membutuhkan internet untuk operasi lokal.

## 5. Penyimpanan dan rollback

Bag tersimpan pada host di `/home/nvidia/ros2_docker/ws/bags`. Nama sesi memakai waktu UTC berakhiran `Z` dan ID unik. Bag dipecah setiap 300 detik. Tidak ada penghapusan otomatis: arsipkan rekaman berkala. Jika ruang kosong kurang dari 512 MiB, supervisor berhenti dan startup berikutnya ditolak sampai ruang tersedia. Log Docker dibatasi tiga file masing-masing 10 MB.

Untuk kembali ke setup manual, pada **host Jetson**:

```bash
docker stop -t 30 tyrant-companion
docker start ros2
docker exec -it ros2 bash
```

Container lama menjalankan `sleep infinity`; source workspace dan jalankan agent manual seperti sebelumnya. Jangan jalankan dua agent pada serial yang sama.

## Deployment payload dan host misi berikutnya

Prosedur pengujian dual-agent, heartbeat host, dan pencatat misi di workspace
ARM64 terpisah tersedia pada [panduan deployment payload dan misi](jetson_payload_mission_deployment.md).
Supervisor lama di halaman ini tetap hanya menjalankan agent Teensy dan rosbag.

## 6. Build image bersih (opsional)

Build ini lebih lama dan belum diuji pada Jetson. Dari root checkout repo pada **Jetson ARM64** yang memiliki internet:

```bash
docker build --network host -f companion/jetson/Dockerfile -t tyrant-companion:humble .
```

Untuk pembuatan container pertama dari image tersebut:

```bash
TYRANT_IMAGE=tyrant-companion:humble \
TYRANT_SETUP=/opt/tyrant_ws/install/setup.bash \
bash companion/jetson/start_container.sh
```

Launcher menolak jika container bernama `tyrant-companion` sudah ada; ini bukan prosedur upgrade container aktif. Dockerfile menyimpan workspace di `/opt/tyrant_ws`. Saat memeriksa ROS pada image ini, source `/opt/tyrant_ws/install/setup.bash` menggantikan `/ws/install/setup.bash`.

Tag base dan branch Humble dapat berubah. Setelah kualifikasi, pin digest base dan commit source melalui build args `MICRO_ROS_AGENT_REF` dan `MICRO_ROS_MSGS_REF`.

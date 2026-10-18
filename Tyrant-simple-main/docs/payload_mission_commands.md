# Perintah harian payload + misi

Untuk Jetson yang sudah memakai container autostart `tyrant-mission`, gunakan
[cheatsheet Jetson](jetson_autostart.md#perintah-harian--terminal-ssh-host-jetson).
Kedua agent, heartbeat, dan plant HIL sudah aktif pada konfigurasi itu.
Perintah laptop di bawah digunakan saat container tersebut berhenti.

Persiapan setiap terminal laptop:

```bash
source /opt/ros/humble/setup.bash
source /home/charisto/microros_ws/install/setup.bash
source /home/charisto/tyrant-simple/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
```

Dengan Teensy HIL dan ESP simulasi yang sudah di-upload, terminal terpisah:

```bash
ros2 launch tyrant_sim hil_plant.launch.py
```

```bash
ros2 launch tyrant_mission_host mission_host.launch.py start_agents:=true \
  output_dir:=/home/charisto/tyrant-simple/ros2_ws/bags/missions
```

Gunakan `start_agents:=false` bila kedua agent sudah dijalankan sendiri. Host
mengirim dua heartbeat; hentikan publisher heartbeat dan teleop lain pada uji ini.

Cek, mulai, pantau, dan hentikan:

```bash
ros2 topic echo /tyrant/system/health --once
ros2 topic echo /tyrant/payload_sim/communication/diagnostics --once
ros2 service call /tyrant/host/mission/start std_srvs/srv/Trigger '{}'
ros2 topic echo /tyrant/host/mission/status
```

```bash
ros2 service call /tyrant/host/mission/stop std_srvs/srv/Trigger '{}'
```

Rekaman manual ketika tidak ada misi aktif:

```bash
ros2 service call /tyrant/host/recording/start std_srvs/srv/Trigger '{}'
ros2 service call /tyrant/host/recording/stop std_srvs/srv/Trigger '{}'
```

Service mengembalikan folder sesi; periksa bag:

```bash
ros2 bag info /path/sesi/bag
```

Parameter rencana: edit YAML sendiri lalu berikan `plan:=/path/misi.yaml`.

Uji sampling ±0,2 m yang disiapkan pada 9 Oktober, setelah menghentikan launcher
host lama (plant boleh tetap berjalan):

```bash
ros2 launch tyrant_mission_host mission_host.launch.py start_agents:=true \
  plan:=/home/charisto/tyrant-simple/ros2_ws/src/tyrant_mission_host/config/two_depth_hil_sampling_020m.yaml \
  output_dir:=/home/charisto/tyrant-simple/ros2_ws/bags/missions
```

Jika agent dijalankan terpisah dan masih aktif, gunakan `start_agents:=false`.
Perubahan file rencana baru tidak memerlukan upload firmware atau rebuild karena
path source YAML diberikan secara langsung. Targetnya `sampling_started`, counts
minimal 3 per sensor pada masing-masing titik, dan `all_sampling_points_complete=true`.
Ini belum hasil pengujian; toleransi rencana awal tetap ±0,1 m.

Detail profil firmware, batas pengujian, parameter dan format keluaran:
[panduan lengkap](payload_mission_host.md).

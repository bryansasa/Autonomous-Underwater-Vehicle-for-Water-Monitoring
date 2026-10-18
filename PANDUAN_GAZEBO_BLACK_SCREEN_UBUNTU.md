# PANDUAN PENYELESAIAN GAZEBO BLACK SCREEN & SETUP SIMULASI (UBUNTU / ROS 2)
**Proyek: Simulasi Robot ROV Tyrant-AQ & Subsistem Waduk Saguling**

---

## 📌 Ringkasan Masalah
Layar hitam (*black screen / viewport kosong*) saat menjalankan Gazebo di Ubuntu umumnya terjadi ketika proses inti simulasi berjalan di background, namun engine rendering grafis (**OGRE 2 / OpenGL**) gagal menginisialisasi konteks 3D pada GPU atau sistem window Ubuntu.

Kasus ini sering terjadi pada:
1. GPU terintegrasi (Intel Iris Xe/UHD, AMD Radeon bawaan CPU).
2. Laptop dual GPU (Intel + NVIDIA) dengan driver offload yang belum sinkron.
3. Mesin virtual atau WSL2 (Windows Subsystem for Linux).
4. Cache konfigurasi GUI Gazebo yang tersimpan dalam keadaan *corrupt*.

---

## 🔍 Langkah Cepat: Cek Log Error Asli (Diagnosis)

Jalankan Gazebo dengan mode **verbose level 4** di terminal:

```bash
# Untuk Gazebo Sim modern (GZ Sim):
gz sim -v 4

# Atau jika menggunakan Gazebo Classic:
gazebo --verbose
```

Perhatikan pesan berwarna merah / `[Err]`:
* `[GUI] [Err] ... Ogre2RenderEngine` ➔ Masalah **Render Engine OGRE2** (Paling sering).
* `Failed to create OpenGL context` / `libGL error` ➔ Masalah **Driver GPU / OpenGL**.
* Stuck pada `Waiting for master...` atau downloading ➔ Masalah **Download Model OSRF Timeout**.

---

## 🛠️ Solusi 1: Ganti Render Engine ke OGRE 1 (Rekomendasi Utama)

Gazebo Sim modern menggunakan OGRE2 secara default yang sangat rentan crash jika hardware OpenGL tidak sempurna. Solusi paling ampuh adalah beralih ke engine **OGRE 1**:

### Jalankan Langsung di Terminal:
```bash
gz sim --render-engine ogre
```

### Solusi Permanen untuk ROS 2 Launch File (`simulasi_rov_gazebo.launch.py`):
Agar saat menjalankan launch file ROS 2 tidak perlu mengubah script Python, pasang environment variable berikut ke bash profile:

```bash
echo "export GZ_RENDERING_ENGINE=ogre" >> ~/.bashrc
source ~/.bashrc
```

---

## 🛠️ Solusi 2: Laptop Dual GPU (NVIDIA + Intel)

Banyak laptop menggunakan NVIDIA discrete GPU + Intel integrated GPU:

### 1. Pastikan Driver NVIDIA Terdeteksi:
```bash
nvidia-smi
```
*(Jika driver belum ada: jalankan `sudo ubuntu-drivers autoinstall` lalu `sudo reboot`)*.

### 2. Paksa Gazebo Berjalan di GPU NVIDIA:
```bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia gz sim
```

---

## 🛠️ Solusi 3: Jika Menjalankan di WSL2 (Windows Subsystem for Linux)

1. **Update WSL di Windows (PowerShell Run as Admin):**
   ```powershell
   wsl --update
   ```
2. **Gunakan Software Rendering (Fallback CPU di Terminal Ubuntu WSL):**
   ```bash
   export LIBGL_ALWAYS_SOFTWARE=1
   gz sim
   ```
3. **Pilih GPU NVIDIA untuk Direct3D 12:**
   ```bash
   export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
   ```

---

## 🛠️ Solusi 4: Reset Cache GUI Gazebo yang Corrupt

Jika Gazebo pernah crash atau ditutup paksa (`Ctrl+C`), setting visualisasinya sering corrupt. Reset konfigurasinya dengan:

```bash
# Untuk Gazebo Sim modern:
rm -rf ~/.gz/sim/

# Untuk Ignition Gazebo:
rm -rf ~/.ignition/gazebo/

# Untuk Gazebo Classic:
rm -rf ~/.gazebo/gui.ini
```

---

## 🛠️ Solusi 5: Khusus Jika Menggunakan Gazebo Classic (`gazebo`)

Jika menjalankan Gazebo Classic (`gazebo 11`), layar hitam disebabkan Gazebo stuck mendownload model default dari server OSRF yang lemot/terblokir.

Pasang model secara lokal:
```bash
mkdir -p ~/.gazebo/models
git clone https://github.com/osrf/gazebo_models.git ~/.gazebo/models
```

---

## 🚀 Prosedur Menjalankan Simulasi ROV Tyrant-AQ di Ubuntu

Berikut urutan perintah di terminal Ubuntu untuk workspace Anda:

```bash
# 1. Masuk ke workspace ROS 2
cd ~/ros2_ws

# 2. Source ROS 2 (sesuaikan dengan distro: humble/jazzy)
source /opt/ros/$ROS_DISTRO/setup.bash

# 3. Build paket simulasi
colcon build --packages-select tyrant_gazebo_sim
source install/setup.bash

# 4. Pastikan Render Engine diset ke OGRE 1
export GZ_RENDERING_ENGINE=ogre

# 5. Jalankan Simulasi Penuh (Gazebo + ROV + Waduk Saguling + EA-DSRA)
ros2 launch tyrant_gazebo_sim simulasi_rov_gazebo.launch.py
```

### Membuka Kontrol Manual Keyboard (Teleop di Terminal Baru):
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 run tyrant_gazebo_sim rov_teleop_key
```

---

## 📋 Tabel Perintah Cepat (Cheat-Sheet)

| Kebutuhan | Perintah di Terminal Ubuntu |
| :--- | :--- |
| **Buka GZ Sim tanpa black screen** | `gz sim --render-engine ogre` |
| **Simpan permanen engine OGRE 1** | `echo "export GZ_RENDERING_ENGINE=ogre" >> ~/.bashrc` |
| **Cek log detail error render** | `gz sim -v 4` |
| **Paksa GPU NVIDIA (PRIME offload)** | `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia gz sim` |
| **Reset cache GUI Gazebo** | `rm -rf ~/.gz/sim/` |
| **Render CPU aman (WSL2/VM)** | `export LIBGL_ALWAYS_SOFTWARE=1` |
| **Teleop ROV via keyboard** | `ros2 run tyrant_gazebo_sim rov_teleop_key` |

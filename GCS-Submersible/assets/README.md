# Aset Model 3D & Foto Tyrant-AQ AUV

Folder ini digunakan untuk menyimpan file model 3D atau gambar fisik robot nyata.

### Cara Menampilkan Model CAD 3D Real Robot di GCS:
1. Buka model assembly robot Anda di **SolidWorks**, **Autodesk Inventor**, atau **Fusion 360**.
2. Pilih menu **File > Save As / Export** dan pilih format **STL (`.stl`)**.
3. Beri nama file: `robot_model.stl` (atau `model.stl`).
4. Letakkan file tersebut di dalam folder `assets/` ini.
5. Saat aplikasi GCS dijalankan, widget 3D di kiri atas akan otomatis memuat file CAD asli robot Anda dan merendernya dalam bentuk 3D solid yang berotasi dinamis mengikuti sensor IMU (Roll, Pitch, Yaw).

> **Catatan:** Jika belum ada file STL eksternal di folder ini, GCS otomatis menggunakan model 3D bawaan (*Solid-Shaded Twin-Hull AUV*).

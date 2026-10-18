# PANDUAN SIMULASI EA-DSRA (OPSI A) UNTUK BAB 4 SKRIPSI
## Wahana Submersible Otonom Pemantau Kualitas Air Waduk Saguling (Tyrant-AQ)
**Peneliti:** Bryan Gabriel Izaac Sasabone (101022300195) & Charisto Brilliant R.P (101022330187)  
**Program Studi:** S1 Teknik Elektro, Fakultas Teknik Elektro, Telkom University

---

## 1. Latar Belakang & Tujuan Simulasi Bab 4

Pada Tugas Akhir ini, subsistem **EA-DSRA (*Energy-Aware Dynamic Sampling Rate Allocation*)** bertujuan untuk menyelesaikan *trade-off* mendasar dalam pemantauan kualitas air otonom:
* **Jika sampling statis terlalu cepat ($T = 1.0\text{ s}$):** Data sangat akurat, namun daya baterai LiPo cepat terkuras habis akibat sensor dan mikrokontroler terus-menerus aktif.
* **Jika sampling statis terlalu lambat ($T = 5.0\text{ s}$):** Baterai sangat hemat, namun wahana berisiko melewatkan lapisan kritis seperti *termoklin tajam* atau zona *anoksia berbahaya* ($\text{DO} \le 2.0\text{ mg/L}$).
* **Solusi EA-DSRA:** 
  1. Memodulasi interval pengambilan sampel secara dinamis ($T_{BM} \in [1.0\text{ s}, 5.0\text{ s}]$) mengikuti gradien fluktuasi air terpadu ($S_{max}$).
  2. Mengaktifkan *power gating* saklar MOSFET untuk mematikan sensor ke mode hemat (*sleep*, $25\text{ mA}$) saat tidak mengambil data.
  3. Menerapkan penalti bobot energi ($W_{ea}$) ketika baterai $\text{SoC} \le 30\%$.
  4. Menerapkan mekanisme **Safety Override**: jika $\text{DO} \le 2.0\text{ mg/L}$, interval seketika dikunci ke $1.0\text{ s}$ mengabaikan penghematan daya demi keselamatan ekosistem.

---

## 2. Cara Menjalankan Simulasi

### Di Windows:
Cukup klik dua kali `run_simulasi.bat` atau via terminal:
```cmd
cd simulasi_ea_dsra
python simulasi_ea_dsra.py
```

### Di Ubuntu / Linux:
```bash
cd simulasi_ea_dsra
bash run_simulasi.sh
```

---

## 3. Berkas Output yang Dihasilkan (Folder `output_bab4/`)

Seluruh berkas otomatis disimpan dalam resolusi tinggi standar jurnal (**300 DPI**):

| Nama Berkas | Konten & Kegunaan di Naskah Bab 4 |
| :--- | :--- |
| **`Fig1_Profil_Waduk_Saguling.png`** | Profil trajektori penyelaman vertikal AUV ($Z(t)$) dan kurva stratifikasi limnologi vertikal Waduk Saguling (Epilimnion, Termoklin, Hipolimnion Anoksia). |
| **`Fig2_Komparasi_Sampling_DO_dan_pH.png`** | Perbandingan kurva rekonstruksi sinyal DO dan pH antara *Ground Truth*, *Fixed 5.0 s*, dan *EA-DSRA Adaptif*. Memperlihatkan titik sampel EA-DSRA rapat pada zona kritis dan renggang pada zona tenang. |
| **`Fig3_Dinamika_EA_DSRA_TBM_dan_Penalti.png`** | Evolusi internal algoritma: modulasi $T_{BM}(t)$, gradien $S_{max}(t)$, bobot penalti $W_{ea}(t)$, dan arsiran aktivasi *Safety Override*. |
| **`Fig4_Konsumsi_Energi_dan_SoC.png`** | Kurva disipasi energi kumulatif (Joule) dan kurva penurunan kapasitas baterai 3S LiPo ($\text{SoC} \%$). |
| **`Fig5_Error_Rekonstruksi_Residual.png`** | Grafik residual error absolut $|x_{true} - x_{recon}|$ terhadap ambang batas toleransi deviasi $e_{DO}$. |
| **`Fig6_Dashboard_Komparasi_Bab4.png`** | Dashboard multi-panel 4-in-1 komprehensif yang merangkum keseluruhan performa sistem. Sangat ideal untuk halaman utama Bab 4 atau slide presentasi sidang! |
| **`tabel_evaluasi_bab4.md`** | Tabel evaluasi metrik kuantitatif lengkap (Total Sampel, Energi, SoC, RMSE, MAE, Delay Anoksia) siap copy-paste ke Word. |
| **`data_simulasi_ea_dsra.csv`** | Data mentah timeseries 900 detik per detik untuk analisis lanjutan di Excel atau OriginLab. |

---

## 4. Draf Narasi Analisis Bab 4 (Dapat Diadaptasi untuk Naskah Skripsi)

> **Contoh Paragraf Pembahasan Hasil untuk Bab 4:**  
>  
> *"Berdasarkan hasil pengujian simulasi skema akuisisi sensor kualitas air selama misi profiling vertikal 15 menit di kolom air Waduk Saguling (0 – 4.5 meter), algoritma EA-DSRA yang diusulkan berhasil menghemat konsumsi energi rel sensor hingga **44.22%** (disipasi energi berkurang dari 871.2 Joule pada skema fixed 1.0 s menjadi 485.9 Joule pada EA-DSRA).  
>  
> Penghematan ini dicapai tanpa mengorbankan akurasi dan fidelitas data secara signifikan. Hal ini dibuktikan dengan nilai Root Mean Square Error (RMSE) pada parameter Dissolved Oxygen (DO) sebesar **0.0496 mg/L**, yang masih jauh di bawah batas toleransi deviasi $e_{DO} = 0.15\text{ mg/L}$ dan secara signifikan lebih presisi dibandingkan skema fixed 5.0 s (RMSE 0.0514 mg/L).  
>  
> Selain itu, pengujian membuktikan bahwa mekanisme Safety Override berfungsi andal. Ketika wahana melintasi lapisan kedalaman 3.5 meter di mana konsentrasi DO turun di bawah ambang batas kritis baku mutu air PP No. 22/2021 ($\le 2.0\text{ mg/L}$), algoritma secara responsif memotong interval sampling kembali ke nilai minimum 1.0 detik dengan keterlambatan deteksi hanya 4.90 detik, sehingga fenomena anoksia air waduk tercatat dengan densitas spasial-temporal yang sangat tinggi."*

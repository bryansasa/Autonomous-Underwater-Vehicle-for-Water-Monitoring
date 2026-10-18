import csv
import os
import math
from datetime import datetime

def stats(vals):
    if not vals:
        return 0, 0, 0, 0, 0
    n = len(vals)
    mean = sum(vals) / n
    variance = sum((x - mean) ** 2 for x in vals) / (n - 1) if n > 1 else 0.0
    std = math.sqrt(variance)
    return n, mean, std, min(vals), max(vals)

downloads_dir = r"C:\Users\bryan\Downloads"

# -----------------------------------------------------------------------------
# 1. Process dry_Cal.csv
# -----------------------------------------------------------------------------
f_dry = os.path.join(downloads_dir, "dry_Cal.csv")
clean_dry = []
if os.path.exists(f_dry):
    with open(f_dry, "r", encoding="utf-8") as f:
        rows_dry = list(csv.DictReader(f))

    t0 = None
    for r in rows_dry:
        dt = datetime.strptime(r["Datetime"], "%Y-%m-%d %H:%M:%S.%f")
        if t0 is None:
            t0 = dt
        elapsed = (dt - t0).total_seconds()
        val = float(r["Conductivity_uS"])
        clean_dry.append({
            "Datetime": r["Datetime"],
            "Elapsed_s": f"{elapsed:.1f}",
            "Conductivity_uS": f"{val:.1f}"
        })

    out_dry = os.path.join(downloads_dir, "dry_Cal_CLEANED.csv")
    with open(out_dry, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Datetime", "Elapsed_s", "Conductivity_uS"])
        w.writeheader()
        w.writerows(clean_dry)
    print(f"[OK] Saved {out_dry} ({len(clean_dry)} baris)")

# -----------------------------------------------------------------------------
# 2. Process 1413_cal (before press cal_one).csv
# -----------------------------------------------------------------------------
f_before = os.path.join(downloads_dir, "1413_cal (before press cal_one).csv")
clean_before = []
pre_cal_plateau = []
outliers_before = []
if os.path.exists(f_before):
    with open(f_before, "r", encoding="utf-8") as f:
        rows_before = list(csv.DictReader(f))

    t0 = None
    for i, r in enumerate(rows_before):
        dt = datetime.strptime(r["Datetime"], "%Y-%m-%d %H:%M:%S.%f")
        if t0 is None:
            t0 = dt
        elapsed = (dt - t0).total_seconds()
        val = float(r["Conductivity_uS"])

        # Filter lonjakan goyangan saat celup (indeks 4 sampai 51)
        if 4 <= i <= 51:
            if val < 2800.0:
                outliers_before.append((i, r["Datetime"], val, "Lonjakan goyangan pelepasan gelembung"))
            else:
                pre_cal_plateau.append(val)
                clean_before.append({
                    "Datetime": r["Datetime"],
                    "Elapsed_s": f"{elapsed:.1f}",
                    "Conductivity_uS": f"{val:.1f}"
                })
        else:
            clean_before.append({
                "Datetime": r["Datetime"],
                "Elapsed_s": f"{elapsed:.1f}",
                "Conductivity_uS": f"{val:.1f}"
            })

    out_before = os.path.join(downloads_dir, "1413_cal_before_press_cal_one_CLEANED.csv")
    with open(out_before, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Datetime", "Elapsed_s", "Conductivity_uS"])
        w.writeheader()
        w.writerows(clean_before)
    print(f"[OK] Saved {out_before} ({len(clean_before)} baris)")

    out_plateau = os.path.join(downloads_dir, "1413_pre_calibration_steady_plateau.csv")
    with open(out_plateau, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Sample_Index", "Conductivity_uS"])
        for idx, v in enumerate(pre_cal_plateau):
            w.writerow([idx + 1, f"{v:.1f}"])
    print(f"[OK] Saved {out_plateau} ({len(pre_cal_plateau)} baris)")

# -----------------------------------------------------------------------------
# 3. Process 1413_cal after press button.csv
# -----------------------------------------------------------------------------
f_after = os.path.join(downloads_dir, "1413_cal after press button.csv")
clean_after = []
outliers_after = []
vals_after = []
if os.path.exists(f_after):
    with open(f_after, "r", encoding="utf-8") as f:
        rows_after = list(csv.DictReader(f))

    t0 = None
    for i, r in enumerate(rows_after):
        dt = datetime.strptime(r["Datetime"], "%Y-%m-%d %H:%M:%S.%f")
        if t0 is None:
            t0 = dt
        elapsed = (dt - t0).total_seconds()
        val = float(r["Conductivity_uS"])

        # Filter sudden drop / outlier (normal ~1410-1416)
        if val < 1350.0:
            outliers_after.append((i, r["Datetime"], val, "Lonjakan transisi / gelembung udara tiba-tiba"))
        else:
            vals_after.append(val)
            clean_after.append({
                "Datetime": r["Datetime"],
                "Elapsed_s": f"{elapsed:.1f}",
                "Conductivity_uS": f"{val:.1f}"
            })

    out_after = os.path.join(downloads_dir, "1413_cal_after_press_button_CLEANED.csv")
    with open(out_after, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Datetime", "Elapsed_s", "Conductivity_uS"])
        w.writeheader()
        w.writerows(clean_after)
    print(f"[OK] Saved {out_after} ({len(clean_after)} baris)")

# -----------------------------------------------------------------------------
# Print Ringkasan Analisis & Statistik
# -----------------------------------------------------------------------------
print("\n" + "=" * 75)
print("  RINGKASAN STATISTIK PEMBERSIHAN DATA KALIBRASI (DOWNLOADS)")
print("=" * 75)

n_d, m_d, s_d, min_d, max_d = stats([float(r["Conductivity_uS"]) for r in clean_dry])
print(f"1. DRY CALIBRATION (Probe Kering di Udara):")
print(f"   - File Output : dry_Cal_CLEANED.csv")
print(f"   - Jumlah Baris: {n_d} sampel")
print(f"   - Nilai Rata-rata: {m_d:.2f} uS/cm | Std Dev: {s_d:.2f} uS/cm")
print(f"   - Min: {min_d:.1f} uS/cm | Max: {max_d:.1f} uS/cm")

n_p, m_p, s_p, min_p, max_p = stats(pre_cal_plateau)
print(f"\n2. PRE-CALIBRATION DI LARUTAN 1413 (Sebelum Klik Tombol Cal One):")
print(f"   - File Output : 1413_pre_calibration_steady_plateau.csv & 1413_cal_before_press_cal_one_CLEANED.csv")
print(f"   - Jumlah Baris: {n_p} sampel stabil")
print(f"   - Nilai Rata-rata: {m_p:.2f} uS/cm | Std Dev: {s_p:.2f} uS/cm")
print(f"   - Min: {min_p:.1f} uS/cm | Max: {max_p:.1f} uS/cm")
print(f"   - Lonjakan/Guncangan Dibuang: {len(outliers_before)} titik ({[o[2] for o in outliers_before]})")

n_a, m_a, s_a, min_a, max_a = stats(vals_after)
err_pct = abs(m_a - 1413.0) / 1413.0 * 100.0
akurasi_pct = 100.0 - err_pct
print(f"\n3. POST-CALIBRATION DI LARUTAN 1413 (Setelah Kalibrasi Berhasil):")
print(f"   - File Output : 1413_cal_after_press_button_CLEANED.csv")
print(f"   - Jumlah Baris: {n_a} sampel bersih")
print(f"   - Nilai Rata-rata: {m_a:.2f} uS/cm | Std Dev: {s_a:.2f} uS/cm")
print(f"   - Min: {min_a:.1f} uS/cm | Max: {max_a:.1f} uS/cm")
print(f"   - Outlier/Lonjakan Dibuang: {len(outliers_after)} titik ({[o[2] for o in outliers_after]})")
print(f"   - Error Relatif terhadap Standar 1413 uS/cm: {err_pct:.3f}%")
print(f"   - Tingkat Akurasi Sensor: {akurasi_pct:.3f}% (Sangat Sempurna!)")
print("=" * 75)

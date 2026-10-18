# -*- coding: utf-8 -*-
"""
Calibration Engine & Mathematical Algorithms
Includes:
- Stability Detector (Rolling Standard Deviation & Peak-to-Peak)
- Magnetometer Circle/Sphere Fitting (Hard-Iron & Soft-Iron Correction)
- Gyro Bias Accumulator
- Depth/Pressure Tare Calculator
"""

import collections
import math
import numpy as np


class StabilityDetector:
    """
    Evaluates signal stability over a rolling window.
    Indicates whether a sensor reading has settled enough for accurate calibration.
    """
    def __init__(self, window_size: int = 30, std_threshold: float = 0.03):
        self.window_size = window_size
        self.std_threshold = std_threshold
        self.buffer = collections.deque(maxlen=window_size)

    def add_sample(self, value: float):
        self.buffer.append(value)

    def clear(self):
        self.buffer.clear()

    def get_stats(self) -> dict:
        if len(self.buffer) < 5:
            return {
                "ready": False,
                "count": len(self.buffer),
                "mean": 0.0,
                "std": 999.0,
                "p2p": 999.0,
                "is_stable": False
            }

        arr = np.array(self.buffer, dtype=np.float64)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        p2p_val = float(np.ptp(arr))
        is_stable = (std_val <= self.std_threshold) and (len(self.buffer) >= self.window_size * 0.7)

        return {
            "ready": True,
            "count": len(self.buffer),
            "mean": mean_val,
            "std": std_val,
            "p2p": p2p_val,
            "is_stable": is_stable
        }


class MagnetometerFitter:
    """
    Fits 2D circle / 3D sphere from raw magnetometer samples to determine:
    - Hard-Iron offset (Center displacement)
    - Soft-Iron deformation (Radius & axis stretch)
    """
    def __init__(self):
        self.samples_x = []
        self.samples_y = []
        self.samples_z = []

    def clear(self):
        self.samples_x.clear()
        self.samples_y.clear()
        self.samples_z.clear()

    def add_sample(self, x: float, y: float, z: float = 0.0):
        self.samples_x.append(x)
        self.samples_y.append(y)
        self.samples_z.append(z)

    def fit_2d(self) -> dict:
        """
        Fits 2D circle: (x - ox)^2 + (y - oy)^2 = R^2
        Using Algebraic Least Squares (Kasa Method)
        """
        N = len(self.samples_x)
        if N < 20:
            return {"valid": False, "msg": "Sampel terlalu sedikit (butuh min. 20 titik)"}

        x = np.array(self.samples_x, dtype=np.float64)
        y = np.array(self.samples_y, dtype=np.float64)

        # Matrix formulation: A * [2*ox, 2*oy, c]^T = x^2 + y^2
        A = np.column_stack((2 * x, 2 * y, np.ones(N)))
        b = x**2 + y**2

        try:
            sol, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
            ox, oy, c = sol
            radius = math.sqrt(c + ox**2 + oy**2)
            
            # Compute corrected points
            xc = x - ox
            yc = y - oy
            fitted_radii = np.sqrt(xc**2 + yc**2)
            rms_error = float(np.sqrt(np.mean((fitted_radii - radius)**2)))

            return {
                "valid": True,
                "center_x": float(ox),
                "center_y": float(oy),
                "radius": float(radius),
                "rms_error": rms_error,
                "count": N
            }
        except Exception as e:
            return {"valid": False, "msg": f"Gagal fitting: {e}"}


class GyroBiasAccumulator:
    """
    Accumulates gyro readings while the vehicle is stationary to compute zero-rate bias.
    """
    def __init__(self, target_samples: int = 500):
        self.target_samples = target_samples
        self.gx = []
        self.gy = []
        self.gz = []

    def clear(self):
        self.gx.clear()
        self.gy.clear()
        self.gz.clear()

    def add_sample(self, x: float, y: float, z: float):
        if len(self.gx) < self.target_samples:
            self.gx.append(x)
            self.gy.append(y)
            self.gz.append(z)

    def is_complete(self) -> bool:
        return len(self.gx) >= self.target_samples

    def progress_pct(self) -> float:
        return min(100.0, (len(self.gx) / float(self.target_samples)) * 100.0)

    def calculate_bias(self) -> dict:
        if len(self.gx) < 50:
            return {"valid": False, "msg": "Sampel tidak cukup"}
        
        return {
            "valid": True,
            "bias_x": float(np.mean(self.gx)),
            "bias_y": float(np.mean(self.gy)),
            "bias_z": float(np.mean(self.gz)),
            "std_x": float(np.std(self.gx)),
            "std_y": float(np.std(self.gy)),
            "std_z": float(np.std(self.gz)),
            "samples": len(self.gx)
        }

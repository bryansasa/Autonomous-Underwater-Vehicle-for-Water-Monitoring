# -*- coding: utf-8 -*-
"""
Server Medan Kualitas Air Waduk Saguling (Saguling Field Server)
Menerima posisi kedalaman Z wahana ROV/AUV dari Gazebo, lalu menginjeksikan
parameter kualitas air terstratifikasi (DO, pH, Suhu, Konduktivitas) ke topik ROS 2:
/tyrant/payload/water_quality
"""

import time
import math
import random
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Header
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist

try:
    from tyrant_payload_interfaces.msg import PayloadWaterQuality
    HAS_TYRANT_MSGS = True
except ImportError:
    HAS_TYRANT_MSGS = False


class SagulingFieldServer(Node):
    def __init__(self):
        super().__init__('saguling_field_server')

        # Parameter kedalaman wahana
        self.declare_parameter('default_depth', 0.5)
        self.current_depth = self.get_parameter('default_depth').value
        self.sim_time_sec = 0.0
        self.sequence = 0
        self.manual_depth_mode = True  # True jika belum ada odometry dari Gazebo

        # Subscriptions dari Gazebo
        self.sub_odom = self.create_subscription(
            Odometry,
            '/model/tyrant_rov/odometry',
            self._cb_odom,
            10
        )
        self.sub_odom_alt = self.create_subscription(
            Odometry,
            '/bluerov2/odometry',
            self._cb_odom,
            10
        )
        self.sub_cmd_vel = self.create_subscription(
            Twist,
            '/cmd_vel',
            self._cb_cmd_vel,
            10
        )

        # Publishers
        if HAS_TYRANT_MSGS:
            self.pub_wq = self.create_publisher(PayloadWaterQuality, '/tyrant/payload/water_quality', 10)
        else:
            self.get_logger().warn("tyrant_payload_interfaces belum ter-source! Memakai fallback std_msgs.")

        self.pub_depth = self.create_publisher(Float32, '/auv/depth', 10)
        self.pub_imu = self.create_publisher(Imu, '/auv/imu', 10)

        # Timer 10 Hz untuk kalkulasi kualitas air
        self.timer = self.create_timer(0.1, self._timer_callback)
        self.get_logger().info("Saguling Field Server aktif pada 10 Hz. Menunggu posisi ROV dari Gazebo...")

    def _cb_odom(self, msg: Odometry):
        """Membaca posisi Z dari model Gazebo (Z negatif menandakan menyelam di bawah permukaan)."""
        self.manual_depth_mode = False
        z_raw = msg.pose.pose.position.z
        # Di Gazebo, permukaan air di z=0 dan menyelam ke arah z negatif
        self.current_depth = max(0.0, -z_raw if z_raw < 0.0 else z_raw)

    def _cb_cmd_vel(self, msg: Twist):
        """Menerima perintah gerak vertikal dari teleop keyboard atau GCS deadman switch."""
        if self.manual_depth_mode:
            # linear.z positif = naik, negatif = turun
            self.current_depth = max(0.0, min(5.0, self.current_depth - msg.linear.z * 0.05))

    def _timer_callback(self):
        self.sim_time_sec += 0.1
        self.sequence += 1

        # Jika tidak ada Gazebo fisik yang running, jalankan profil penyelaman mandiri (autonomous profiling)
        if self.manual_depth_mode:
            self._auto_step_profiling()

        d = self.current_depth

        # -------------------------------------------------------------
        # Model Stratifikasi Kolom Air Waduk Saguling vs Kedalaman (d)
        # -------------------------------------------------------------
        # 1. Suhu (°C): Termoklin antara 2.0 m - 3.5 m
        temp = 28.5 - 3.7 / (1.0 + math.exp(-(d - 2.5) / 0.45)) + random.uniform(-0.02, 0.02)

        # 2. DO (mg/L): Transisi curam ke anoksia (< 2.0 mg/L) di kedalaman > 3.2 m
        do_val = max(0.5, 7.4 - 6.0 / (1.0 + math.exp(-(d - 3.0) / 0.40)) + random.uniform(-0.03, 0.03))

        # 3. pH: Asam di dasar waduk akibat dekomposisi organik
        ph = max(6.0, min(8.5, 7.65 - 0.90 / (1.0 + math.exp(-(d - 2.8) / 0.60)) + random.uniform(-0.015, 0.015)))

        # 4. Konduktivitas (µS/cm): Peningkatan ion terlarut di dekat sedimen dasar
        cond = 295.0 + 135.0 / (1.0 + math.exp(-(d - 3.2) / 0.50)) + random.uniform(-0.8, 0.8)

        # Publikasikan ke /tyrant/payload/water_quality
        if HAS_TYRANT_MSGS:
            wq_msg = PayloadWaterQuality()
            wq_msg.sequence = self.sequence
            wq_msg.timestamp_us = int(time.time() * 1e6)
            wq_msg.conductivity_us_cm = float(cond)
            wq_msg.ph = float(ph)
            wq_msg.temperature_c = float(temp)
            wq_msg.dissolved_oxygen_mg_l = float(do_val)
            wq_msg.conductivity_valid = True
            wq_msg.ph_valid = True
            wq_msg.temperature_valid = True
            wq_msg.dissolved_oxygen_valid = True
            wq_msg.conductivity_state = PayloadWaterQuality.READY
            wq_msg.ph_state = PayloadWaterQuality.READY
            wq_msg.temperature_state = PayloadWaterQuality.READY
            wq_msg.dissolved_oxygen_state = PayloadWaterQuality.READY
            self.pub_wq.publish(wq_msg)

        # Publikasikan kedalaman ke /auv/depth
        depth_msg = Float32()
        depth_msg.data = float(d)
        self.pub_depth.publish(depth_msg)

        # Publikasikan orientasi dasar ke /auv/imu
        imu_msg = Imu()
        imu_msg.header.stamp = self.get_clock().now().to_msg()
        imu_msg.header.frame_id = "base_link"
        imu_msg.orientation.w = 1.0
        self.pub_imu.publish(imu_msg)

        # Log periodik tiap 3 detik
        if self.sequence % 30 == 0:
            status_anoksia = "[ANOKSIA KRITIS!]" if do_val <= 2.0 else "[NOMINAL]"
            self.get_logger().info(
                f"[SAGULING FIELD] Kedalaman: {d:.2f} m | DO: {do_val:.2f} mg/L {status_anoksia} | pH: {ph:.2f} | T: {temp:.2f} °C"
            )

    def _auto_step_profiling(self):
        """Profil penyelaman bertahap jika teleop Gazebo belum disentuh."""
        t = self.sim_time_sec % 300.0  # siklus 5 menit
        if t < 30:
            self.current_depth = 0.50
        elif t < 90:
            self.current_depth = 0.50 + 1.00 * ((t - 30) / 60)
        elif t < 150:
            self.current_depth = 1.50
        elif t < 210:
            self.current_depth = 1.50 + 2.50 * ((t - 150) / 60)  # Menyelam ke 4.0 m (anoksia)
        elif t < 270:
            self.current_depth = 4.00
        else:
            self.current_depth = 4.00 - 3.50 * ((t - 270) / 30)


def main(args=None):
    rclpy.init(args=args)
    node = SagulingFieldServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

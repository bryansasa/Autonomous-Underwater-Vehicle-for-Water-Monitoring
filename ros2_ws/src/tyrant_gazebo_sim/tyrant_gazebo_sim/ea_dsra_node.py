# -*- coding: utf-8 -*-
"""
Node Algoritma EA-DSRA (Energy-Aware Dynamic Sampling Rate Allocation) - ROS 2
Menerima telemetri kualitas air, menghitung gradien fluktuasi S_max,
memodulasi interval pengambilan sampel T_BM, dan mengelola konsumsi daya sensor
berdasarkan kapasitas baterai (SoC %) serta Safety Override (DO <= 2.0 mg/L).
"""

import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Header

try:
    from tyrant_payload_interfaces.msg import (
        PayloadWaterQuality,
        PayloadPower,
        PayloadHealth,
        SensorPowerStatus,
        SensorPowerRequest
    )
    HAS_TYRANT_MSGS = True
except ImportError:
    HAS_TYRANT_MSGS = False


class EaDsraNode(Node):
    def __init__(self):
        super().__init__('ea_dsra_node')

        # Parameter EA-DSRA
        self.soc_threshold = 30.0
        self.t_min = 1.0
        self.t_max = 5.0
        self.alpha = 2.0
        self.do_critical = 2.0

        # Toleransi deviasi sensor (e)
        self.e_temp = 0.20
        self.e_do = 0.15
        self.e_ph = 0.05
        self.e_cond = 5.0

        # State tracking
        self.prev_vals = {"temp": None, "do": None, "ph": None, "cond": None}
        self.prev_time = None
        self.current_tbm = 3.0
        self.wea_penalty = 1.0
        self.is_override_active = False

        # Model Baterai Sensor 3S LiPo (11.1V, 2200 mAh = 87912 Joule)
        self.sensor_voltage = 11.80
        self.sensor_soc = 42.0  # Mulai di 42% agar melintasi 30% dalam sesi pengujian
        self.sensor_current = 0.05
        self.v_cov = 1.0

        # MOSFET Power Gating status (True = ON, False = OFF)
        self.mosfet_status = {"DO": True, "PH": True, "TEMP": True, "COND": True}

        # Subscriptions
        if HAS_TYRANT_MSGS:
            self.sub_wq = self.create_subscription(
                PayloadWaterQuality,
                '/tyrant/payload/water_quality',
                self._cb_water_quality,
                10
            )
            self.sub_pwr_req = self.create_subscription(
                SensorPowerRequest,
                '/tyrant/payload/sensor_power/request',
                self._cb_pwr_request,
                10
            )

            # Publishers
            self.pub_pwr_sensor = self.create_publisher(PayloadPower, '/tyrant/payload/power/sensors', 10)
            self.pub_health = self.create_publisher(PayloadHealth, '/tyrant/payload/health', 10)
            self.pub_pwr_status = self.create_publisher(SensorPowerStatus, '/tyrant/payload/sensor_power/status', 10)

        # Timer berkala untuk pembaruan status daya & diagnostik (1 Hz)
        self.timer_diag = self.create_timer(1.0, self._timer_diagnostic_callback)
        self.get_logger().info("Node EA-DSRA aktif. Memulai modulasi adaptif frekuensi sampling sensor...")

    def _cb_water_quality(self, msg: PayloadWaterQuality):
        now = time.time()
        if self.prev_time is None:
            self.prev_time = now
            self.prev_vals = {
                "temp": msg.temperature_c,
                "do": msg.dissolved_oxygen_mg_l,
                "ph": msg.ph,
                "cond": msg.conductivity_us_cm
            }
            return

        dt = max(0.1, now - self.prev_time)

        # 1. Hitung Normalisasi Gradien Fluktuasi Air S_i
        s_temp = abs(msg.temperature_c - self.prev_vals["temp"]) / (self.e_temp * dt)
        s_do = abs(msg.dissolved_oxygen_mg_l - self.prev_vals["do"]) / (self.e_do * dt)
        s_ph = abs(msg.ph - self.prev_vals["ph"]) / (self.e_ph * dt)
        s_cond = abs(msg.conductivity_us_cm - self.prev_vals["cond"]) / (self.e_cond * dt)

        # 2. Gradien Maksimum Terpadu S_max
        s_max = max(s_temp, s_do, s_ph, s_cond)

        # 3. Hitung Interval Dasar T_BM
        t_bm_raw = max(self.t_min, min(self.t_max, self.t_max - self.alpha * s_max))

        # 4. Evaluasi Penalti Baterai W_ea
        if self.sensor_soc <= self.soc_threshold:
            self.wea_penalty = self.soc_threshold / max(1.0, self.sensor_soc)
        else:
            self.wea_penalty = 1.0

        t_adjusted = min(self.t_max, t_bm_raw * self.wea_penalty)

        # 5. SAFETY OVERRIDE: Kondisi Anoksia DO <= 2.0 mg/L
        if msg.dissolved_oxygen_valid and msg.dissolved_oxygen_mg_l <= self.do_critical:
            self.current_tbm = self.t_min
            self.is_override_active = True
        else:
            self.current_tbm = t_adjusted
            self.is_override_active = False

        self.prev_vals = {
            "temp": msg.temperature_c,
            "do": msg.dissolved_oxygen_mg_l,
            "ph": msg.ph,
            "cond": msg.conductivity_us_cm
        }
        self.prev_time = now

        # Update konsumsi baterai tiruan
        self._step_battery_discharge(self.current_tbm)

    def _step_battery_discharge(self, interval):
        # Saat interval panjang (misal 5 detik), sensor lebih lama di mode sleep (power gating)
        # Rata-rata arus berbanding terbalik dengan interval sampling
        p_active = 2.00  # Watt
        p_sleep = 0.28   # Watt
        t_sample = 0.40  # detik
        avg_power = (p_active * t_sample + p_sleep * (interval - t_sample)) / interval
        self.sensor_current = avg_power / max(1.0, self.sensor_voltage)

        # Turunkan SoC
        energy_j = avg_power * 0.1
        self.sensor_soc = max(0.0, self.sensor_soc - (energy_j / 87912.0) * 100.0)

    def _cb_pwr_request(self, msg: SensorPowerRequest):
        """Menerima permintaan saklar daya MOSFET dari GCS."""
        sensor_names = {1: "DO", 2: "PH", 3: "COND", 4: "TEMP"}
        s_name = sensor_names.get(msg.sensor_id, "UNKNOWN")
        if s_name in self.mosfet_status:
            self.mosfet_status[s_name] = bool(msg.enable)
            self.get_logger().info(f"[MOSFET SWITCH] Sensor {s_name} diatur ke {'ON' if msg.enable else 'OFF'}")

    def _timer_diagnostic_callback(self):
        if not HAS_TYRANT_MSGS:
            return

        now_us = int(time.time() * 1e6)

        # Publish telemetri daya sensor
        pwr_msg = PayloadPower()
        pwr_msg.monitor_id = PayloadPower.PAYLOAD_SENSOR_RAIL
        pwr_msg.bus_voltage_v = float(self.sensor_voltage)
        pwr_msg.current_a = float(self.sensor_current)
        pwr_msg.power_w = float(self.sensor_voltage * self.sensor_current)
        pwr_msg.valid = True
        pwr_msg.timestamp_us = now_us
        self.pub_pwr_sensor.publish(pwr_msg)

        # Publish kesehatan & status MOSFET
        hlth_msg = PayloadHealth()
        hlth_msg.timestamp_us = now_us
        hlth_msg.mosfet_do_on = self.mosfet_status["DO"]
        hlth_msg.mosfet_ph_on = self.mosfet_status["PH"]
        hlth_msg.mosfet_temperature_on = self.mosfet_status["TEMP"]
        hlth_msg.mosfet_conductivity_on = self.mosfet_status["COND"]
        hlth_msg.i2c_bus1_healthy = True
        hlth_msg.i2c_bus2_healthy = True
        self.pub_health.publish(hlth_msg)

        override_text = " [SAFETY OVERRIDE AKTIF!]" if self.is_override_active else ""
        self.get_logger().info(
            f"[EA-DSRA STATUS] Interval T_BM: {self.current_tbm:.2f} s | Baterai SoC: {self.sensor_soc:.1f}% | Penalti W_ea: {self.wea_penalty:.2f}{override_text}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = EaDsraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

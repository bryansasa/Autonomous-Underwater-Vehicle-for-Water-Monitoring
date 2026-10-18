import math

import rclpy
from rclpy.node import Node

from tyrant_interfaces.msg import SimpleState, ThrusterCommand

from .model import (
    BodyWrench,
    ReducedPlantConfig,
    ReducedPlantModel,
    ReducedPlantState,
    synthetic_thrusters_to_wrench,
)


class TyrantPlantSim(Node):
    def __init__(self):
        super().__init__('tyrant_plant_sim')

        self.declare_parameter('update_rate_hz', 50.0)
        self.declare_parameter('initial_depth_m', 0.0)
        self.declare_parameter('initial_roll_rad', 0.0)
        self.declare_parameter('initial_pitch_rad', 0.0)
        self.declare_parameter('initial_yaw_rad', 0.0)

        for name, default in {
            'heave_accel_per_z': 0.80,
            'heave_damping_per_s': 1.20,
            'roll_accel_per_k': 1.50,
            'roll_damping_per_s': 1.50,
            'roll_restoring_per_s2': 0.70,
            'pitch_accel_per_m': 1.50,
            'pitch_damping_per_s': 1.50,
            'pitch_restoring_per_s2': 0.70,
            'yaw_accel_per_n': 1.00,
            'yaw_damping_per_s': 1.20,
            'max_depth_m': 20.0,
            'max_angular_rate_rad_s': 2.0,
        }.items():
            self.declare_parameter(name, default)

        rate_hz = float(self.get_parameter('update_rate_hz').value)
        if not math.isfinite(rate_hz) or rate_hz <= 0.0 or rate_hz > 200.0:
            raise ValueError('update_rate_hz must be in (0, 200]')

        cfg = ReducedPlantConfig(
            heave_accel_per_z=float(self.get_parameter('heave_accel_per_z').value),
            heave_damping_per_s=float(self.get_parameter('heave_damping_per_s').value),
            roll_accel_per_k=float(self.get_parameter('roll_accel_per_k').value),
            roll_damping_per_s=float(self.get_parameter('roll_damping_per_s').value),
            roll_restoring_per_s2=float(self.get_parameter('roll_restoring_per_s2').value),
            pitch_accel_per_m=float(self.get_parameter('pitch_accel_per_m').value),
            pitch_damping_per_s=float(self.get_parameter('pitch_damping_per_s').value),
            pitch_restoring_per_s2=float(self.get_parameter('pitch_restoring_per_s2').value),
            yaw_accel_per_n=float(self.get_parameter('yaw_accel_per_n').value),
            yaw_damping_per_s=float(self.get_parameter('yaw_damping_per_s').value),
            max_depth_m=float(self.get_parameter('max_depth_m').value),
            max_angular_rate_rad_s=float(self.get_parameter('max_angular_rate_rad_s').value),
        )
        state = ReducedPlantState(
            depth_m=float(self.get_parameter('initial_depth_m').value),
            roll_rad=float(self.get_parameter('initial_roll_rad').value),
            pitch_rad=float(self.get_parameter('initial_pitch_rad').value),
            yaw_rad=float(self.get_parameter('initial_yaw_rad').value),
        )
        self.model = ReducedPlantModel(cfg, state)
        self.dt_s = 1.0 / rate_hz
        self.last_wrench = BodyWrench()

        self.state_pub = self.create_publisher(
            SimpleState,
            '/tyrant/sim/state_input',
            10,
        )
        self.thruster_sub = self.create_subscription(
            ThrusterCommand,
            '/tyrant/control/thruster_command',
            self._thruster_callback,
            10,
        )
        self.timer = self.create_timer(self.dt_s, self._update)

        self.get_logger().info(
            'Synthetic reduced plant HIL active. This is not a validated vehicle model.'
        )

    def _thruster_callback(self, msg: ThrusterCommand):
        if not msg.enabled or not msg.valid or not msg.allocator_ready:
            self.last_wrench = BodyWrench()
            return

        try:
            self.last_wrench = synthetic_thrusters_to_wrench(msg.command)
        except ValueError as exc:
            self.get_logger().warning(f'invalid thruster command: {exc}')
            self.last_wrench = BodyWrench()

    def _update(self):
        state = self.model.step(self.last_wrench, self.dt_s)

        msg = SimpleState()
        msg.timestamp_us = int(self.get_clock().now().nanoseconds // 1000)
        msg.status = SimpleState.RUNNING
        msg.roll = float(state.roll_rad)
        msg.pitch = float(state.pitch_rad)
        msg.yaw = float(state.yaw_rad)
        msg.angular_velocity_x = float(state.p_rad_s)
        msg.angular_velocity_y = float(state.q_rad_s)
        msg.angular_velocity_z = float(state.r_rad_s)
        msg.yaw_rate_bias = 0.0
        msg.depth = float(state.depth_m)
        msg.attitude_valid = True
        msg.heading_valid = True
        msg.depth_valid = True
        self.state_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TyrantPlantSim()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

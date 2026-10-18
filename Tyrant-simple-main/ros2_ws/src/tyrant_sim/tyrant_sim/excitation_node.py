import rclpy
from rclpy.node import Node

from std_msgs.msg import UInt32
from tyrant_interfaces.msg import ManualCommand, ModeRequest, ModeStatus, SysIdControl

from .profiles import Command6, ExcitationProfile


MODE_MANUAL = 2
MODE_SAFE = 4
SYSID_STOP = 0
SYSID_START = 1


class TyrantSysIdExcitation(Node):
    def __init__(self):
        super().__init__('tyrant_sysid_excitation')

        self.declare_parameter('profile', 'step_yaw')
        self.declare_parameter('amplitude', 0.25)
        self.declare_parameter('duration_s', 12.0)
        self.declare_parameter('pre_roll_s', 2.0)
        self.declare_parameter('post_roll_s', 2.0)
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('experiment_id', 1001)
        self.declare_parameter('profile_id_override', 0)
        self.declare_parameter('prbs_hold_s', 0.5)
        self.declare_parameter('chirp_start_hz', 0.05)
        self.declare_parameter('chirp_end_hz', 0.8)
        self.declare_parameter('mode_timeout_s', 5.0)

        profile_name = str(self.get_parameter('profile').value)
        self.profile = ExcitationProfile(
            profile_name,
            float(self.get_parameter('amplitude').value),
            float(self.get_parameter('duration_s').value),
            float(self.get_parameter('prbs_hold_s').value),
            float(self.get_parameter('chirp_start_hz').value),
            float(self.get_parameter('chirp_end_hz').value),
        )

        self.pre_roll_s = float(self.get_parameter('pre_roll_s').value)
        self.post_roll_s = float(self.get_parameter('post_roll_s').value)
        self.mode_timeout_s = float(self.get_parameter('mode_timeout_s').value)
        self.experiment_id = int(self.get_parameter('experiment_id').value)
        override = int(self.get_parameter('profile_id_override').value)
        self.profile_id = override if override > 0 else self.profile.profile_id

        rate_hz = float(self.get_parameter('publish_rate_hz').value)
        if rate_hz <= 0.0 or rate_hz > 100.0:
            raise ValueError('publish_rate_hz must be in (0, 100]')
        if self.experiment_id <= 0:
            raise ValueError('experiment_id must be non-zero')
        if self.pre_roll_s < 0.5:
            raise ValueError('pre_roll_s must be >= 0.5 s for reference settling')
        if self.post_roll_s < 0.0:
            raise ValueError('post_roll_s must be non-negative')
        if self.mode_timeout_s < 1.0:
            raise ValueError('mode_timeout_s must be >= 1 s')

        self.command_pub = self.create_publisher(ManualCommand, '/tyrant/manual/command', 10)
        self.heartbeat_pub = self.create_publisher(UInt32, '/tyrant/host_heartbeat', 10)
        self.mode_pub = self.create_publisher(ModeRequest, '/tyrant/mode/request', 10)
        self.sysid_pub = self.create_publisher(SysIdControl, '/tyrant/sysid/control', 10)
        self.mode_sub = self.create_subscription(
            ModeStatus,
            '/tyrant/mode/status',
            self._mode_callback,
            10,
        )

        self.node_start_ns = self.get_clock().now().nanoseconds
        self.manual_start_ns = None
        self.sequence = 0
        self.heartbeat = 0
        self.current_mode = None
        self.last_mode_request_ns = 0
        self.sysid_started = False
        self.finished = False
        self.request_id = 100

        self.timer = self.create_timer(1.0 / rate_hz, self._tick)

        self.get_logger().info(
            f'SysID excitation armed: {profile_name}, experiment={self.experiment_id}, '
            f'profile_id={self.profile_id}. Use only with mock/HIL until hardware procedure is approved.'
        )

    def _mode_callback(self, msg: ModeStatus):
        self.current_mode = int(msg.current_mode)

    def _publish_heartbeat(self):
        self.heartbeat += 1
        msg = UInt32()
        msg.data = self.heartbeat
        self.heartbeat_pub.publish(msg)

    def _request_mode(self, mode: int):
        self.request_id += 1
        msg = ModeRequest()
        msg.request_id = self.request_id
        msg.requested_mode = mode
        self.mode_pub.publish(msg)

    def _sysid_control(self, command: int):
        self.request_id += 1
        msg = SysIdControl()
        msg.request_id = self.request_id
        msg.command = command
        msg.experiment_id = self.experiment_id
        msg.profile_id = self.profile_id
        self.sysid_pub.publish(msg)

    def _publish_command(self, command: Command6):
        self.sequence += 1
        msg = ManualCommand()
        msg.sequence = self.sequence
        msg.surge = command.surge
        msg.sway = command.sway
        msg.heave = command.heave
        msg.roll = command.roll
        msg.pitch = command.pitch
        msg.yaw = command.yaw
        self.command_pub.publish(msg)

    def _finish(self, reason: str):
        if self.finished:
            return
        self._publish_command(Command6())
        if self.sysid_started:
            self._sysid_control(SYSID_STOP)
            self.sysid_started = False
        self._request_mode(MODE_SAFE)
        self.finished = True
        self.get_logger().info(reason)
        self.timer.cancel()

    def _tick(self):
        if self.finished:
            return

        self._publish_heartbeat()
        now_ns = self.get_clock().now().nanoseconds
        node_elapsed_s = (now_ns - self.node_start_ns) * 1.0e-9

        if self.manual_start_ns is None:
            # Re-request MANUAL every 0.5 s until status confirms the mode.
            if self.current_mode != MODE_MANUAL:
                if (now_ns - self.last_mode_request_ns) >= 500_000_000:
                    self._request_mode(MODE_MANUAL)
                    self.last_mode_request_ns = now_ns
                if node_elapsed_s > self.mode_timeout_s:
                    self._finish('SysID aborted: MANUAL mode was not established in time.')
                return

            self.manual_start_ns = now_ns
            self._sysid_control(SYSID_START)
            self.sysid_started = True
            self.get_logger().info('MANUAL confirmed; SysID recording started.')

        if self.current_mode != MODE_MANUAL:
            self._finish('SysID aborted: vehicle left MANUAL mode.')
            return

        elapsed_s = (now_ns - self.manual_start_ns) * 1.0e-9
        excitation_t = elapsed_s - self.pre_roll_s

        if excitation_t < 0.0:
            self._publish_command(Command6())
            return

        if excitation_t < self.profile.duration_s:
            self._publish_command(self.profile.command_at(excitation_t))
            return

        if excitation_t < self.profile.duration_s + self.post_roll_s:
            self._publish_command(Command6())
            return

        self._finish('SysID excitation complete; requested SAFE.')


def main(args=None):
    rclpy.init(args=args)
    node = TyrantSysIdExcitation()
    try:
        rclpy.spin(node)
    finally:
        if not node.finished:
            node._finish('SysID excitation stopped; requested SAFE.')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

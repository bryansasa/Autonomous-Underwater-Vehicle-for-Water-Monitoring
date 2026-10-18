import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy


class JoyProbe(Node):
    def __init__(self) -> None:
        super().__init__('tyrant_joy_probe')
        self.declare_parameter('change_threshold', 0.20)
        self._threshold = float(self.get_parameter('change_threshold').value)
        self._last_axes: list[float] = []
        self._last_buttons: list[int] = []
        self.create_subscription(Joy, '/joy', self._on_joy, 10)
        self.get_logger().info('Watching /joy. Move one control at a time.')

    def _on_joy(self, msg: Joy) -> None:
        if len(self._last_axes) != len(msg.axes):
            self.get_logger().info(f'axes count={len(msg.axes)} buttons count={len(msg.buttons)}')
            self._last_axes = list(msg.axes)
            self._last_buttons = list(msg.buttons)
            return

        for index, value in enumerate(msg.axes):
            previous = self._last_axes[index]
            if math.fabs(value - previous) >= self._threshold:
                self.get_logger().info(f'axis[{index}] {previous:+.3f} -> {value:+.3f}')

        if len(self._last_buttons) != len(msg.buttons):
            self._last_buttons = list(msg.buttons)
        else:
            for index, value in enumerate(msg.buttons):
                if value != self._last_buttons[index]:
                    self.get_logger().info(f'button[{index}] {self._last_buttons[index]} -> {value}')

        self._last_axes = list(msg.axes)
        self._last_buttons = list(msg.buttons)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = JoyProbe()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

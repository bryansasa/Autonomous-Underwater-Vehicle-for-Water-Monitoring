from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from std_msgs.msg import UInt32

from tyrant_interfaces.msg import DepthReferenceRequest
from tyrant_interfaces.msg import ManualCommand
from tyrant_interfaces.msg import ModeRequest

from .mapper import AxisSpec
from .mapper import TeleopMapping
from .mapper import TriggerPairSpec
from .mapper import map_axes


# ============================================================
# BUTTON STATE
# ============================================================

@dataclass
class ButtonState:
    deadman: bool = False

    manual: bool = False
    idle: bool = False
    safe: bool = False

    surface: bool = False


# ============================================================
# TELEOP NODE
# ============================================================

class TyrantTeleop(Node):

    def __init__(self) -> None:
        super().__init__('tyrant_teleop')

        self._declare_parameters()

        self._mapping = self._load_mapping()

        self._publish_rate_hz = float(
            self.get_parameter(
                'publish_rate_hz'
            ).value
        )

        self._heartbeat_rate_hz = float(
            self.get_parameter(
                'heartbeat_rate_hz'
            ).value
        )

        self._joy_timeout_s = float(
            self.get_parameter(
                'joy_timeout_s'
            ).value
        )

        self._safe_timeout_s = float(
            self.get_parameter(
                'safe_timeout_s'
            ).value
        )

        self._safe_on_joy_timeout = bool(
            self.get_parameter(
                'safe_on_joy_timeout'
            ).value
        )

        self._publish_heartbeat = bool(
            self.get_parameter(
                'publish_heartbeat'
            ).value
        )

        # ====================================================
        # CONTROLLER BUTTON MAPPING
        # ====================================================

        self._deadman_button = int(
            self.get_parameter(
                'buttons.deadman'
            ).value
        )

        self._manual_button = int(
            self.get_parameter(
                'buttons.manual_mode'
            ).value
        )

        self._idle_button = int(
            self.get_parameter(
                'buttons.idle_mode'
            ).value
        )

        self._safe_button = int(
            self.get_parameter(
                'buttons.safe_mode'
            ).value
        )

        self._surface_button = int(
            self.get_parameter(
                'buttons.set_surface'
            ).value
        )

        # ====================================================
        # RUNTIME STATE
        # ====================================================

        self._latest_joy: Optional[Joy] = None
        self._latest_joy_time = None

        self._last_buttons = ButtonState()

        self._sequence = 0
        self._request_id = 0
        self._heartbeat_counter = 0

        self._safe_timeout_sent = False

        self._deadman_release_neutral_sent = False

        # ====================================================
        # PUBLISHERS
        # ====================================================

        self._manual_pub = self.create_publisher(
            ManualCommand,
            '/tyrant/manual/command',
            10,
        )

        self._mode_pub = self.create_publisher(
            ModeRequest,
            '/tyrant/mode/request',
            10,
        )

        self._depth_ref_pub = self.create_publisher(
            DepthReferenceRequest,
            '/tyrant/depth/reference/request',
            10,
        )

        self._heartbeat_pub = self.create_publisher(
            UInt32,
            '/tyrant/host_heartbeat',
            10,
        )

        # ====================================================
        # SUBSCRIBERS
        # ====================================================

        self.create_subscription(
            Joy,
            '/joy',
            self._on_joy,
            10,
        )

        # ====================================================
        # TIMERS
        # ====================================================

        self.create_timer(
            1.0 / max(
                1.0,
                self._publish_rate_hz
            ),
            self._publish_manual_tick,
        )

        self.create_timer(
            1.0 / max(
                1.0,
                self._heartbeat_rate_hz
            ),
            self._publish_heartbeat_tick,
        )

        self.get_logger().info(
            'Tyrant teleop ready.'
        )

        self.get_logger().info(
            'L1=DEADMAN | CROSS=MANUAL | '
            'SQUARE=IDLE | CIRCLE=SAFE | '
            'TRIANGLE=SET SURFACE'
        )


    # ========================================================
    # PARAMETERS
    # ========================================================

    def _declare_parameters(self) -> None:

        defaults = {

            # ------------------------------------------------
            # GENERAL
            # ------------------------------------------------

            'publish_rate_hz': 20.0,

            'heartbeat_rate_hz': 10.0,

            'publish_heartbeat': True,

            'joy_timeout_s': 0.20,

            'safe_timeout_s': 1.00,

            'safe_on_joy_timeout': True,

            'deadzone': 0.08,

            # ------------------------------------------------
            # SURGE
            # Left stick Y
            # ------------------------------------------------

            'axes.surge.index': 1,

            'axes.surge.invert': True,

            'axes.surge.scale': 1.0,

            # ------------------------------------------------
            # SWAY
            # Left stick X
            # ------------------------------------------------

            'axes.sway.index': 0,

            'axes.sway.invert': False,

            'axes.sway.scale': 1.0,

            # ------------------------------------------------
            # HEAVE
            # Trigger pair used by default
            # ------------------------------------------------

            'axes.heave.index': -1,

            'axes.heave.invert': False,

            'axes.heave.scale': 1.0,

            # ------------------------------------------------
            # ROLL
            # Auto-level by default
            # ------------------------------------------------

            'axes.roll.index': -1,

            'axes.roll.invert': False,

            'axes.roll.scale': 1.0,

            # ------------------------------------------------
            # PITCH
            # Auto-level by default
            # ------------------------------------------------

            'axes.pitch.index': -1,

            'axes.pitch.invert': False,

            'axes.pitch.scale': 1.0,

            # ------------------------------------------------
            # YAW
            # Right stick X
            # ------------------------------------------------

            'axes.yaw.index': 3,

            'axes.yaw.invert': False,

            'axes.yaw.scale': 1.0,

            # ------------------------------------------------
            # HEAVE TRIGGERS
            # ------------------------------------------------

            'heave_triggers.positive_index': 5,

            'heave_triggers.negative_index': 2,

            'heave_triggers.rest_value': 1.0,

            'heave_triggers.pressed_value': -1.0,

            'heave_triggers.scale': 1.0,

            # ------------------------------------------------
            # BUTTONS
            # Actual controller mapping from joy probe
            # ------------------------------------------------

            # L1
            'buttons.deadman': 4,

            # CROSS
            'buttons.manual_mode': 0,

            # SQUARE
            'buttons.idle_mode': 2,

            # CIRCLE
            'buttons.safe_mode': 1,

            # TRIANGLE
            'buttons.set_surface': 3,
        }

        for name, value in defaults.items():
            self.declare_parameter(
                name,
                value
            )


    # ========================================================
    # AXIS CONFIG
    # ========================================================

    def _axis_spec(
        self,
        name: str
    ) -> AxisSpec:

        return AxisSpec(
            index=int(
                self.get_parameter(
                    f'axes.{name}.index'
                ).value
            ),

            invert=bool(
                self.get_parameter(
                    f'axes.{name}.invert'
                ).value
            ),

            scale=float(
                self.get_parameter(
                    f'axes.{name}.scale'
                ).value
            ),
        )


    def _load_mapping(
        self
    ) -> TeleopMapping:

        return TeleopMapping(

            surge=self._axis_spec(
                'surge'
            ),

            sway=self._axis_spec(
                'sway'
            ),

            heave=self._axis_spec(
                'heave'
            ),

            roll=self._axis_spec(
                'roll'
            ),

            pitch=self._axis_spec(
                'pitch'
            ),

            yaw=self._axis_spec(
                'yaw'
            ),

            heave_triggers=TriggerPairSpec(

                positive_index=int(
                    self.get_parameter(
                        'heave_triggers.positive_index'
                    ).value
                ),

                negative_index=int(
                    self.get_parameter(
                        'heave_triggers.negative_index'
                    ).value
                ),

                rest_value=float(
                    self.get_parameter(
                        'heave_triggers.rest_value'
                    ).value
                ),

                pressed_value=float(
                    self.get_parameter(
                        'heave_triggers.pressed_value'
                    ).value
                ),

                scale=float(
                    self.get_parameter(
                        'heave_triggers.scale'
                    ).value
                ),
            ),

            deadzone=float(
                self.get_parameter(
                    'deadzone'
                ).value
            ),
        )


    # ========================================================
    # BUTTON HELPERS
    # ========================================================

    @staticmethod
    def _button(
        buttons: list[int] | tuple[int, ...],
        index: int
    ) -> bool:

        return (
            0 <= index < len(buttons)
            and bool(buttons[index])
        )


    def _read_buttons(
        self,
        msg: Joy
    ) -> ButtonState:

        return ButtonState(

            deadman=self._button(
                msg.buttons,
                self._deadman_button
            ),

            manual=self._button(
                msg.buttons,
                self._manual_button
            ),

            idle=self._button(
                msg.buttons,
                self._idle_button
            ),

            safe=self._button(
                msg.buttons,
                self._safe_button
            ),

            surface=self._button(
                msg.buttons,
                self._surface_button
            ),
        )


    # ========================================================
    # REQUEST ID
    # ========================================================

    def _next_request_id(
        self
    ) -> int:

        self._request_id = (
            self._request_id + 1
        ) & 0xFFFFFFFF

        if self._request_id == 0:
            self._request_id = 1

        return self._request_id


    # ========================================================
    # MODE REQUEST
    # ========================================================

    def _publish_mode_request(
        self,
        mode: int
    ) -> None:

        msg = ModeRequest()

        msg.request_id = (
            self._next_request_id()
        )

        msg.requested_mode = mode

        self._mode_pub.publish(
            msg
        )


    # ========================================================
    # JOYSTICK CALLBACK
    # ========================================================

    def _on_joy(
        self,
        msg: Joy
    ) -> None:

        now = self.get_clock().now()

        buttons = self._read_buttons(
            msg
        )

        # ----------------------------------------------------
        # CROSS -> MANUAL
        # ----------------------------------------------------

        if (
            buttons.manual
            and not self._last_buttons.manual
        ):
            self._publish_mode_request(
                ModeRequest.MANUAL
            )

            self.get_logger().info(
                'MANUAL requested from controller'
            )

        # ----------------------------------------------------
        # SQUARE -> IDLE
        # ----------------------------------------------------

        if (
            buttons.idle
            and not self._last_buttons.idle
        ):
            self._publish_mode_request(
                ModeRequest.IDLE
            )

            self.get_logger().info(
                'IDLE requested from controller'
            )

        # ----------------------------------------------------
        # CIRCLE -> SAFE
        # ----------------------------------------------------

        if (
            buttons.safe
            and not self._last_buttons.safe
        ):
            self._publish_mode_request(
                ModeRequest.SAFE
            )

            self.get_logger().warn(
                'SAFE requested from controller'
            )

        # ----------------------------------------------------
        # TRIANGLE -> SET DEPTH SURFACE REFERENCE
        # ----------------------------------------------------

        if (
            buttons.surface
            and not self._last_buttons.surface
        ):

            request = DepthReferenceRequest()

            request.request_id = (
                self._next_request_id()
            )

            request.command = (
                DepthReferenceRequest.SET_SURFACE
            )

            self._depth_ref_pub.publish(
                request
            )

            self.get_logger().info(
                'Depth surface reference requested'
            )

        # ----------------------------------------------------
        # DEADMAN RELEASE -> SEND NEUTRAL ONCE
        # ----------------------------------------------------

        if (
            self._last_buttons.deadman
            and not buttons.deadman
        ):
            self._publish_neutral_once()

            self._deadman_release_neutral_sent = True

        elif buttons.deadman:

            self._deadman_release_neutral_sent = False

        # ----------------------------------------------------
        # SAVE JOYSTICK STATE
        # ----------------------------------------------------

        self._latest_joy = msg

        self._latest_joy_time = now

        self._last_buttons = buttons

        self._safe_timeout_sent = False


    # ========================================================
    # JOYSTICK AGE
    # ========================================================

    def _joy_age_s(
        self
    ) -> float:

        if self._latest_joy_time is None:
            return float('inf')

        return (
            self.get_clock().now()
            - self._latest_joy_time
        ).nanoseconds * 1.0e-9


    # ========================================================
    # NEUTRAL COMMAND
    # ========================================================

    def _publish_neutral_once(
        self
    ) -> None:

        msg = ManualCommand()

        self._sequence = (
            self._sequence + 1
        ) & 0xFFFFFFFF

        msg.sequence = self._sequence

        self._manual_pub.publish(
            msg
        )


    # ========================================================
    # MANUAL COMMAND
    # ========================================================

    def _publish_manual_tick(
        self
    ) -> None:

        if self._latest_joy is None:
            return

        age_s = self._joy_age_s()

        # ----------------------------------------------------
        # JOYSTICK TIMEOUT
        # ----------------------------------------------------

        if age_s > self._joy_timeout_s:

            if (
                self._safe_on_joy_timeout
                and age_s > self._safe_timeout_s
                and not self._safe_timeout_sent
            ):

                self._publish_mode_request(
                    ModeRequest.SAFE
                )

                self._safe_timeout_sent = True

                self.get_logger().warn(
                    'Joy timeout: SAFE requested'
                )

            return

        # ----------------------------------------------------
        # DEADMAN REQUIRED
        # ----------------------------------------------------

        buttons = self._read_buttons(
            self._latest_joy
        )

        if not buttons.deadman:
            return

        # ----------------------------------------------------
        # MAP JOYSTICK AXES
        # ----------------------------------------------------

        (
            surge,
            sway,
            heave,
            roll,
            pitch,
            yaw
        ) = map_axes(
            self._latest_joy.axes,
            self._mapping,
        )

        # ----------------------------------------------------
        # PUBLISH MANUAL COMMAND
        # ----------------------------------------------------

        msg = ManualCommand()

        self._sequence = (
            self._sequence + 1
        ) & 0xFFFFFFFF

        msg.sequence = self._sequence

        msg.surge = surge
        msg.sway = sway
        msg.heave = heave

        msg.roll = roll
        msg.pitch = pitch
        msg.yaw = yaw

        self._manual_pub.publish(
            msg
        )


    # ========================================================
    # HOST HEARTBEAT
    # ========================================================

    def _publish_heartbeat_tick(
        self
    ) -> None:

        if not self._publish_heartbeat:
            return

        self._heartbeat_counter = (
            self._heartbeat_counter + 1
        ) & 0xFFFFFFFF

        msg = UInt32()

        msg.data = (
            self._heartbeat_counter
        )

        self._heartbeat_pub.publish(
            msg
        )


# ============================================================
# MAIN
# ============================================================

def main(args=None) -> None:

    rclpy.init(
        args=args
    )

    node = TyrantTeleop()

    try:
        rclpy.spin(
            node
        )

    finally:
        node.destroy_node()

        rclpy.shutdown()

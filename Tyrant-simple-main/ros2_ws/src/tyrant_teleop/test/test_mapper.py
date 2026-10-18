import math

from tyrant_teleop.mapper import AxisSpec
from tyrant_teleop.mapper import TeleopMapping
from tyrant_teleop.mapper import TriggerPairSpec
from tyrant_teleop.mapper import apply_deadzone
from tyrant_teleop.mapper import map_axes
from tyrant_teleop.mapper import trigger_activation


def make_mapping() -> TeleopMapping:
    return TeleopMapping(
        surge=AxisSpec(1, True, 1.0),
        sway=AxisSpec(0, False, 1.0),
        heave=AxisSpec(-1, False, 1.0),
        roll=AxisSpec(-1, False, 1.0),
        pitch=AxisSpec(-1, False, 1.0),
        yaw=AxisSpec(3, False, 1.0),
        heave_triggers=TriggerPairSpec(5, 2, 1.0, -1.0, 1.0),
        deadzone=0.08,
    )


def test_deadzone_zeroes_small_input():
    assert apply_deadzone(0.04, 0.08) == 0.0


def test_deadzone_preserves_sign():
    assert apply_deadzone(-0.50, 0.08) < 0.0
    assert apply_deadzone(+0.50, 0.08) > 0.0


def test_trigger_activation_common_linux_range():
    assert trigger_activation(+1.0, +1.0, -1.0) == 0.0
    assert trigger_activation(-1.0, +1.0, -1.0) == 1.0
    assert math.isclose(trigger_activation(0.0, +1.0, -1.0), 0.5)


def test_map_axes_inverts_forward_stick():
    axes = [0.0, -1.0, +1.0, 0.0, 0.0, +1.0]
    surge, sway, heave, roll, pitch, yaw = map_axes(axes, make_mapping())
    assert surge == 1.0
    assert sway == 0.0
    assert heave == 0.0
    assert roll == 0.0
    assert pitch == 0.0
    assert yaw == 0.0


def test_right_trigger_commands_positive_down_heave():
    axes = [0.0, 0.0, +1.0, 0.0, 0.0, -1.0]
    values = map_axes(axes, make_mapping())
    assert values[2] == 1.0


def test_left_trigger_commands_negative_up_heave():
    axes = [0.0, 0.0, -1.0, 0.0, 0.0, +1.0]
    values = map_axes(axes, make_mapping())
    assert values[2] == -1.0


def test_both_triggers_cancel():
    axes = [0.0, 0.0, -1.0, 0.0, 0.0, -1.0]
    values = map_axes(axes, make_mapping())
    assert values[2] == 0.0


def test_missing_axis_is_safe_zero():
    values = map_axes([0.0], make_mapping())
    assert values == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

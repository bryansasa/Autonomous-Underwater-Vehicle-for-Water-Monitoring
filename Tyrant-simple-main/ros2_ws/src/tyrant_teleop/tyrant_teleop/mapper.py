from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class AxisSpec:
    index: int = -1
    invert: bool = False
    scale: float = 1.0


@dataclass(frozen=True)
class TriggerPairSpec:
    positive_index: int = -1
    negative_index: int = -1
    rest_value: float = 1.0
    pressed_value: float = -1.0
    scale: float = 1.0


@dataclass(frozen=True)
class TeleopMapping:
    surge: AxisSpec
    sway: AxisSpec
    heave: AxisSpec
    roll: AxisSpec
    pitch: AxisSpec
    yaw: AxisSpec
    heave_triggers: TriggerPairSpec
    deadzone: float = 0.08


def clamp_unit(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(-1.0, min(1.0, value))


def apply_deadzone(value: float, deadzone: float) -> float:
    value = clamp_unit(value)
    deadzone = max(0.0, min(0.95, deadzone))
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0

    scaled = (magnitude - deadzone) / (1.0 - deadzone)
    return math.copysign(scaled, value)


def read_axis(axes: Sequence[float], spec: AxisSpec, deadzone: float) -> float:
    if spec.index < 0 or spec.index >= len(axes):
        return 0.0

    value = float(axes[spec.index])
    if spec.invert:
        value = -value

    return clamp_unit(apply_deadzone(value, deadzone) * spec.scale)


def trigger_activation(value: float, rest_value: float, pressed_value: float) -> float:
    denominator = pressed_value - rest_value
    if abs(denominator) < 1.0e-6:
        return 0.0

    activation = (value - rest_value) / denominator
    return max(0.0, min(1.0, activation))


def read_trigger_pair(
    axes: Sequence[float],
    spec: TriggerPairSpec,
    deadzone: float,
) -> float:
    if (
        spec.positive_index < 0
        or spec.negative_index < 0
        or spec.positive_index >= len(axes)
        or spec.negative_index >= len(axes)
    ):
        return 0.0

    positive = trigger_activation(
        float(axes[spec.positive_index]),
        spec.rest_value,
        spec.pressed_value,
    )
    negative = trigger_activation(
        float(axes[spec.negative_index]),
        spec.rest_value,
        spec.pressed_value,
    )

    return clamp_unit(apply_deadzone(positive - negative, deadzone) * spec.scale)


def map_axes(axes: Sequence[float], mapping: TeleopMapping) -> tuple[float, float, float, float, float, float]:
    heave = read_axis(axes, mapping.heave, mapping.deadzone)
    if mapping.heave_triggers.positive_index >= 0 and mapping.heave_triggers.negative_index >= 0:
        heave = read_trigger_pair(axes, mapping.heave_triggers, mapping.deadzone)

    return (
        read_axis(axes, mapping.surge, mapping.deadzone),
        read_axis(axes, mapping.sway, mapping.deadzone),
        heave,
        read_axis(axes, mapping.roll, mapping.deadzone),
        read_axis(axes, mapping.pitch, mapping.deadzone),
        read_axis(axes, mapping.yaw, mapping.deadzone),
    )

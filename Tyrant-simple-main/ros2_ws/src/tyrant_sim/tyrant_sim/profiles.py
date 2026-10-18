from dataclasses import dataclass
import math


AXES = ('surge', 'sway', 'heave', 'roll', 'pitch', 'yaw')

PROFILE_ID = {
    'step_surge': 1,
    'step_sway': 2,
    'step_heave': 3,
    'step_roll': 4,
    'step_pitch': 5,
    'step_yaw': 6,
    'prbs_surge': 10,
    'prbs_sway': 10,
    'prbs_heave': 10,
    'prbs_roll': 10,
    'prbs_pitch': 10,
    'prbs_yaw': 10,
    'chirp_yaw': 10,
}


@dataclass(frozen=True)
class Command6:
    surge: float = 0.0
    sway: float = 0.0
    heave: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _axis_command(axis: str, value: float) -> Command6:
    if axis not in AXES:
        raise ValueError(f'unsupported axis: {axis}')
    fields = {name: 0.0 for name in AXES}
    fields[axis] = _clamp(value)
    return Command6(**fields)


def _profile_parts(name: str):
    if name.startswith('step_'):
        return 'step', name[len('step_'):]
    if name.startswith('prbs_'):
        return 'prbs', name[len('prbs_'):]
    if name == 'chirp_yaw':
        return 'chirp', 'yaw'
    raise ValueError(f'unknown SysID profile: {name}')


class ExcitationProfile:
    """Deterministic excitation. It never uses random module state."""

    def __init__(
        self,
        name: str,
        amplitude: float,
        duration_s: float,
        prbs_hold_s: float = 0.5,
        chirp_start_hz: float = 0.05,
        chirp_end_hz: float = 0.8,
    ):
        if name not in PROFILE_ID:
            raise ValueError(f'unknown profile: {name}')
        if not math.isfinite(amplitude) or amplitude <= 0.0 or amplitude > 1.0:
            raise ValueError('amplitude must be in (0, 1]')
        if not math.isfinite(duration_s) or duration_s <= 0.0:
            raise ValueError('duration_s must be positive')
        if not math.isfinite(prbs_hold_s) or prbs_hold_s <= 0.0:
            raise ValueError('prbs_hold_s must be positive')
        if chirp_start_hz <= 0.0 or chirp_end_hz <= 0.0:
            raise ValueError('chirp frequencies must be positive')

        self.name = name
        self.amplitude = amplitude
        self.duration_s = duration_s
        self.prbs_hold_s = prbs_hold_s
        self.chirp_start_hz = chirp_start_hz
        self.chirp_end_hz = chirp_end_hz
        self.kind, self.axis = _profile_parts(name)

    @property
    def profile_id(self) -> int:
        return PROFILE_ID[self.name]

    def command_at(self, time_s: float) -> Command6:
        if time_s < 0.0 or time_s >= self.duration_s:
            return Command6()

        if self.kind == 'step':
            # Sign reversal halfway through reduces DC bias and gives both
            # directions in one deterministic session.
            value = self.amplitude if time_s < self.duration_s * 0.5 else -self.amplitude
            return _axis_command(self.axis, value)

        if self.kind == 'prbs':
            index = int(time_s / self.prbs_hold_s)
            bit = self._lfsr_bit(index)
            return _axis_command(self.axis, self.amplitude if bit else -self.amplitude)

        if self.kind == 'chirp':
            slope = (self.chirp_end_hz - self.chirp_start_hz) / self.duration_s
            phase = 2.0 * math.pi * (
                self.chirp_start_hz * time_s + 0.5 * slope * time_s * time_s
            )
            return _axis_command(self.axis, self.amplitude * math.sin(phase))

        raise RuntimeError('unreachable profile type')

    @staticmethod
    def _lfsr_bit(index: int) -> int:
        # 8-bit maximal-ish deterministic LFSR. Recomputed from a fixed seed
        # so output is repeatable regardless of publish rate or dropped ticks.
        state = 0xA5
        for _ in range(index + 1):
            feedback = ((state >> 7) ^ (state >> 5) ^ (state >> 4) ^ (state >> 3)) & 1
            state = ((state << 1) & 0xFF) | feedback
            if state == 0:
                state = 0xA5
        return state & 1

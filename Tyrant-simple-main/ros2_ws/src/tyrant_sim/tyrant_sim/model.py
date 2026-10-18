from dataclasses import dataclass
import math


@dataclass
class ReducedPlantConfig:
    heave_accel_per_z: float = 0.80
    heave_damping_per_s: float = 1.20

    roll_accel_per_k: float = 1.50
    roll_damping_per_s: float = 1.50
    roll_restoring_per_s2: float = 0.70

    pitch_accel_per_m: float = 1.50
    pitch_damping_per_s: float = 1.50
    pitch_restoring_per_s2: float = 0.70

    yaw_accel_per_n: float = 1.00
    yaw_damping_per_s: float = 1.20

    max_depth_m: float = 20.0
    max_angular_rate_rad_s: float = 2.0


@dataclass
class ReducedPlantState:
    depth_m: float = 0.0
    heave_velocity_mps: float = 0.0

    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0

    p_rad_s: float = 0.0
    q_rad_s: float = 0.0
    r_rad_s: float = 0.0


@dataclass
class BodyWrench:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    k: float = 0.0
    m: float = 0.0
    n: float = 0.0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def wrap_angle_rad(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def synthetic_thrusters_to_wrench(command) -> BodyWrench:
    """Reconstruct the mock TAM wrench used by teensy41-hil.

    This matrix exactly matches loadSyntheticDevelopmentGeometry() in
    firmware/teensy/include/config/thruster_config.h. It is never a
    physical Tyrant geometry model.
    """
    if len(command) != 8:
        raise ValueError('expected exactly 8 thruster commands')
    if not all(math.isfinite(float(value)) for value in command):
        raise ValueError('thruster command contains a non-finite value')

    t = [float(value) for value in command]
    return BodyWrench(
        x=t[0] + t[1],
        y=t[2] + t[3],
        z=t[4] + t[5] + t[6] + t[7],
        k=t[4] - t[5],
        m=-t[6] + t[7],
        n=-t[0] + t[1] + t[2] - t[3],
    )


class ReducedPlantModel:
    def __init__(self, config: ReducedPlantConfig, state=None):
        self.config = config
        self.state = state if state is not None else ReducedPlantState()

    def step(self, wrench: BodyWrench, dt_s: float) -> ReducedPlantState:
        if not math.isfinite(dt_s) or dt_s <= 0.0 or dt_s > 0.2:
            raise ValueError('dt_s must be finite and in (0, 0.2]')

        values = (wrench.x, wrench.y, wrench.z, wrench.k, wrench.m, wrench.n)
        if not all(math.isfinite(value) for value in values):
            raise ValueError('wrench contains a non-finite value')

        cfg = self.config
        state = self.state

        # BODY/NAV Z and depth are positive-down.
        w_dot = cfg.heave_accel_per_z * wrench.z - cfg.heave_damping_per_s * state.heave_velocity_mps
        state.heave_velocity_mps += w_dot * dt_s
        state.depth_m += state.heave_velocity_mps * dt_s

        if state.depth_m <= 0.0:
            state.depth_m = 0.0
            if state.heave_velocity_mps < 0.0:
                state.heave_velocity_mps = 0.0
        state.depth_m = min(state.depth_m, cfg.max_depth_m)

        p_dot = (
            cfg.roll_accel_per_k * wrench.k
            - cfg.roll_damping_per_s * state.p_rad_s
            - cfg.roll_restoring_per_s2 * state.roll_rad
        )
        q_dot = (
            cfg.pitch_accel_per_m * wrench.m
            - cfg.pitch_damping_per_s * state.q_rad_s
            - cfg.pitch_restoring_per_s2 * state.pitch_rad
        )
        r_dot = (
            cfg.yaw_accel_per_n * wrench.n
            - cfg.yaw_damping_per_s * state.r_rad_s
        )

        state.p_rad_s = _clamp(
            state.p_rad_s + p_dot * dt_s,
            -cfg.max_angular_rate_rad_s,
            cfg.max_angular_rate_rad_s,
        )
        state.q_rad_s = _clamp(
            state.q_rad_s + q_dot * dt_s,
            -cfg.max_angular_rate_rad_s,
            cfg.max_angular_rate_rad_s,
        )
        state.r_rad_s = _clamp(
            state.r_rad_s + r_dot * dt_s,
            -cfg.max_angular_rate_rad_s,
            cfg.max_angular_rate_rad_s,
        )

        # Small-angle HIL approximation is sufficient for controller and
        # mission plumbing validation. Vehicle model identification replaces
        # this synthetic plant before LMPC design.
        state.roll_rad = wrap_angle_rad(state.roll_rad + state.p_rad_s * dt_s)
        state.pitch_rad = wrap_angle_rad(state.pitch_rad + state.q_rad_s * dt_s)
        state.yaw_rad = wrap_angle_rad(state.yaw_rad + state.r_rad_s * dt_s)

        return state

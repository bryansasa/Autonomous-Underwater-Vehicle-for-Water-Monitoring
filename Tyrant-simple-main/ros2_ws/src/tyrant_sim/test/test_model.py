import math

from tyrant_sim.model import (
    BodyWrench,
    ReducedPlantConfig,
    ReducedPlantModel,
    synthetic_thrusters_to_wrench,
)


def test_synthetic_tam_reconstruction():
    wrench = synthetic_thrusters_to_wrench([0.2, 0.3, -0.1, 0.4, 0.2, -0.2, 0.1, -0.1])
    assert math.isclose(wrench.x, 0.5)
    assert math.isclose(wrench.y, 0.3)
    assert math.isclose(wrench.z, 0.0, abs_tol=1e-9)
    assert math.isclose(wrench.k, 0.4)
    assert math.isclose(wrench.m, -0.2)
    assert math.isclose(wrench.n, -0.4)


def test_positive_z_increases_depth():
    model = ReducedPlantModel(ReducedPlantConfig())
    for _ in range(100):
        model.step(BodyWrench(z=0.4), 0.02)
    assert model.state.depth_m > 0.0
    assert model.state.heave_velocity_mps > 0.0


def test_negative_z_surfaces_but_does_not_go_above_surface():
    model = ReducedPlantModel(ReducedPlantConfig())
    model.state.depth_m = 0.2
    for _ in range(200):
        model.step(BodyWrench(z=-0.5), 0.02)
    assert model.state.depth_m == 0.0
    assert model.state.heave_velocity_mps >= 0.0


def test_positive_yaw_wrench_increases_yaw():
    model = ReducedPlantModel(ReducedPlantConfig())
    for _ in range(50):
        model.step(BodyWrench(n=0.3), 0.02)
    assert model.state.yaw_rad > 0.0
    assert model.state.r_rad_s > 0.0


def test_roll_restoring_returns_toward_level():
    model = ReducedPlantModel(ReducedPlantConfig())
    model.state.roll_rad = 0.3
    for _ in range(250):
        model.step(BodyWrench(), 0.02)
    assert abs(model.state.roll_rad) < 0.3

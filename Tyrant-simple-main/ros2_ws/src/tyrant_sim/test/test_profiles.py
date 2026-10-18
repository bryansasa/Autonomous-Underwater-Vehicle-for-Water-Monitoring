import math
import pytest

from tyrant_sim.profiles import ExcitationProfile


def test_step_reverses_sign_halfway():
    profile = ExcitationProfile('step_surge', 0.3, 10.0)
    assert profile.command_at(1.0).surge == 0.3
    assert profile.command_at(7.0).surge == -0.3
    assert profile.command_at(10.0).surge == 0.0


def test_prbs_is_deterministic():
    a = ExcitationProfile('prbs_yaw', 0.2, 10.0, prbs_hold_s=0.5)
    b = ExcitationProfile('prbs_yaw', 0.2, 10.0, prbs_hold_s=0.5)
    values_a = [a.command_at(i * 0.5).yaw for i in range(12)]
    values_b = [b.command_at(i * 0.5).yaw for i in range(12)]
    assert values_a == values_b
    assert set(values_a).issubset({-0.2, 0.2})


def test_chirp_stays_bounded():
    profile = ExcitationProfile('chirp_yaw', 0.4, 10.0)
    for i in range(100):
        value = profile.command_at(i * 0.1).yaw
        assert abs(value) <= 0.4 + 1e-9


def test_profile_ids_preserve_existing_contract():
    assert ExcitationProfile('step_surge', 0.2, 4.0).profile_id == 1
    assert ExcitationProfile('step_yaw', 0.2, 4.0).profile_id == 6
    assert ExcitationProfile('prbs_yaw', 0.2, 4.0).profile_id == 10


def test_invalid_amplitude_rejected():
    with pytest.raises(ValueError):
        ExcitationProfile('step_yaw', 1.2, 4.0)

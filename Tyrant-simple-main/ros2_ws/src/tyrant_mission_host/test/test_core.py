from copy import deepcopy
from pathlib import Path
import math
import pytest
import yaml
from tyrant_mission_host.core import MissionEngine, validate_plan, CHANNELS

PLAN = yaml.safe_load((Path(__file__).parents[1]/'config/two_depth_hil.yaml').read_text())


def state(depth=1.0, depth_valid=True, **changes):
    return dict(depth=depth, depth_valid=depth_valid, attitude_valid=True,
                heading_valid=True, roll=0.0, pitch=0.0, yaw=0.0, status=1, **changes)


def engine():
    p = deepcopy(PLAN)
    p['steps'] = p['steps'][:1]
    e = MissionEngine(p)
    e.update_health(0, dict(communication_healthy=True, estimator_ready=True, current_mode=1))
    e.update_depth(0, state())
    e.start(0)
    handshake(e, 0)
    return e


def handshake(e, now):
    while e.pending:
        a = e.pending[1]
        e.acknowledge(a['kind'], dict(a, accepted=True), now)


def ready_sampling(e):
    e.update_depth(1, state())
    e.update_status(dict(state=2, active=True, current_step=1, current_step_type=1), 1)
    for i in range(41):
        now = 1+i/10
        e.update_depth(now, state(depth=1.0, depth_valid=True))
        e.update_health(now, dict(communication_healthy=True, estimator_ready=True, current_mode=3))
        e.tick(now)
    assert e.phase == 'SAMPLING'


def payload(seq, stamp, age=0, valid=True):
    d = dict(timestamp_us=stamp, sequence=seq)
    for name in CHANNELS.values():
        d.update({name+'_valid': valid, name+'_value': 7., name+'_age_ms': age})
    return d


def test_plan_validation_and_tolerance():
    p = deepcopy(PLAN); p['steps'][0]['tolerance'] = .02
    assert validate_plan(p)['steps'][0]['tolerance'] == .02
    for field, value in [('tolerance', 0), ('target', math.nan), ('effort', 1.1)]:
        p = deepcopy(PLAN); p['steps'][0][field] = value
        with pytest.raises(ValueError): validate_plan(p)
    p = deepcopy(PLAN); p['sensors'] = [True]
    with pytest.raises(ValueError): validate_plan(p)
    p = deepcopy(PLAN); p['steps'][0]['sample'] = 'yes'
    with pytest.raises(ValueError): validate_plan(p)


def test_correlated_ack_and_rejection():
    e = engine()
    assert e.phase == 'TRAVEL'
    e = MissionEngine(PLAN)
    e.update_health(0, dict(communication_healthy=True, estimator_ready=True, current_mode=1)); e.update_depth(0, state()); e.start(0)
    a = dict(e.pending[1])
    e.acknowledge('mode', dict(a, request_id=a['request_id']+1, accepted=True), 0)
    assert e.phase == 'CONFIGURING' and e.pending
    e.acknowledge('mode', dict(a, accepted=False, reason=4), 0)
    assert e.phase == 'FAILED'
    assert any(x.get('requested_mode') == 4 for x in e.take_actions())


def test_new_samples_only_and_reboot():
    e = engine(); ready_sampling(e)
    e.update_depth(5.1, state(depth=1., depth_valid=True))
    r = e.observe_payload(payload(1, 5_100_000), 5.1)
    assert all(r['qualified'].values())
    # Same acquisition re-published, including age rounding uncertainty.
    e.update_depth(5.2, state(depth=1., depth_valid=True))
    e.observe_payload(payload(2, 5_200_500, age=100), 5.2)
    assert set(e.counts.values()) == {1}
    e.update_depth(6.2, state(depth=1., depth_valid=True))
    r = e.observe_payload(payload(0, 100_000), 6.2)
    assert r['reboot'] and r['payload_boot'] == 1
    assert set(e.counts.values()) == {2}
    e.update_depth(7.2, state(depth=1., depth_valid=True))
    e.observe_payload(payload(1, 1_100_000), 7.2)
    assert e.phase == 'ENDING_STEP'
    handshake(e, 7.2)
    assert e.phase == 'COMPLETE'


def test_old_or_invalid_samples_not_qualified():
    e = engine(); ready_sampling(e)
    e.update_depth(5.1, state(depth=1., depth_valid=True))
    e.observe_payload(payload(1, 5_100_000, age=3000), 5.1)
    e.observe_payload(payload(2, 5_100_000, valid=False), 5.1)
    assert set(e.counts.values()) == {0}
    e.update_depth(6.1, state(depth=2., depth_valid=True))
    e.observe_payload(payload(3, 6_100_000), 6.1)
    assert set(e.counts.values()) == {0}


def test_instability_resets_gate_and_timeout_continues():
    e = engine(); ready_sampling(e)
    e.update_depth(5.1, state(depth=1.5, depth_valid=True)); e.tick(5.1)
    assert e.phase == 'STABILIZING' and e.sample_since is None
    e.update_depth(42, state(depth=1., depth_valid=True))
    e.update_health(42, dict(communication_healthy=True, estimator_ready=True, current_mode=3)); e.tick(42)
    assert e.phase == 'ENDING_STEP'
    assert not [x for x in e.events if x['event']=='step_result'][-1]['complete']
    handshake(e, 42); assert e.phase == 'COMPLETE'
    assert e.summary()['all_sampling_points_complete'] is False


def test_invalid_depth_and_lost_health_abort():
    e = engine(); ready_sampling(e)
    e.update_health(42, dict(communication_healthy=True, estimator_ready=True, current_mode=3))
    e.update_depth(42, state(depth=0., depth_valid=False)); e.tick(42)
    assert e.phase == 'FAILED'
    e = engine(); e.tick(2)
    assert e.phase == 'FAILED'


def test_at_point_policy_and_no_automatic_start():
    p = deepcopy(PLAN); p['sensor_policy'] = 'at_point'
    e = MissionEngine(p)
    assert not e.active and not e.take_actions()
    e.update_health(0, dict(communication_healthy=True, estimator_ready=True, current_mode=1)); e.update_depth(0, state()); e.start(0)
    handshake(e, 0)
    assert not any(a['kind']=='power' for a in e.take_actions())
    e.update_depth(1, state())
    e.update_status(dict(state=2, active=True, current_step=1, current_step_type=1), 1)
    assert any(a['kind']=='power' and a['enable'] for a in e.take_actions())
    e.stop(2)
    assert e.phase == 'STOPPED' and any(a['kind']=='power' and not a['enable'] for a in e.take_actions())


def test_motion_timeout_and_wait_completion():
    e = engine()
    e.update_depth(91, state())
    e.update_health(91, dict(communication_healthy=True, estimator_ready=True, current_mode=3)); e.tick(91)
    assert e.phase == 'FAILED'
    e = engine()
    e.update_depth(1, state())
    e.update_status(dict(state=3, active=False, current_step=2, current_step_type=1), 1)
    assert e.phase == 'ENDING_STEP'


def test_external_safe_and_command_timeout():
    e = engine()
    e.update_depth(1, state())
    e.update_health(1, dict(communication_healthy=True, estimator_ready=True, current_mode=4))
    e.tick(1)
    assert e.phase == 'FAILED'
    e = MissionEngine(PLAN)
    e.update_health(0, dict(communication_healthy=True, estimator_ready=True, current_mode=1)); e.update_depth(0, state()); e.start(0)
    e.update_depth(4, state())
    e.update_health(4, dict(communication_healthy=True, estimator_ready=True, current_mode=1)); e.tick(4)
    assert e.phase == 'FAILED' and e.result == 'Command ACK timeout'


def test_start_rejects_unhealthy_or_manual_board():
    e = MissionEngine(PLAN)
    with pytest.raises(ValueError): e.start(0)
    e.update_health(0, dict(communication_healthy=True, estimator_ready=True, current_mode=2))
    with pytest.raises(ValueError): e.start(0)


def assert_abort_commands(e):
    actions = e.take_actions()
    assert [a['command'] for a in actions if a['kind']=='mission'] == [3]
    assert [a['requested_mode'] for a in actions if a['kind']=='mode'] == [4]
    assert all(not a['enable'] for a in actions if a['kind']=='power')
    assert not e.pending and not e.queue


@pytest.mark.parametrize('bad_field', ['depth_valid', 'attitude_valid', 'heading_valid', 'yaw', 'status'])
def test_invalid_state_immediately_aborts_timed_motion(bad_field):
    plan = deepcopy(PLAN); plan['steps'] = [plan['steps'][1], plan['steps'][2]]
    e = MissionEngine(plan)
    e.update_depth(0, state()); e.update_health(0, dict(communication_healthy=True, estimator_ready=True, current_mode=1))
    e.start(0); handshake(e, 0); e.take_actions()
    bad = state()
    bad[bad_field] = math.nan if bad_field=='yaw' else (3 if bad_field=='status' else False)
    e.update_depth(.1, bad)
    assert e.phase == 'FAILED' and e.result == 'Teensy state invalid'
    assert e.step_results[-1]['step_id']=='forward' and not e.step_results[-1]['complete']
    assert_abort_commands(e)
    # Timed completion arriving after invalidation cannot advance to sway.
    e.update_status(dict(state=3, active=False, current_step=1, current_step_type=2), .11)
    assert e.phase == 'FAILED' and e.index==0 and not e.take_actions()


def test_not_ready_health_aborts_before_timer_or_completion():
    e = engine(); e.take_actions()
    e.update_health(.1, dict(communication_healthy=True, estimator_ready=False, current_mode=3))
    assert e.phase == 'FAILED' and e.result == 'Teensy estimator not ready'
    assert_abort_commands(e)


def test_stale_state_aborts_even_when_health_and_heartbeat_are_fresh():
    e = engine(); e.take_actions()
    e.update_health(.4, dict(communication_healthy=True, estimator_ready=True, current_mode=3))
    e.tick(.501)
    assert e.phase == 'FAILED' and e.result == 'Teensy state stale or missing'
    assert_abort_commands(e)


def test_invalid_state_drops_pending_auto_and_late_ack():
    e = MissionEngine(PLAN)
    e.update_depth(0, state()); e.update_health(0, dict(communication_healthy=True, estimator_ready=True, current_mode=1)); e.start(0)
    while e.pending[1].get('requested_mode') != 3:
        a = e.pending[1]; e.acknowledge(a['kind'], dict(a, accepted=True), 0)
    auto = dict(e.pending[1])
    e.update_depth(.1, state(depth_valid=False))
    assert_abort_commands(e)
    e.acknowledge('mode', dict(auto, accepted=True), .11)
    assert e.phase == 'FAILED' and not e.take_actions()


def test_invalid_during_sampling_does_not_count_payload_and_preserves_manual_mode():
    e = engine(); ready_sampling(e); e.take_actions()
    e.update_depth(5.1, state(depth_valid=False))
    result = e.observe_payload(payload(1,5_100_000),5.1)
    assert not any(result['qualified'].values()) and set(e.counts.values()) == {0}
    assert_abort_commands(e)
    e = MissionEngine(PLAN)
    e.update_depth(0, state(depth_valid=False))
    e.update_health(0, dict(communication_healthy=True, estimator_ready=False, current_mode=2))
    assert e.phase=='IDLE' and not e.take_actions()

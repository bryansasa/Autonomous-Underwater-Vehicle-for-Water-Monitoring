"""ROS-independent mission sequencing and conservative acquisition-time association."""
from collections import deque
from copy import deepcopy
import math

CHANNELS = {1: 'conductivity', 2: 'ph', 3: 'temperature', 4: 'dissolved_oxygen'}
STEP_TYPES = {'wait': 1, 'surge': 2, 'sway': 3, 'dive': 4, 'heading': 5, 'surface': 6}
DEFAULT_SAMPLING = dict(target_samples=3, timeout_s=40.0, stable_s=3.0,
                        stable_span_m=0.05, depth_fresh_s=0.5, sample_max_age_s=6.5)


def positive(value, name, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite numeric')
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f'{name} must be positive')
    return value


def validate_plan(raw):
    if not isinstance(raw, dict):
        raise ValueError('Mission must be a mapping')
    plan = deepcopy(raw)
    if not isinstance(plan.get('mission_id'), str) or not plan['mission_id'].strip():
        raise ValueError('mission_id is required')
    if plan.get('sensor_policy', 'throughout') not in ('throughout', 'at_point'):
        raise ValueError('Unknown sensor_policy')
    plan.setdefault('sensor_policy', 'throughout')
    sensors = plan.setdefault('sensors', [1, 2, 3, 4])
    if not isinstance(sensors, list) or not sensors or any(type(i) is not int or i not in CHANNELS for i in sensors) or len(set(sensors)) != len(sensors):
        raise ValueError('sensors must contain unique IDs 1..4')
    settings = {**DEFAULT_SAMPLING, **plan.get('sampling', {})}
    for key in DEFAULT_SAMPLING:
        positive(settings[key], key)
    if type(settings['target_samples']) is not int:
        raise ValueError('target_samples must be an integer')
    plan['sampling'] = settings
    steps = plan.get('steps')
    if not isinstance(steps, list) or not steps or len(steps) > 100:
        raise ValueError('Mission requires 1..100 host steps')
    ids = set()
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get('id'), str) or not step['id'] or step['id'] in ids:
            raise ValueError('Each step requires a unique string id')
        ids.add(step['id'])
        kind = step.get('type')
        if kind not in STEP_TYPES:
            raise ValueError('Unknown step type')
        positive(step.get('timeout_s'), 'timeout_s')
        if type(step.get('sample', False)) is not bool:
            raise ValueError('sample must be boolean')
        if step.get('sample') and kind not in ('dive', 'surface'):
            raise ValueError('Sampling is supported only at depth steps')
        if kind in ('wait', 'surge', 'sway'):
            positive(step.get('duration_s'), 'duration_s')
            if step['timeout_s'] <= step['duration_s']:
                raise ValueError('timeout_s must exceed duration_s')
        if kind != 'wait':
            effort = step.get('effort')
            if not isinstance(effort, (float, int)) or isinstance(effort, bool) or not math.isfinite(effort) or not 0 < abs(effort) <= 1:
                raise ValueError('effort must be nonzero and in [-1, 1]')
        if kind in ('dive', 'surface', 'heading'):
            target = step.get('target')
            if not isinstance(target, (float, int)) or isinstance(target, bool) or not math.isfinite(target):
                raise ValueError('target must be finite')
            if kind != 'heading' and not 0 <= target <= 10:
                raise ValueError('Depth target must be within existing controller range 0..10 m')
            positive(step.get('tolerance'), 'tolerance')
            if kind == 'heading' and step['tolerance'] >= math.pi:
                raise ValueError('Heading tolerance must be below pi')
        for key in ('planned_x', 'planned_y'):
            if key in step and (type(step[key]) not in (float, int) or not math.isfinite(step[key])):
                raise ValueError(f'{key} must be finite')
        if 'sampling' in step:
            override = {**settings, **step['sampling']}
            for key in DEFAULT_SAMPLING:
                positive(override[key], key)
            if type(override['target_samples']) is not int:
                raise ValueError('target_samples must be integer')
            step['sampling'] = override
        # Teensy duration is uint32 milliseconds, including the inserted WAIT.
        max_wait = step.get('sampling', settings)['timeout_s'] + 5
        if max(step.get('duration_s', 0), step['timeout_s'], max_wait) * 1000 >= 2**32:
            raise ValueError('Duration exceeds Teensy uint32 milliseconds')
    return plan


class MissionEngine:
    def __init__(self, plan, request_base=100000):
        self.plan = validate_plan(plan)
        self.phase = 'IDLE'
        self.index = -1
        self.request_id = request_base
        self.pending = None
        self.queue = deque()
        self.actions = []
        self.events = []
        self.depth_history = deque()
        self.health = None
        self.depth = None
        self.state = None
        self.status = None
        self.counts = {}
        self.last_samples = {}
        self.payload_boot = 0
        self.last_payload = None
        self.stable_since = None
        self.sample_since = None
        self.run_since = None
        self.point_since = None
        self.result = None
        self.step_results = []

    @property
    def step(self):
        return self.plan['steps'][self.index] if self.index >= 0 else None

    @property
    def settings(self):
        return self.step.get('sampling', self.plan['sampling']) if self.step else self.plan['sampling']

    @property
    def active(self):
        return self.phase not in ('IDLE', 'COMPLETE', 'FAILED', 'STOPPED')

    def event(self, kind, now, **data):
        self.events.append(dict(event=kind, monotonic_s=now, step_id=self.step['id'] if self.step else None, **data))

    def take_actions(self):
        out, self.actions = self.actions, []
        return out

    def update_health(self, now, data):
        self.health = (now, data)
        self.abort_invalid_state(now)

    def update_depth(self, now, data):
        required_valid = ('attitude_valid', 'heading_valid', 'depth_valid')
        required_values = ('roll', 'pitch', 'yaw', 'depth')
        ready = (all(data.get(key, False) for key in required_valid) and
                 all(math.isfinite(data.get(key, math.nan)) for key in required_values) and
                 data.get('status') != 3)
        self.state = (now, ready)
        valid = data['depth_valid'] and math.isfinite(data['depth'])
        self.depth = (now, data['depth'], valid)
        self.depth_history.append(self.depth)
        while self.depth_history and now-self.depth_history[0][0] > 20:
            self.depth_history.popleft()
        self.abort_invalid_state(now)

    def state_problem(self, now):
        if self.health and not self.health[1]['estimator_ready']:
            return 'Teensy estimator not ready'
        if not self.state or now-self.state[0] > self.settings['depth_fresh_s']:
            return 'Teensy state stale or missing'
        if not self.state[1]:
            return 'Teensy state invalid'
        return None

    def abort_invalid_state(self, now):
        if not self.active:
            return False
        problem = self.state_problem(now)
        if problem:
            self.finish('FAILED', now, problem)
            return True
        return False

    def fresh_depth(self, now):
        return self.depth and self.depth[2] and now-self.depth[0] <= self.settings['depth_fresh_s']

    def in_target(self, now):
        return self.fresh_depth(now) and abs(self.depth[1]-self.step['target']) <= self.step['tolerance']

    def start(self, now):
        if self.active:
            raise ValueError('Mission already active')
        if not self.health or now-self.health[0] > 1 or not self.health[1]['communication_healthy'] or not self.health[1]['estimator_ready']:
            raise ValueError('Fresh healthy Teensy telemetry is required')
        if self.health[1]['current_mode'] not in (1, 4):
            raise ValueError('Start requires Teensy IDLE or SAFE')
        problem = self.state_problem(now)
        if problem:
            raise ValueError(problem)
        self.index = -1
        self.result = None
        self.step_results = []
        self.event('mission_started', now)
        if self.plan['sensor_policy'] == 'throughout':
            self.actions.append(dict(kind='power', enable=True))
        self.next_step(now)

    def command(self, kind, **data):
        self.queue.append(dict(kind=kind, **data))

    def next_step(self, now):
        self.index += 1
        if self.index == len(self.plan['steps']):
            self.index -= 1
            self.finish('COMPLETE', now, 'All host steps finished')
            return
        self.phase = 'CONFIGURING'
        self.status = None
        self.run_since = self.point_since = self.sample_since = self.stable_since = None
        self.counts = {CHANNELS[i]: 0 for i in self.plan['sensors']}
        self.last_samples = {}
        self.queue.clear()
        self.command('mode', requested_mode=4)
        self.command('mission', command=0)
        step = self.step
        self.command('mission', command=1, step_type=STEP_TYPES[step['type']],
                     target=step.get('target', 0.0), effort=step.get('effort', 0.0),
                     tolerance=step.get('tolerance', 0.0), duration_ms=round(step.get('duration_s', 0)*1000))
        if step.get('sample'):
            # WAIT preserves the existing stabilized controller while host samples.
            self.command('mission', command=1, step_type=1,
                         duration_ms=math.ceil((self.settings['timeout_s']+5)*1000))
        self.command('mode', requested_mode=1)
        self.command('mode', requested_mode=3)
        self.command('mission', command=2)
        self.event('step_configuring', now)
        self.dispatch(now)

    def dispatch(self, now):
        if self.pending or not self.queue:
            return
        action = self.queue.popleft()
        self.request_id = (self.request_id + 1) % (2**32) or 1
        action['request_id'] = self.request_id
        self.pending = (now, action)
        self.actions.append(action)

    def acknowledge(self, kind, data, now):
        if self.abort_invalid_state(now):
            return
        if not self.pending:
            return
        action = self.pending[1]
        if kind != action['kind'] or data['request_id'] != action['request_id']:
            return
        # A matching request ID alone is insufficient when other controllers exist.
        selector = 'command' if kind == 'mission' else 'requested_mode'
        if data.get(selector) != action[selector]:
            return
        accepted = data['accepted']
        self.pending = None
        if not accepted:
            self.finish('FAILED', now, f'{kind} rejected, reason={data.get("reason")}')
            return
        if self.phase == 'ENDING_STEP':
            self.next_step(now)
            return
        if not self.queue:
            self.phase = 'TRAVEL'
            self.run_since = now
            self.event('step_started', now)
        else:
            self.dispatch(now)

    def update_status(self, data, now):
        if self.abort_invalid_state(now):
            return
        if self.phase not in ('TRAVEL', 'STABILIZING', 'SAMPLING'):
            return
        self.status = data
        if data['state'] in (4, 5):
            self.finish('FAILED', now, 'Teensy mission stopped or failed')
        elif data['state'] == 3:
            if self.step.get('sample'):
                self.end_step(now, False, 'Teensy WAIT ended before sampling completion')
            else:
                self.end_step(now, True, 'Motion completed')
        elif self.phase == 'TRAVEL' and self.step.get('sample') and data['active'] and data['current_step'] == 1 and data['current_step_type'] == 1:
            self.phase = 'STABILIZING'
            self.point_since = now
            self.stable_since = None
            if self.plan['sensor_policy'] == 'at_point':
                self.actions.append(dict(kind='power', enable=True))
            self.event('point_reached_wait', now)

    def end_step(self, now, complete, reason):
        if self.phase == 'ENDING_STEP':
            return
        self.event('step_result', now, complete=complete, reason=reason, counts=dict(self.counts))
        self.step_results.append(dict(step_id=self.step['id'], sampling=bool(self.step.get('sample')),
                                      complete=complete, reason=reason, counts=dict(self.counts)))
        if self.step.get('sample') and self.plan['sensor_policy'] == 'at_point':
            self.actions.append(dict(kind='power', enable=False))
        self.phase = 'ENDING_STEP'
        self.pending = None
        self.queue.clear()
        self.command('mission', command=3)
        self.dispatch(now)

    def finish(self, phase, now, reason):
        if phase == 'FAILED' and self.step and not any(s['step_id'] == self.step['id'] for s in self.step_results):
            self.event('step_result', now, complete=False, reason=reason, counts=dict(self.counts))
            self.step_results.append(dict(step_id=self.step['id'], sampling=bool(self.step.get('sample')),
                                          complete=False, reason=reason, counts=dict(self.counts)))
        self.phase = phase
        self.result = reason
        self.pending = None
        self.queue.clear()
        # Discard unsent motion/ON actions before emitting only stop commands.
        self.actions.clear()
        # Independent stop + SAFE requests remain necessary if telemetry/ACK vanished.
        for kind, data in [('mission', dict(command=3)), ('mode', dict(requested_mode=4))]:
            self.request_id = (self.request_id+1) % (2**32) or 1
            self.actions.append(dict(kind=kind, request_id=self.request_id, **data))
        self.actions.append(dict(kind='power', enable=False))
        self.event('mission_result', now, state=phase, reason=reason)

    def stop(self, now):
        if self.active:
            self.finish('STOPPED', now, 'Operator requested stop')

    def tick(self, now):
        if not self.active:
            return
        if not self.health or now-self.health[0] > 1 or not self.health[1]['communication_healthy'] or self.health[1]['current_mode'] in (5, 6):
            self.finish('FAILED', now, 'Teensy communication lost or fault/emergency')
            return
        if self.abort_invalid_state(now):
            return
        if self.pending:
            if now-self.pending[0] > 3:
                self.finish('FAILED', now, 'Command ACK timeout')
            return
        if self.phase in ('TRAVEL', 'STABILIZING', 'SAMPLING') and self.health[1]['current_mode'] != 3 and now-self.run_since > 0.5:
            self.finish('FAILED', now, 'Unexpected Teensy mode change')
            return
        if self.phase == 'TRAVEL' and now-self.run_since > self.step['timeout_s']:
            self.finish('FAILED', now, 'Motion/depth arrival timeout')
        elif self.phase in ('STABILIZING', 'SAMPLING'):
            if now-self.point_since >= self.settings['timeout_s']:
                # Invalid depth cannot be qualified as an incomplete payload point.
                if not self.fresh_depth(now):
                    self.finish('FAILED', now, 'Depth invalid/stale at point timeout')
                else:
                    self.end_step(now, False, 'Sampling/stabilization timeout')
                return
            if not self.in_target(now):
                self.phase = 'STABILIZING'
                self.stable_since = None
                self.sample_since = None
                return
            if self.phase == 'STABILIZING':
                if self.stable_since is None:
                    self.stable_since = now
                window = [v for t,v,ok in self.depth_history if t >= self.stable_since and ok]
                if len(window) >= 2 and max(window)-min(window) > self.settings['stable_span_m']:
                    self.stable_since = now
                elif now-self.stable_since >= self.settings['stable_s'] and len(window) >= 2:
                    self.phase = 'SAMPLING'
                    self.sample_since = now
                    self.event('sampling_started', now)

    def observe_payload(self, data, now):
        self.abort_invalid_state(now)
        stamp, seq = data['timestamp_us'], data['sequence']
        reboot = False
        if self.last_payload and stamp < self.last_payload[0] and seq <= self.last_payload[1]:
            self.payload_boot += 1
            self.last_samples = {}
            reboot = True
            self.event('payload_session_changed', now, payload_boot=self.payload_boot)
            if self.active and (self.plan['sensor_policy'] == 'throughout' or self.phase in ('STABILIZING', 'SAMPLING')):
                self.actions.append(dict(kind='power', enable=True))
        self.last_payload = (stamp, seq)
        qualified = {}
        associated = {}
        for name in CHANNELS.values():
            age = data[name+'_age_ms']
            acquisition_rx = now-age/1000 if age != 2**32-1 else None
            # Approximate host receive-time association; not clock synchronization.
            candidates = [x for x in self.depth_history if acquisition_rx is not None and x[0] <= acquisition_rx]
            match = candidates[-1] if candidates else None
            valid_depth = bool(match and match[2] and acquisition_rx-match[0] <= self.settings['depth_fresh_s'])
            associated[name] = dict(depth=match[1] if valid_depth else None,
                                    depth_valid=valid_depth, estimated_acquisition_host_s=acquisition_rx)
            ok = bool(self.phase == 'SAMPLING' and self.sample_since is not None and
                      data[name+'_valid'] and math.isfinite(data[name+'_value']) and
                      age <= self.settings['sample_max_age_s']*1000 and
                      acquisition_rx >= self.sample_since and valid_depth and
                      abs(match[1]-self.step['target']) <= self.step['tolerance'] and self.in_target(now))
            sample_key = (self.payload_boot, stamp-age*1000)
            previous = self.last_samples.get(name)
            # age_ms truncates sub-millisecond timing: tolerate that uncertainty.
            is_new = previous is None or sample_key[0] != previous[0] or sample_key[1]-previous[1] >= 500000
            qualified[name] = ok and is_new and name in self.counts
            if data[name+'_valid'] and is_new:
                self.last_samples[name] = sample_key
            if qualified[name]:
                self.counts[name] += 1
        if self.phase == 'SAMPLING' and all(n >= self.settings['target_samples'] for n in self.counts.values()):
            self.end_step(now, True, 'Per-sensor valid sample targets met')
        return dict(payload_boot=self.payload_boot, reboot=reboot, qualified=qualified, associated=associated)

    def summary(self):
        return dict(mission_id=self.plan['mission_id'], phase=self.phase,
                    step_id=self.step['id'] if self.step else None, counts=self.counts,
                    payload_boot=self.payload_boot, result=self.result, step_results=self.step_results,
                    all_sampling_points_complete=(all(s['complete'] for s in self.step_results if s['sampling'])
                                                  if self.phase == 'COMPLETE' else None))

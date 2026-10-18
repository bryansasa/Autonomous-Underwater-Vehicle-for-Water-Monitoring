"""Exercise actual ROS types, callbacks, services and rosbag using fake board endpoints.
Run on an isolated ROS_DOMAIN_ID; this does not model vehicle dynamics or access USB.
"""
import csv
import json
from pathlib import Path
import tempfile
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
import rosbag2_py
from std_msgs.msg import UInt32
from std_srvs.srv import Trigger
from tyrant_interfaces.msg import SimpleState, SystemHealth, MissionStatus, ModeStatus, MissionCommand, ModeRequest
from tyrant_payload_interfaces.msg import PayloadWaterQuality, SensorPowerRequest, SensorPowerStatus
from tyrant_mission_host.node import MissionHost
import yaml


class FakeBoards(Node):
    def __init__(self):
        super().__init__('fake_boards')
        self.mode = 1; self.active = False; self.wait = False; self.started = 0
        self.queue = []; self.enabled = {i: False for i in range(1,5)}
        self.hb = [0,0]; self.seq = 0; self.last_payload = 0
        self.created = time.monotonic()
        self.failed_sensor = None
        self.state_valid = True
        self.publish_state = True
        self.motion_runtime = .1
        self.state_pub = self.create_publisher(SimpleState, '/tyrant/simple_state', 10)
        self.health_pub = self.create_publisher(SystemHealth, '/tyrant/system/health', 10)
        self.mission_pub = self.create_publisher(MissionStatus, '/tyrant/mission/status', 10)
        self.mode_pub = self.create_publisher(ModeStatus, '/tyrant/mode/status', 10)
        self.water_pub = self.create_publisher(PayloadWaterQuality, '/tyrant/payload_sim/water_quality', 10)
        self.power_pub = self.create_publisher(SensorPowerStatus, '/tyrant/payload_sim/sensor_power/status', 10)
        self.create_subscription(MissionCommand, '/tyrant/mission/command', self.mission, 10)
        self.create_subscription(ModeRequest, '/tyrant/mode/request', self.mode_request, 10)
        self.create_subscription(SensorPowerRequest, '/tyrant/payload_sim/sensor_power/request', self.power, 10)
        self.create_subscription(UInt32, '/tyrant/host_heartbeat', lambda m: self.heartbeat(0), 10)
        self.create_subscription(UInt32, '/tyrant/payload_sim/host_heartbeat', lambda m: self.heartbeat(1), 10)
        self.create_timer(.05, self.tick)

    def heartbeat(self, index): self.hb[index] += 1

    def mode_request(self, req):
        self.mode = req.requested_mode
        self.mode_pub.publish(ModeStatus(request_id=req.request_id, requested_mode=self.mode,
            current_mode=self.mode, request_accepted=True, reason=1, communication_healthy=True))

    def mission(self, req):
        if req.command == 0: self.queue = []
        elif req.command == 1: self.queue.append(req)
        elif req.command == 2:
            self.active = True; self.started = time.monotonic(); self.wait = len(self.queue) == 2
        elif req.command == 3: self.active = False; self.mode = 4
        self.mission_pub.publish(MissionStatus(request_id=req.request_id, command=req.command,
            accepted=True, state=2 if self.active else 1, step_count=len(self.queue), active=self.active,
            current_step=0, current_step_type=self.queue[0].step_type if self.queue else 0))

    def power(self, req):
        self.enabled[req.sensor_id] = req.enable
        self.power_pub.publish(SensorPowerStatus(request_id=req.request_id, sensor_id=req.sensor_id,
            requested_enable=req.enable, accepted=True, reason=1, actual_enabled=req.enable))

    def tick(self):
        now = time.monotonic()
        if self.publish_state:
            self.state_pub.publish(SimpleState(timestamp_us=int((now-self.created)*1e6), status=1 if self.state_valid else 2,
                depth=1., depth_valid=self.state_valid, attitude_valid=self.state_valid, heading_valid=self.state_valid))
        self.health_pub.publish(SystemHealth(communication_healthy=True, estimator_ready=self.state_valid,
            autonomy_ready=True, current_mode=self.mode, propulsion_allowed=self.mode==3))
        if self.active and now-self.started > (.1 if self.wait else self.motion_runtime):
            if self.wait:
                self.mission_pub.publish(MissionStatus(state=2, active=True, current_step=1, current_step_type=1))
            else:
                self.mission_pub.publish(MissionStatus(state=3, active=False, current_step=1))
                self.active = False; self.mode = 4
        if now-self.last_payload >= .6:
            self.last_payload = now
            m = PayloadWaterQuality(timestamp_us=int((now-self.created)*1e6), sequence=self.seq,
                 conductivity_us_cm=1200., ph=7.2, temperature_c=26., dissolved_oxygen_mg_l=7.5)
            for name,i in [('conductivity',1),('ph',2),('temperature',3),('dissolved_oxygen',4)]:
                valid = self.enabled[i] and i != self.failed_sensor
                setattr(m,name+'_valid',valid); setattr(m,name+'_state',2 if valid else 4)
            self.water_pub.publish(m); self.seq += 1


def main():
    root = Path(tempfile.mkdtemp(prefix='tyrant-host-smoke-'))
    plan = dict(mission_id='ros_smoke', sensor_policy='throughout', sensors=[1,2,3,4],
                sampling=dict(target_samples=2, stable_s=.2, timeout_s=5.),
                steps=[dict(id='sample_1', type='dive', target=1., tolerance=.1, effort=.5, timeout_s=5., sample=True),
                       dict(id='move', type='surge', effort=.2, duration_s=.1, timeout_s=2.)])
    path = root/'plan.yaml'; path.write_text(yaml.safe_dump(plan))
    rclpy.init(args=['--ros-args','-p','plan:='+str(path),'-p','output_dir:='+str(root/'sessions')])
    host = MissionHost(); boards = FakeBoards(); executor = SingleThreadedExecutor()
    executor.add_node(host); executor.add_node(boards)
    def until(condition, timeout=10):
        deadline = time.monotonic()+timeout
        while not condition() and time.monotonic()<deadline: executor.spin_once(timeout_sec=.05)
        assert condition(), host.engine.summary()
    def call(service):
        client = boards.create_client(Trigger, service)
        assert client.wait_for_service(timeout_sec=2)
        future = client.call_async(Trigger.Request()); until(future.done)
        result = future.result(); assert result.success, result.message
        return result
    try:
        until(lambda: host.engine.health is not None and all(boards.hb))
        assert host.engine.phase == 'IDLE' and not boards.active
        result = call('/tyrant/host/mission/start'); session = Path(result.message)
        until(lambda: host.engine.phase in ('COMPLETE','FAILED'))
        assert host.engine.phase == 'COMPLETE', host.engine.summary()
        until(lambda: host.recorder is None)
        metadata = json.loads((session/'session.json').read_text())
        assert metadata['payload_simulated'] and metadata['teensy_simulated']
        rows = list(csv.DictReader((session/'samples.csv').open()))
        assert len([r for r in rows if r['qualified_point_sample']=='True']) == 8
        assert all(not r['planned_x'] and not r['planned_y'] for r in rows)
        events = [json.loads(line) for line in (session/'events.jsonl').read_text().splitlines()]
        assert len([e for e in events if e['event']=='step_result']) == 2
        reader = rosbag2_py.SequentialReader()
        reader.open(rosbag2_py.StorageOptions(uri=str(session/'bag'),storage_id='sqlite3'),rosbag2_py.ConverterOptions('',''))
        counts = {}
        while reader.has_next():
            topic,_,_ = reader.read_next(); counts[topic] = counts.get(topic,0)+1
        assert counts['/tyrant/mission/command'] >= 10
        assert counts['/tyrant/payload_sim/water_quality'] > 0
        assert counts['/tyrant/host_heartbeat'] > 0
        del reader
        result = call('/tyrant/host/recording/start'); manual = Path(result.message)
        until(lambda: len(list(csv.DictReader((manual/'samples.csv').open()))) >= 4)
        call('/tyrant/host/recording/stop')
        rows = list(csv.DictReader((manual/'samples.csv').open()))
        assert all(r['phase']=='MANUAL' and r['qualified_point_sample']=='False' for r in rows)
        assert all(not r['target_depth'] for r in rows)
        host.engine.plan['sensor_policy'] = 'at_point'
        host.engine.plan['sampling']['timeout_s'] = 2.0
        boards.failed_sensor = 1
        result = call('/tyrant/host/mission/start'); incomplete = Path(result.message)
        until(lambda: host.engine.phase in ('COMPLETE','FAILED'))
        assert host.engine.phase == 'COMPLETE', host.engine.summary()
        until(lambda: host.recorder is None)
        events = [json.loads(line) for line in (incomplete/'events.jsonl').read_text().splitlines()]
        results = [e for e in events if e['event']=='step_result']
        assert len(results) == 2 and not results[0]['complete'] and results[1]['complete']
        assert any(e['event']=='sensor_power_ack' and e['actual_enabled'] for e in events)
        boards.failed_sensor = None
        boards.motion_runtime = 10.0
        host.engine.plan['sampling']['timeout_s'] = 5.0
        for fault in ('invalid', 'stale'):
            result = call('/tyrant/host/mission/start'); stopped = Path(result.message)
            until(lambda: host.engine.phase=='TRAVEL' and host.engine.step['id']=='move')
            injected = time.monotonic()
            if fault=='invalid':
                boards.state_valid = False
            else:
                boards.publish_state = False  # health remains ready and heartbeat continues
            until(lambda: host.engine.phase=='FAILED', timeout=2)
            delay = time.monotonic()-injected
            assert delay < (1.0 if fault=='invalid' else 1.5), delay
            assert 'Teensy state' in host.engine.result or host.engine.result=='Teensy estimator not ready'
            until(lambda: boards.mode==4 and not boards.active and not any(boards.enabled.values()))
            until(lambda: host.recorder is None)
            metadata = json.loads((stopped/'session.json').read_text())
            move = [s for s in metadata['result']['step_results'] if s['step_id']=='move']
            assert len(move)==1 and not move[0]['complete']
            events = [json.loads(line) for line in (stopped/'events.jsonl').read_text().splitlines()]
            assert len([e for e in events if e['event']=='mission_result'])==1
            boards.state_valid = True; boards.publish_state = True
            until(lambda: host.engine.state[1] and host.engine.health[1]['estimator_ready'])
            print(f'PASS ROS: {fault} state during motion aborts in {delay:.3f}s; STOP/SAFE/OFF received and failed step recorded')
        print('PASS ROS: explicit start, two board heartbeats, sequential power ACK, two host steps, per-sensor sampling, finalized bag/CSV, manual recording')
        print('PASS ROS: at-point power policy, failed sensor marks incomplete point, mission continues to motion step')
        print('Artifacts:', root)
    finally:
        host.shutdown_session(); executor.shutdown(); host.destroy_node(); boards.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__': main()

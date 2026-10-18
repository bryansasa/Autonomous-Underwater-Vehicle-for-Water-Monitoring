"""Explicit service-started mission coordinator; no GUI or physical LMPC controller."""
import json
from collections import deque
from pathlib import Path
import secrets
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.serialization import serialize_message
from rosidl_runtime_py.utilities import get_message
from std_msgs.msg import UInt32, String
from std_srvs.srv import Trigger
import rosbag2_py
import yaml

from .core import CHANNELS, MissionEngine
from .recording import SessionRecorder, clean

TEENSY_TOPICS = {
    '/tyrant/simple_state': 'tyrant_interfaces/msg/SimpleState',
    '/tyrant/system/health': 'tyrant_interfaces/msg/SystemHealth',
    '/tyrant/mode/status': 'tyrant_interfaces/msg/ModeStatus',
    '/tyrant/mission/status': 'tyrant_interfaces/msg/MissionStatus',
    '/tyrant/sensors/imu': 'tyrant_interfaces/msg/ImuTelemetry',
    '/tyrant/sensors/pressure': 'tyrant_interfaces/msg/PressureTelemetry',
    '/tyrant/communication/diagnostics': 'tyrant_interfaces/msg/CommunicationDiagnostics',
    '/tyrant/control/wrench_request': 'tyrant_interfaces/msg/WrenchRequest',
    '/tyrant/control/thruster_command': 'tyrant_interfaces/msg/ThrusterCommand',
    '/tyrant/actuation/status': 'tyrant_interfaces/msg/ActuatorStatus',
    '/tyrant/emergency/status': 'tyrant_interfaces/msg/EmergencyStatus',
}
PAYLOAD_TOPICS = {
    'water_quality': 'PayloadWaterQuality', 'power/sensors': 'PayloadPower',
    'power/thruster': 'PayloadPower', 'health': 'PayloadHealth',
    'communication/diagnostics': 'PayloadCommunicationDiagnostics',
    'sensor_power/status': 'SensorPowerStatus', 'heartbeat': 'std_msgs/msg/UInt32',
}
VALUE_FIELDS = dict(conductivity='conductivity_us_cm', ph='ph',
                    temperature='temperature_c', dissolved_oxygen='dissolved_oxygen_mg_l')


def fields(message):
    return {key: getattr(message, key) for key in message.get_fields_and_field_types()}


class MissionHost(Node):
    def __init__(self):
        super().__init__('tyrant_mission_host')
        self.declare_parameter('plan', '')
        self.declare_parameter('payload_namespace', '/tyrant/payload_sim')
        self.declare_parameter('teensy_simulated', True)
        self.declare_parameter('output_dir', str(Path.home()/'tyrant_missions'))
        self.declare_parameter('publish_heartbeats', True)
        plan_path = Path(self.get_parameter('plan').value)
        if not plan_path.is_file():
            raise ValueError('Set plan to a mission YAML file')
        self.engine = MissionEngine(yaml.safe_load(plan_path.read_text()), secrets.randbelow(2**30)+100000)
        self.payload_ns = self.get_parameter('payload_namespace').value.rstrip('/')
        if self.payload_ns not in ('/tyrant/payload', '/tyrant/payload_sim'):
            raise ValueError('Use the hardware or simulation payload namespace')
        self.topics = dict(TEENSY_TOPICS)
        for suffix, type_name in PAYLOAD_TOPICS.items():
            self.topics[self.payload_ns+'/'+suffix] = type_name if '/' in type_name else 'tyrant_payload_interfaces/msg/'+type_name
        self.topics.update({
            '/tyrant/mission/command': 'tyrant_interfaces/msg/MissionCommand',
            '/tyrant/mode/request': 'tyrant_interfaces/msg/ModeRequest',
            self.payload_ns+'/sensor_power/request': 'tyrant_payload_interfaces/msg/SensorPowerRequest',
            '/tyrant/host_heartbeat': 'std_msgs/msg/UInt32',
            self.payload_ns+'/host_heartbeat': 'std_msgs/msg/UInt32',
            '/tyrant/host/mission/status': 'std_msgs/msg/String',
        })
        self.pubs = {}
        for topic in ('/tyrant/mission/command', '/tyrant/mode/request',
                      self.payload_ns+'/sensor_power/request', '/tyrant/host_heartbeat',
                      self.payload_ns+'/host_heartbeat', '/tyrant/host/mission/status'):
            self.pubs[topic] = self.create_publisher(get_message(self.topics[topic]), topic, 10)
        self.subs = [self.create_subscription(get_message(type_name), topic,
                     lambda message, topic=topic: self.receive(topic, message), qos_profile_sensor_data)
                     for topic,type_name in self.topics.items()]
        self.recorder = None
        self.record_only = False
        self.power_pending = None
        self.power_queue = deque()
        self.power_id = secrets.randbelow(2**30)+100000
        self.hb_sequence = 0
        self.mission_services = [self.create_service(Trigger, '/tyrant/host/mission/start', self.start),
                         self.create_service(Trigger, '/tyrant/host/mission/stop', self.stop),
                         self.create_service(Trigger, '/tyrant/host/recording/start', self.start_recording),
                         self.create_service(Trigger, '/tyrant/host/recording/stop', self.stop_recording)]
        self.create_timer(0.1, self.tick)
        self.get_logger().info('Ready; no motion until /tyrant/host/mission/start. '+
                               f'Payload namespace: {self.payload_ns}')

    def open_recording(self, kind):
        if self.recorder:
            raise ValueError('A recording session is already open')
        self.recorder = SessionRecorder(self.get_parameter('output_dir').value,
            dict(kind=kind, plan=self.engine.plan, payload_namespace=self.payload_ns,
                 payload_simulated=self.payload_ns.endswith('_sim'),
                 teensy_simulated=self.get_parameter('teensy_simulated').value,
                 time_association='Host receive-time approximation with channel age; independent device uptimes retained'),
            self.topics, serialize_message, rosbag2_py)
        self.get_logger().info(f'Recording: {self.recorder.path}')

    def start(self, request, response):
        try:
            if self.engine.active or self.recorder:
                raise ValueError('Stop the current mission/recording before starting')
            # Validate readiness before creating files or sending actuator commands.
            now = time.monotonic()
            self.engine.start(now)
            try:
                self.open_recording('mission')
            except Exception:
                self.engine.stop(now)
                self.flush(now)
                raise
            self.flush(now)
            response.success = True
            response.message = str(self.recorder.path)
        except (ValueError, RuntimeError, OSError) as error:
            response.success = False
            response.message = str(error)
        return response

    def stop(self, request, response):
        self.engine.stop(time.monotonic())
        self.flush(time.monotonic())
        response.success = True
        response.message = 'Stop/SAFE requested; board confirmation appears in telemetry'
        return response

    def start_recording(self, request, response):
        try:
            if self.engine.active:
                raise ValueError('Mission recording already controlled by active mission')
            self.open_recording('manual')
            self.record_only = True
            response.success, response.message = True, str(self.recorder.path)
        except (ValueError, RuntimeError, OSError) as error:
            response.success, response.message = False, str(error)
        return response

    def stop_recording(self, request, response):
        if self.engine.active:
            response.success, response.message = False, 'Stop mission first to preserve its recording'
        else:
            self.close_recording('manual_stop')
            response.success, response.message = True, 'Recording closed'
        return response

    def close_recording(self, result):
        if self.recorder:
            self.recorder.close(result)
            self.recorder = None
        self.record_only = False

    def receive(self, topic, message):
        now, ros_ns = time.monotonic(), self.get_clock().now().nanoseconds
        if self.recorder:
            self.recorder.message(topic, message, ros_ns)
        if topic == '/tyrant/simple_state':
            self.engine.update_depth(now, fields(message))
        elif topic == '/tyrant/system/health':
            self.engine.update_health(now, fields(message))
        elif topic == '/tyrant/mode/status':
            data = fields(message)
            data['accepted'] = data['request_accepted']
            self.engine.acknowledge('mode', data, now)
        elif topic == '/tyrant/mission/status':
            data = fields(message)
            self.engine.acknowledge('mission', data, now)
            self.engine.update_status(data, now)
        elif topic == self.payload_ns+'/sensor_power/status':
            data = fields(message)
            pending = self.power_pending
            if pending and message.request_id == pending['message'].request_id and message.sensor_id == pending['message'].sensor_id and message.requested_enable == pending['message'].enable:
                self.power_pending = None
            self.engine.event('sensor_power_ack', now, **data)
        elif topic == self.payload_ns+'/water_quality':
            self.water_quality(message, now, ros_ns)
        self.flush(now)

    def water_quality(self, message, now, ros_ns):
        data = fields(message)
        for name, value_field in VALUE_FIELDS.items():
            data[name+'_value'] = data[value_field]
        before = self.engine.summary().copy()
        step = {} if self.record_only else (self.engine.step or {})
        result = self.engine.observe_payload(data, now)
        if not self.recorder:
            return
        depth = self.engine.depth
        for name, value_field in VALUE_FIELDS.items():
            association = result['associated'][name]
            self.recorder.sample(dict(session_id=self.recorder.metadata['session_id'], host_ros_ns=ros_ns,
                host_monotonic_s=now, mission_id=self.engine.plan['mission_id'] if not self.record_only else '',
                step_id=before['step_id'] if not self.record_only else '', phase=before['phase'] if not self.record_only else 'MANUAL',
                planned_x=step.get('planned_x'), planned_y=step.get('planned_y'),
                target_depth=step.get('target') if step.get('type') in ('dive', 'surface') else None,
                depth_at_receive=depth[1] if depth else None,
                depth_valid_at_receive=bool(self.engine.fresh_depth(now)), payload_boot=result['payload_boot'],
                payload_timestamp_us=message.timestamp_us, sequence=message.sequence,
                sensor=name, value=data[value_field], valid=data[name+'_valid'], sensor_state=data[name+'_state'],
                age_ms=data[name+'_age_ms'], estimated_depth_at_acquisition=association['depth'],
                association_depth_valid=association['depth_valid'], qualified_point_sample=result['qualified'][name] and not self.record_only,
                payload_simulated=self.payload_ns.endswith('_sim'), teensy_simulated=self.get_parameter('teensy_simulated').value))

    def flush(self, now):
        for action in self.engine.take_actions():
            if action['kind'] == 'power':
                if not action['enable']:
                    # Cancel unsent ON commands when a point/mission ends.
                    self.power_queue.clear()
                for sensor_id in self.engine.plan['sensors']:
                    self.power_id = (self.power_id+1) % (2**32) or 1
                    topic = self.payload_ns+'/sensor_power/request'
                    msg = get_message(self.topics[topic])(request_id=self.power_id, sensor_id=sensor_id, enable=action['enable'])
                    self.power_queue.append(msg)
            else:
                topic = '/tyrant/mode/request' if action['kind'] == 'mode' else '/tyrant/mission/command'
                msg = get_message(self.topics[topic])()
                for key,value in action.items():
                    if key != 'kind':
                        if key in ('target', 'effort', 'tolerance'):
                            value = float(value)
                        setattr(msg, key, value)
                self.pubs[topic].publish(msg)
        while self.engine.events:
            event = self.engine.events.pop(0)
            if self.recorder:
                self.recorder.event(event)
            if event['event'] in ('step_result', 'mission_result'):
                self.get_logger().info(json.dumps(clean(event)))
        # Keep final stop/SAFE telemetry for 2 seconds before finalizing the bag.
        if self.recorder and not self.record_only and not self.engine.active:
            if not hasattr(self, 'close_at') or self.close_at is None:
                self.close_at = now+2
            elif now >= self.close_at:
                self.close_recording(self.engine.summary())
                self.close_at = None

    def service_power(self, now):
        topic = self.payload_ns+'/sensor_power/request'
        if self.power_pending and now-self.power_pending['sent_at'] > 1:
            pending = self.power_pending
            if pending['attempts'] < 3:
                self.pubs[topic].publish(pending['message'])
                pending['sent_at'] = now
                pending['attempts'] += 1
            else:
                self.engine.event('sensor_power_ack_timeout', now, request_id=pending['message'].request_id,
                                  sensor_id=pending['message'].sensor_id)
                self.power_pending = None
        if not self.power_pending and self.power_queue:
            msg = self.power_queue.popleft()
            self.pubs[topic].publish(msg)
            self.power_pending = dict(message=msg, sent_at=now, attempts=1)

    def tick(self):
        now = time.monotonic()
        if self.get_parameter('publish_heartbeats').value:
            self.hb_sequence = (self.hb_sequence+1) % (2**32)
            msg = UInt32(data=self.hb_sequence)
            self.pubs['/tyrant/host_heartbeat'].publish(msg)
            self.pubs[self.payload_ns+'/host_heartbeat'].publish(msg)
        self.engine.tick(now)
        self.service_power(now)
        self.flush(now)
        self.pubs['/tyrant/host/mission/status'].publish(String(data=json.dumps(clean(self.engine.summary()), allow_nan=False)))

    def shutdown_session(self):
        self.engine.stop(time.monotonic())
        self.flush(time.monotonic())
        self.close_recording(self.engine.summary())


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MissionHost()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node:
            if rclpy.ok():
                node.shutdown_session()
            else:
                node.close_recording(node.engine.summary())
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

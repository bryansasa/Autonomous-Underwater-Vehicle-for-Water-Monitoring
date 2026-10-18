#!/usr/bin/env python3
"""First GUI gateway stage: receive real ROS telemetry, no publishers."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from state import StateStore


def topic_specs(namespace):
    result = {}
    def add(key, topic, name, package='tyrant_interfaces', stale_ms=2000):
        result[key] = dict(topic=topic, type=f'{package}/msg/{name}', stale_ms=stale_ms)
    for key, suffix, name in (
        ('navigation', 'simple_state', 'SimpleState'),
        ('health', 'system/health', 'SystemHealth'),
        ('mode', 'mode/status', 'ModeStatus'),
        ('mission_board', 'mission/status', 'MissionStatus'),
        ('teensy_diagnostics', 'communication/diagnostics', 'CommunicationDiagnostics'),
        ('thrusters', 'control/thruster_command', 'ThrusterCommand'),
        ('actuation', 'actuation/status', 'ActuatorStatus'),
        ('depth_reference', 'depth/reference/status', 'DepthReferenceStatus'),
    ):
        add(key, '/tyrant/'+suffix, name)
    for key, suffix, name in (
        ('water_quality', 'water_quality', 'PayloadWaterQuality'),
        ('power_sensors', 'power/sensors', 'PayloadPower'),
        ('power_thruster', 'power/thruster', 'PayloadPower'),
        ('sensor_power_ack', 'sensor_power/status', 'SensorPowerStatus'),
        ('payload_health', 'health', 'PayloadHealth'),
        ('esp_diagnostics', 'communication/diagnostics', 'PayloadCommunicationDiagnostics'),
    ):
        # Payload acquisition age/validity remains in the message. ACK is an
        # event: stale here means old reception, not reversal of accepted state.
        add(key, namespace+'/'+suffix, name, 'tyrant_payload_interfaces', 8000)
    add('mission_host', '/tyrant/host/mission/status', 'String', 'std_msgs')
    return result


def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if urlsplit(self.path).path != '/api/state':
                self.send_error(404)
                return
            body = json.dumps(store.snapshot(), allow_nan=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.send_error(405, 'Commands are not available in this gateway stage')

        def log_message(self, *_args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--payload-namespace', choices=['/tyrant/payload', '/tyrant/payload_sim'], default='/tyrant/payload')
    args = parser.parse_args()
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    rclpy.init(args=[])
    node = Node('tyrant_gui_gateway')
    specs = topic_specs(args.payload_namespace)
    store = StateStore(specs, args.payload_namespace)
    subscriptions = []
    try:
        for key, spec in specs.items():
            subscriptions.append(node.create_subscription(
                get_message(spec['type']), spec['topic'],
                lambda msg, key=key: store.update(key, message_to_ordereddict(msg)),
                qos_profile_sensor_data))
        server = ThreadingHTTPServer((args.bind, args.port), handler_for(store))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        node.get_logger().info(f'Telemetry API http://{args.bind}:{args.port}/api/state; no commands or heartbeat publishers')
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

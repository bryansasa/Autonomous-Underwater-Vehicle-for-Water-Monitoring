"""ROS-independent snapshot store. Reception age never uses board uptime."""
import math
import threading
import time
from datetime import datetime, timezone


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    return value


class StateStore:
    def __init__(self, topics, payload_namespace, clock=time.monotonic):
        self.topics = topics
        self.namespace = payload_namespace
        self.clock = clock
        self.lock = threading.Lock()
        self.latest = {}

    def update(self, key, data):
        # Clean once before publishing the immutable snapshot to HTTP readers.
        data = clean(data)
        with self.lock:
            self.latest[key] = (self.clock(), data)

    def snapshot(self):
        with self.lock:
            now = self.clock()
            streams = {}
            for key, spec in self.topics.items():
                entry = self.latest.get(key)
                age = max(0, int((now-entry[0])*1000)) if entry else None
                streams[key] = {
                    'topic': spec['topic'], 'type': spec['type'],
                    'received': entry is not None, 'reception_age_ms': age,
                    'stale': entry is None or age > spec['stale_ms'],
                    'stale_after_ms': spec['stale_ms'],
                    'data': entry[1] if entry else None,
                }
        return {
            'schema_version': 1,
            'server_time_utc': datetime.now(timezone.utc).isoformat(),
            'source': 'ROS', 'payload_namespace': self.namespace,
            'payload_profile': 'SIM' if self.namespace.endswith('_sim') else 'PAYLOAD',
            'capabilities': {'telemetry': True, 'commands': False,
                             'manual_input': False, 'camera': False},
            'streams': streams,
        }

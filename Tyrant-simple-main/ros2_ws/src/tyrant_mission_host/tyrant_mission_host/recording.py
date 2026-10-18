"""Durable CSV/event records and a matching rosbag with explicit session provenance."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import uuid


def clean(value):
    import math
    if isinstance(value, dict):
        return {k: clean(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


class SessionRecorder:
    def __init__(self, root, metadata, topics, serialize, bag_module):
        root = Path(root).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(root).free < 512*1024**2:
            raise RuntimeError('Recording requires at least 512 MiB free storage')
        name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_')+uuid.uuid4().hex[:8]
        self.path = root/name
        self.path.mkdir()
        self.files = []
        self.serialize = serialize
        self.writer = None
        self.metadata = clean(dict(session_id=name, started_utc=datetime.now(timezone.utc).isoformat(), **metadata))
        self.metadata_path = self.path/'session.json'
        try:
            self.metadata_path.write_text(json.dumps(self.metadata, indent=2)+'\n')
            self.csv_file = self.open('samples.csv')
            self.columns = ['session_id', 'host_ros_ns', 'host_monotonic_s', 'mission_id', 'step_id',
                            'phase', 'planned_x', 'planned_y', 'target_depth', 'depth_at_receive',
                            'depth_valid_at_receive', 'payload_boot', 'payload_timestamp_us', 'sequence',
                            'sensor', 'value', 'valid', 'sensor_state', 'age_ms',
                            'estimated_depth_at_acquisition', 'association_depth_valid',
                            'qualified_point_sample', 'payload_simulated', 'teensy_simulated']
            self.csv = csv.DictWriter(self.csv_file, fieldnames=self.columns)
            self.csv.writeheader()
            self.event_file = self.open('events.jsonl')
            self.writer = bag_module.SequentialWriter()
            self.writer.open(bag_module.StorageOptions(uri=str(self.path/'bag'), storage_id='sqlite3'),
                             bag_module.ConverterOptions('', ''))
            for topic, type_name in topics.items():
                self.writer.create_topic(bag_module.TopicMetadata(name=topic, type=type_name, serialization_format='cdr'))
        except Exception:
            self.close('initialization_failed')
            raise

    def open(self, name):
        handle = (self.path/name).open('w', newline='')
        self.files.append(handle)
        return handle

    def message(self, topic, message, ros_ns):
        if self.writer:
            self.writer.write(topic, self.serialize(message), ros_ns)

    def event(self, data):
        self.event_file.write(json.dumps(clean(data), allow_nan=False)+'\n')
        self.event_file.flush()

    def sample(self, row):
        self.csv.writerow(clean(row))
        self.csv_file.flush()

    def close(self, result):
        # Humble writer finalizes metadata on destruction (no public close method).
        self.writer = None
        for handle in self.files:
            if not handle.closed:
                handle.close()
        if self.metadata_path.exists():
            self.metadata.update(ended_utc=datetime.now(timezone.utc).isoformat(), result=clean(result))
            self.metadata_path.write_text(json.dumps(self.metadata, indent=2)+'\n')

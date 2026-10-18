import json
import unittest
from state import StateStore
from server import topic_specs


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.specs = topic_specs('/tyrant/payload_sim')
        self.store = StateStore(self.specs, '/tyrant/payload_sim', lambda: self.now)

    def test_missing_data_is_explicit_not_zero_or_healthy(self):
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['payload_profile'], 'SIM')
        self.assertFalse(snapshot['capabilities']['commands'])
        for stream in snapshot['streams'].values():
            self.assertFalse(stream['received'])
            self.assertTrue(stream['stale'])
            self.assertIsNone(stream['data'])
            self.assertIsNone(stream['reception_age_ms'])

    def test_invalid_values_and_board_uptime_are_preserved_correctly(self):
        self.store.update('water_quality', {'ph': float('nan'),
            'conductivity_us_cm': float('inf'), 'ph_valid': False,
            'timestamp_us': 4294000000, 'ph_age_ms': 4294967295})
        data = json.loads(json.dumps(self.store.snapshot(), allow_nan=False))
        channel = data['streams']['water_quality']
        self.assertIsNone(channel['data']['ph'])
        self.assertIsNone(channel['data']['conductivity_us_cm'])
        self.assertEqual(channel['data']['timestamp_us'], 4294000000)
        self.assertEqual(channel['data']['ph_age_ms'], 4294967295)
        self.assertEqual(channel['reception_age_ms'], 0)

    def test_freshness_per_stream_and_old_ack_are_not_reversed(self):
        self.store.update('navigation', {'depth': 3.2, 'depth_valid': True})
        self.store.update('sensor_power_ack', {'request_id': 1, 'accepted': True})
        self.now += 9
        streams = self.store.snapshot()['streams']
        self.assertTrue(streams['navigation']['stale'])
        self.assertEqual(streams['navigation']['data']['depth'], 3.2)
        self.assertTrue(streams['sensor_power_ack']['stale'])
        self.assertTrue(streams['sensor_power_ack']['data']['accepted'])
        self.store.update('navigation', {'depth': 1.1, 'depth_valid': False})
        self.assertFalse(self.store.snapshot()['streams']['navigation']['stale'])
        self.assertFalse(self.store.snapshot()['streams']['navigation']['data']['depth_valid'])

    def test_namespaces_do_not_mix_and_type_matches_esp(self):
        for namespace in ('/tyrant/payload', '/tyrant/payload_sim'):
            specs = topic_specs(namespace)
            self.assertEqual(specs['water_quality']['topic'], namespace+'/water_quality')
            self.assertEqual(specs['esp_diagnostics']['type'],
                             'tyrant_payload_interfaces/msg/PayloadCommunicationDiagnostics')


if __name__ == '__main__':
    unittest.main()

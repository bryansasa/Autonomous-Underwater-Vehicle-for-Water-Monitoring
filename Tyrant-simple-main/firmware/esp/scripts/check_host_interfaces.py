#!/usr/bin/env python3
"""Diagnose active payload Python package and C type support, without a ROS node."""
from rosidl_runtime_py.utilities import get_message
import tyrant_payload_interfaces
print('Active Python package:', tyrant_payload_interfaces.__file__)
for name in ('PayloadWaterQuality', 'PayloadPower', 'PayloadHealth',
             'PayloadCommunicationDiagnostics', 'SensorPowerRequest', 'SensorPowerStatus'):
    cls = get_message('tyrant_payload_interfaces/msg/' + name)
    cls.__class__.__import_type_support__()
    if cls.__class__._TYPE_SUPPORT is None:
        raise RuntimeError(name + ': C type support unavailable')
    print(name + ': Python and C type support OK')

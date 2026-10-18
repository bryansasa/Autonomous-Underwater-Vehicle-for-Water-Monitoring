# tyrant_teleop

Configurable ROS 2 joystick/PS-controller bridge for Tyrant AUV.

## Safety behavior

- `ManualCommand` is published only while the deadman button is held.
- Deadman release publishes one neutral command and then stops publication, allowing the Teensy 250 ms manual-command timeout to force zero wrench.
- `/joy` timeout stops manual publication.
- If configured, a longer `/joy` timeout requests `SAFE`.
- The development node can publish `/tyrant/host_heartbeat`; if the node dies, the Teensy heartbeat timeout still forces `SAFE`.

## Calibration

Run `joy_node`, then:

```bash
ros2 run tyrant_teleop tyrant_joy_probe
```

Move one stick/trigger/button at a time. Update `config/ps_controller.yaml` with the observed indices and signs.

The default button mapping matches the PRD and the node defaults:

| Button | Index | Action |
|---|---:|---|
| L1 | 4 | Hold deadman to stream manual commands |
| CROSS | 0 | Request MANUAL |
| SQUARE | 2 | Request IDLE |
| CIRCLE | 1 | Request SAFE |
| TRIANGLE | 3 | Request depth surface reference |

Keep these actions on distinct buttons when calibrating. Mode and surface-reference
requests are sent once on the press edge. Request IDLE before setting the surface
reference, then inspect the corresponding status topics for acceptance.

## Development run

```bash
ros2 launch tyrant_teleop ps_teleop.launch.py
```

The launch file loads `config/ps_controller.yaml`, overriding the node defaults.
Verify its button and axis indices on the actual controller/OS driver before use.

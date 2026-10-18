# PS / Joystick Teleoperation

`tyrant_teleop` converts `sensor_msgs/Joy` into Tyrant vehicle-level manual commands. It does not know or command individual thrusters.

```text
PS / USB controller
      ↓
joy_node
      ↓
/joy
      ↓
tyrant_teleop
      ↓
/tyrant/manual/command
      ↓
Teensy stabilized MANUAL controller
      ↓
/tyrant/control/wrench_request
      ↓
allocator / mock backend
```

## Safety contract

- A deadman button must be held before `ManualCommand` is streamed.
- Releasing deadman publishes one neutral command and then stops the stream. Teensy manual-command freshness therefore expires and forces zero wrench.
- If `/joy` stops updating, manual-command publication stops after the configured `joy_timeout_s`.
- By default a longer joystick timeout requests `SAFE`.
- The development teleop node can publish `/tyrant/host_heartbeat` at 10 Hz. If another Jetson supervisor owns heartbeat later, set `publish_heartbeat: false` in the YAML.
- `SAFE` remains zero-propulsion; teleop does not implement emergency surfacing.

## Calibrate the actual controller first

Controller indices can differ between PS4/PS5, Bluetooth/USB, Linux drivers, and machines. Do not assume the example YAML is correct.

```bash
ros2 run joy joy_node
ros2 run tyrant_teleop tyrant_joy_probe
```

Move one control at a time and record the reported `axis[N]` / `button[N]` indices. Then edit:

```text
ros2_ws/src/tyrant_teleop/config/ps_controller.yaml
```

The default axes map:

```text
left stick Y  -> surge
left stick X  -> sway
right stick X -> yaw-rate command
R2 - L2       -> heave/depth-rate command
roll/pitch    -> auto-level (no stick axis by default)
```

The button mapping follows the PRD and the node defaults:

| Button | Index | Action |
|---|---:|---|
| L1 | 4 | Hold deadman to stream manual commands |
| CROSS | 0 | Request MANUAL |
| SQUARE | 2 | Request IDLE |
| CIRCLE | 1 | Request SAFE |
| TRIANGLE | 3 | Request depth surface reference |

`ps_teleop.launch.py` loads this YAML, so changes here override the node defaults.
Verify all indices on the actual controller and keep each action on a distinct
button. Mode and surface-reference requests occur once on a button press; holding
the button does not repeat the request. Request IDLE before setting the surface
reference, and check `/tyrant/mode/status` and `/tyrant/depth/reference/status`
for acceptance.

## Run against mock thrusters

Use the software-only Teensy profile:

```bash
pio run -e teensy41-mock-thrusters -t upload
```

Then on the laptop/Jetson:

```bash
ros2 launch tyrant_teleop ps_teleop.launch.py
```

Inspect the chain:

```bash
ros2 topic echo /joy
ros2 topic echo /tyrant/manual/command
ros2 topic echo /tyrant/control/wrench_request
ros2 topic echo /tyrant/control/thruster_command
```

No ESC/PWM output exists in the mock profile.

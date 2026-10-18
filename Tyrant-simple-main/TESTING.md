# Tyrant Simple Test Guide

The `tyrant-simple` test suite intentionally keeps the proven non-EKF regression coverage from `tyrant-auv` and replaces full-EKF tests with reduced-state tests.

## Test environments

### Core regression suite

```bash
cd ~/tyrant-simple/firmware/teensy
pio test -e teensy41-test
```

This runs every test suite except `test_connection_manager`.

### ConnectionManager suite

```bash
pio test -e teensy41-test-connection
```

This environment links `connection_manager.cpp` against tiny `TyrantROS` stubs supplied by the test. It preserves and tests the four connection states without pulling the full micro-ROS implementation into the unit test.

## Current suite

| Suite | Cases | Origin / purpose |
|---|---:|---|
| `test_depth_estimator` | 14 | Reused from `tyrant-auv`; pressure-to-depth model, metadata, invalid/NaN/Inf handling |
| `test_imu_mounting` | 5 | Verified production `[+X,-Y,-Z]` mapping regression |
| `test_imu_source` | 12 | Reused/adapted IMU source and stats behavior |
| `test_pressure_source` | 8 | Reused/adapted pressure source and stats behavior |
| `test_simple_state_estimator` | 8 | Reduced estimator stability, yaw bias, timing, freshness, depth |
| `test_vehicle_mode` | 7 | Vehicle-mode transition contract |
| `test_safety_manager` | 8 | Heartbeat, MANUAL/AUTO readiness gates, emergency authority, timeout/disconnect |
| `test_scheduler` | 2 | Task cadence/reset |
| `test_depth_reference_manager` | 4 | Surface-reference policy |
| `test_connection_manager` | 4 | Four-state ROS connection/reconnect contract |
| `test_manual_control` | 20 | Command freshness + stabilized depth/attitude/heading controller |
| `test_thruster_allocation` | 14 | TAM build, DLS allocator, saturation, residual, synthetic full-rank mock geometry |
| `test_mock_thruster_backend` | 5 | Valid storage and fail-closed neutral behavior |
| `test_thruster_output_mapper` | 7 | Normalized command to PWM pulse mapping, deadband, inversion, invalid configuration |
| `test_thruster_backend` | 6 | Disabled/mock/PWM boundary, watchdog neutralization, invalid-command fault latch |
| `test_sysid_recorder` | 8 | Session lifecycle, 20 Hz cadence, synchronized I/O including backend thruster command |
| `test_mission_manager` | 10 | Fixed mission queue, timed effort, depth/heading targets, wrap, state-failure behavior |
| `test_emergency_recovery_manager` | 6 | Zero-thrust policy, controlled surface, completion, timeout, fail-closed state loss |
| `test_sim_state_source` | 7 | HIL state validity, timeout, wrap-safe freshness, non-finite/fault rejection |
| **Total** | **155** | |

## Run one suite

Examples:

```bash
pio test -e teensy41-test -f test_simple_state_estimator
pio test -e teensy41-test -f test_imu_source
pio test -e teensy41-test -f test_safety_manager
pio test -e teensy41-test -f test_manual_control
pio test -e teensy41-test -f test_thruster_allocation
pio test -e teensy41-test -f test_mock_thruster_backend
pio test -e teensy41-test -f test_sysid_recorder
pio test -e teensy41-test-connection -f test_connection_manager
```

## What was intentionally not migrated

The following test families remain only in the old `tyrant-auv` R&D repository because their production code does not exist in `tyrant-simple`:

```text
test_covariance15
test_covariance_propagation
test_error_state_injection
test_ekf_prediction
test_estimator_runtime
test_estimator_health
test_estimator_initialization
test_prediction_timing
test_depth_update
test_yaw_update
test_magnetometer_aiding
test_magnetometer_fusion_flow
```

Do not copy those tests into this repository just to increase coverage: they specify a different architecture.

## Hardware integration tests

Unit tests do not replace physical validation. Keep these separate:

```bash
# Raw HWT905 frame / mounting smoke test
pio run -e teensy41-hwt905-smoke -t upload

# Raw FullDepth/MS5837 I2C smoke test
pio run -e teensy41-fulldepth-smoke -t upload

# Production firmware
pio run -e teensy41 -t upload
```

After production upload, validate at minimum:

```bash
ros2 topic echo /tyrant/sensors/imu
ros2 topic echo /tyrant/sensors/pressure
ros2 topic echo /tyrant/simple_state
ros2 topic echo /tyrant/system/health
```

For the first estimator regression, leave the IMU stationary for 5-10 minutes and confirm attitude and angular rate remain bounded.


## FullDepth production integration check

1. Confirm `/tyrant/sensors/pressure` reports finite positive pressure and temperature.
2. Keep the vehicle `IDLE` and sensor at the intended zero-depth surface.
3. Publish `DepthReferenceRequest` with `command: 1` (`SET_SURFACE`).
4. Confirm `/tyrant/depth/reference/status` returns `accepted: true` and `reference_valid: true`.
5. Lower the sensor into water and confirm `/tyrant/simple_state` depth increases positive-down.
6. Return to the original surface and confirm depth returns close to zero.

The current BlueRobotics MS5837 library performs a blocking conversion, so production sampling is throttled to 5 Hz during this validation stage. Before high-rate closed-loop control is enabled, re-check loop jitter with IMU, micro-ROS, and pressure acquisition active together.


## Stabilized MANUAL ROS integration test

The unit tests validate both the command manager and the temporary pre-LMPC stabilized controller. Production validation should additionally check ROS, state-validity, and mode gates:

1. Confirm `/tyrant/simple_state` has `attitude_valid: true`; set a surface reference if depth hold is being tested.
2. Stream `/tyrant/host_heartbeat` at 10 Hz.
3. Request MANUAL.
4. Stream a neutral `/tyrant/manual/command` at 20 Hz. Current depth/yaw should latch as hold references.
5. Confirm `/tyrant/control/wrench_request` is enabled. `K/M` may correct non-level roll/pitch; `Z/N` should be near zero at the freshly latched depth/heading.
6. Command positive surge and confirm `X > 0`; positive sway should make `Y > 0`.
7. Command positive heave and confirm `Z > 0` initially because positive depth is down.
8. Command positive yaw and confirm `N > 0` initially; release yaw and confirm the latest heading is held.
9. Stop the manual command stream and confirm output is zero/disabled within about 250 ms.
10. Restart the command and confirm current depth/yaw re-latch instead of returning to the old references.
11. Stop heartbeat and confirm mode falls to SAFE and wrench is disabled.

No physical actuator is connected at this stage. The mock backend can be exercised with the `teensy41-mock-thrusters` profile. The P/PD gains remain provisional normalized-wrench development gains, not wet-tuned vehicle gains.


## SysID software integration test

After rebuilding `tyrant_interfaces`, start a session:

```bash
ros2 topic pub --once \
  /tyrant/sysid/control \
  tyrant_interfaces/msg/SysIdControl \
  "{request_id: 1, command: 1, experiment_id: 101, profile_id: 6}"
```

Then inspect:

```bash
ros2 topic echo /tyrant/sysid/status
ros2 topic echo /tyrant/sysid/sample
```

With the normal `teensy41` profile, `thruster_command_valid` remains `false` because production geometry is intentionally unavailable. With `teensy41-mock-thrusters`, it becomes `true` and contains the eight virtual commands accepted by the mock backend. These mock data are for software validation only, not vehicle identification.


## Mock allocator ROS integration test

Build/upload the explicit software-only profile:

```bash
pio run -e teensy41-mock-thrusters -t upload
```

Run heartbeat + MANUAL command as in the stabilized-control test, then inspect:

```bash
ros2 topic echo /tyrant/control/thruster_command
```

Expected:

- `allocator_ready: true`;
- `mock_backend: true`;
- finite eight-channel command;
- `valid: true` while the request is allocatable;
- `enabled: false` and all-zero command after manual-command timeout or SAFE;
- no PWM output exists in this build.

Repeat with production `teensy41`; `allocator_ready` must be `false` and all eight commands must remain zero until real geometry is configured.

## ROS 2 teleop mapping tests

The `tyrant_teleop` package adds eight host-side Python mapping tests. They are separate from the 155 Teensy/Unity test cases.

```bash
cd ~/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tyrant_interfaces tyrant_teleop --symlink-install
source install/setup.bash
colcon test --packages-select tyrant_teleop
colcon test-result --verbose
```

The pure mapper regression covers deadzone behavior, stick inversion, common `+1 released / -1 pressed` trigger normalization, R2/L2 heave sign, trigger cancellation, and safe-zero handling for missing axis indices.

Hardware/controller mapping still must be calibrated with:

```bash
ros2 run joy joy_node
ros2 run tyrant_teleop tyrant_joy_probe
```

Then run the complete chain with `teensy41-mock-thrusters` and verify `/joy -> /tyrant/manual/command -> /tyrant/control/wrench_request -> /tyrant/control/thruster_command`.


## Mission / emergency software integration test

Use `teensy41-mock-thrusters` or `teensy41-hil` for AUTO software validation. Production `teensy41` remains AUTO-blocked while verified thruster geometry and a ready actuator backend are unavailable. A loaded mission, valid attitude/heading/depth, and healthy host communication are also required.

1. Keep host heartbeat healthy and confirm reduced attitude/heading/depth are valid.
2. CLEAR then APPEND mission steps on `/tyrant/mission/command`.
3. Confirm `/tyrant/system/health` reports `autonomy_ready: true`.
4. Request AUTO and then send mission START.
5. Observe `/tyrant/mission/status`, `/tyrant/control/wrench_request`, and `/tyrant/control/thruster_command`.
6. On mission completion, confirm mode falls to SAFE and thruster command becomes neutral.
7. Trigger `EmergencyControl` ZERO_THRUST and confirm EMERGENCY latches with neutral output.
8. After reboot, with valid depth/attitude, trigger CONTROLLED_SURFACE and confirm an upward virtual heave command is produced.
9. Invalidate depth/attitude (or use unit tests) and confirm recovery fails closed to neutral.

See `docs/mission_emergency.md` for concrete ROS commands.

## Actuation/PWM regression

New tests cover normalized-command-to-PWM mapping and the backend watchdog/fault latch:

```bash
pio test -e teensy41-test -f test_thruster_output_mapper
pio test -e teensy41-test -f test_thruster_backend
```

The full Teensy regression suite now contains **155 test cases**.

Compile-check the future physical backend without valid output pins:

```bash
pio run -e teensy41-pwm-skeleton
```

Expected runtime behavior in the default production build is backend type `DISABLED`, `ready=false`, and neutral/invalid thruster output. In the mock build, backend type is `MOCK`, `ready=true`, and `physical_output_enabled=false`.


## HIL / SysID simulation regression

The HIL state source adds seven Unity cases:

```bash
pio test -e teensy41-test -f test_sim_state_source
```

The host-side `tyrant_sim` package has pure Python tests for the synthetic TAM reconstruction, reduced plant signs/restoring behavior, step profiles, deterministic PRBS, chirp bounds, and profile-ID contract:

```bash
cd ~/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tyrant_interfaces tyrant_sim --symlink-install
source install/setup.bash
colcon test --packages-select tyrant_sim
colcon test-result --verbose
```

For closed-loop HIL:

```bash
pio run -e teensy41-hil -t upload
ros2 launch tyrant_sim hil_plant.launch.py
```

Then run an excitation and verify the path:

```text
ManualCommand -> WrenchRequest -> ThrusterCommand -> plant -> sim state -> Teensy controller
```

If the plant node is killed, `/tyrant/sim/state_input` becomes stale within 200 ms and the HIL state source invalidates attitude/heading/depth. This fail-closed behavior is part of the regression contract.

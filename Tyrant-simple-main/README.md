# Tyrant Simple

Panduan terpadu setup hardware, tes thruster/manual, tuning P/PD, SysID dan tahapan LMPC: [Panduan setup dan kontrol](docs/PANDUAN_SETUP_KONTROL_SYSID_LMPC.md) (13 Oktober 2026). Panduan membedakan fitur tersedia dari pekerjaan hardware/controller yang belum selesai.

Payload ESP firmware is now in `firmware/esp`. ESP and Teensy message packages
remain separate in `ros2_ws/src`. Host sampling coordination and combined rosbag/CSV
recording are described in [the laptop HIL guide](docs/payload_mission_host.md).

Clean reduced-state Tyrant AUV development baseline.

This repository intentionally contains **no full 15-state ESKF**. The previous `tyrant-auv` repository should be kept separately as R&D/reference history.

## What is included

- Teensy 4.1 firmware with sensor, control, safety, mission/emergency, and SysID modules.
- HWT905 driver + verified BODY-FRD mounting path.
- Sensor manager and production FullDepth/MS5837 pressure path.
- Reduced state estimator:
  - roll/pitch: gyro + accelerometer complementary filter;
  - yaw: 2-state Kalman filter `[yaw, yaw_rate_bias]` + tilt-compensated magnetometer heading;
  - depth: latest pressure-derived depth.
- Existing safety/mode state machine.
- Existing 4-state micro-ROS connection manager.
- Clean ROS 2 interface package.
- AUTO requires a loaded mission, valid reduced state, healthy communication, and ready allocator/backend. Production remains blocked; mock/HIL profiles can exercise missions when these conditions are met.
- Stabilized MANUAL path: surge/sway effort + depth/attitude/heading hold -> normalized body-FRD wrench request.
- Tested TAM builder + damped least-squares allocator + explicit 8-channel mock thruster backend.
- Production thruster geometry and PWM/ESC output remain intentionally disabled until chassis geometry and actuator characterization are available.

## Explicitly not included

- `Covariance15`
- `ErrorState15`
- nominal 6-DOF inertial propagation
- full ESKF prediction/update/injection
- X/Y inertial position
- translational velocity from IMU double integration
- `/tyrant/state`
- `/tyrant/estimator/health`

The reduced state is published on:

```text
/tyrant/simple_state
```

## Repository layout

```text
tyrant-simple/
├── firmware/teensy/
│   ├── include/
│   ├── src/
│   ├── test/
│   ├── lib/witmotion_sdk/
│   ├── extra_packages/tyrant_interfaces/
│   └── platformio.ini
├── ros2_ws/src/tyrant_interfaces/
├── firmware/esp/
├── ros2_ws/src/tyrant_payload_interfaces/
├── ros2_ws/src/tyrant_mission_host/
├── ros2_ws/src/tyrant_teleop/
├── ros2_ws/src/tyrant_sim/
├── companion/jetson/
└── docs/
```

## 1. Put the project on the laptop

Recommended:

```bash
cd ~
unzip tyrant-simple.zip
cd ~/tyrant-simple
```

Keep the old repo:

```text
~/tyrant-auv      # full EKF archive/reference
~/tyrant-simple   # new development baseline
```

## 2. Build ROS 2 interfaces

```bash
cd ~/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tyrant_interfaces tyrant_teleop tyrant_sim --symlink-install
source install/setup.bash
```

Check:

```bash
ros2 interface show tyrant_interfaces/msg/SimpleState
```

## 3. Run firmware regression tests

The clean baseline now contains 155 Teensy/Unity test cases. Proven non-EKF tests from `tyrant-auv` are reused for sensors/depth/mounting, while new tests cover the reduced estimator, safety policy, vehicle mode, scheduler, depth reference, manual command gating, and the 4-state ConnectionManager.

```bash
cd ~/tyrant-simple/firmware/teensy

# Core suite
pio test -e teensy41-test

# 4-state ConnectionManager with ROS stubs
pio test -e teensy41-test-connection
```

Run one suite while debugging, for example:

```bash
pio test -e teensy41-test -f test_simple_state_estimator
pio test -e teensy41-test -f test_imu_source
pio test -e teensy41-test-connection -f test_connection_manager
```

See [`TESTING.md`](TESTING.md) for the complete test matrix and what was intentionally not migrated from the full-EKF repository.

## 4. Build / upload Teensy

```bash
pio run -e teensy41 -t clean
pio run -e teensy41
pio run -e teensy41 -t upload
```

Current production hardware bindings are:

- HWT905: `Serial1`, 9600 baud, sensor-to-body mapping `[+X, -Y, -Z]`;
- FullDepth/MS5837: default `Wire` I2C bus, 100 kHz, 5 Hz sampling.

On Teensy 4.1 the default `Wire` bus uses SDA pin 18 and SCL pin 19. The FullDepth adapter publishes absolute pressure and temperature; `DepthEstimator` owns surface-zero and pressure-to-depth conversion.


## 5. Validate FullDepth production path

Physical depth-sensor installation and qualification remain deferred in the PRD V0.3 baseline. Use HIL for depth-dependent software validation until the sensor is available. The procedure below applies when the real sensor is installed; it is not a record of a completed hardware test.

Before production firmware, the standalone FullDepth smoke environment remains available:

```bash
pio run -e teensy41-fulldepth-smoke -t upload
pio device monitor -b 115200
```

With production firmware running, inspect raw pressure first:

```bash
ros2 topic echo /tyrant/sensors/pressure
```

While the vehicle is IDLE and the pressure sensor is at the desired zero-depth surface, set the surface reference:

```bash
ros2 topic pub --once \
  /tyrant/depth/reference/request \
  tyrant_interfaces/msg/DepthReferenceRequest \
  "{request_id: 1, command: 1}"
```

Confirm acceptance:

```bash
ros2 topic echo /tyrant/depth/reference/status
```

Then inspect:

```bash
ros2 topic echo /tyrant/simple_state
```

`depth` is positive down. The development default water density is `1025 kg/m^3` (seawater). For a freshwater bucket/tank characterization, temporarily change `DEPTH_WATER_DENSITY_KG_M3` in `sensor_config.h` to about `997.0f`.

## 6. Run micro-ROS agent and inspect state

Use your normal serial micro-ROS agent command, then:

```bash
source /opt/ros/humble/setup.bash
source ~/tyrant-simple/ros2_ws/install/setup.bash

ros2 topic echo /tyrant/sensors/imu
ros2 topic echo /tyrant/simple_state
ros2 topic echo /tyrant/system/health
```

For the first hardware validation, leave the sensor stationary for 5-10 minutes. Expect approximately the physical roll/pitch/yaw, body angular velocity close to zero, and no runaway position/velocity fields because those fields do not exist in this architecture.

## 7. Stabilized MANUAL control validation

The temporary pre-LMPC controller feeds the TAM/allocator and selected actuator backend. Physical output remains disabled in the default build:

```text
/tyrant/manual/command
        ↓
ManualCommandManager
  clamp + finite check
  250 ms freshness gate
        ↓
StabilizedManualController
        ↓
normalized BODY-FRD wrench request
        ↓
/tyrant/control/wrench_request
        ↓
TAM / damped least-squares allocator
        ↓
Thruster backend (DISABLED / MOCK / PWM skeleton)
```

The input axes remain dimensionless in `[-1,+1]`, but their MANUAL semantics are now:

- `surge`: direct normalized `X` effort;
- `sway`: direct normalized `Y` effort;
- `heave`: depth-reference rate command; positive means command deeper depth;
- `roll`: bounded roll-angle reference, currently up to ±15°;
- `pitch`: bounded pitch-angle reference, currently up to ±15°;
- `yaw`: heading-reference rate command, currently up to ±45°/s.

When `heave` returns to zero, the latest depth reference is held. When `yaw` returns to zero, the latest heading reference is held. `roll=0` and `pitch=0` request level attitude, so `K/M` may be nonzero while the vehicle is tilted. This is intentional.

The current controller is deliberately simple:

```text
surge/sway -> direct normalized effort

depth      -> P
roll       -> PD
pitch      -> PD
yaw         -> PD
```

There is no integral term yet. Gains in `control_config.h` are provisional normalized-wrench development values and are **not wet-tuned vehicle gains**.

Safety behavior:

- MANUAL + healthy heartbeat are required;
- manual command must be refreshed within 250 ms;
- stale command, blocked propulsion, invalid attitude, or excessive control-loop gap zeroes the request and resets held references;
- invalid depth disables only `Z` depth control;
- invalid heading disables only `N` heading control;
- after a reset/resume, depth and heading references re-latch the current state for a bumpless restart.

No physical force units are claimed yet. A normalized damped least-squares allocator and a unified actuator boundary now exist. PWM mapping/backend code is present, but physical output remains disabled by default until production geometry, pin mapping, force calibration, and ESC characterization are verified.

Example validation sequence:

```bash
# Terminal 1: keep host heartbeat alive
ros2 topic pub -r 10 \
  /tyrant/host_heartbeat \
  std_msgs/msg/UInt32 \
  "{data: 1}"

# Terminal 2: request MANUAL
ros2 topic pub --once \
  /tyrant/mode/request \
  tyrant_interfaces/msg/ModeRequest \
  "{request_id: 10, requested_mode: 2}"

# Terminal 3: stream a neutral stabilized command
ros2 topic pub -r 20 \
  /tyrant/manual/command \
  tyrant_interfaces/msg/ManualCommand \
  "{sequence: 1, surge: 0.0, sway: 0.0, heave: 0.0, roll: 0.0, pitch: 0.0, yaw: 0.0}"

# Terminal 4: inspect the gated controller output
ros2 topic echo /tyrant/control/wrench_request
```

With valid depth/heading, the first neutral command latches the current depth and yaw. `Z` and `N` should then stay near zero while those states remain at the latched references. `K/M` may be nonzero if the measured roll/pitch are not level.

Then test each axis individually. For example, positive surge should make `X > 0`, positive heave should slowly move the held depth reference deeper and make `Z > 0` while the measured depth has not yet followed, and positive yaw should slew the heading reference clockwise and make `N > 0` initially.

Stop only the manual-command publisher. Within about 250 ms the request must become zero with `enabled: false`. Restarting the stream should re-latch current depth/yaw rather than jump back to an old reference.

## 8. Control roadmap

The simple closed-loop controller above is the **temporary validation controller before LMPC**. The current software path and hardware roadmap are:

```text
stabilized MANUAL controller
        ↓
normalized vehicle wrench [X Y Z K M N]
        ↓
TAM + damped least-squares allocator
        ↓
8-channel mock thruster command   ← current software boundary
        ↓
future characterized allocator / QP
        ↓
characterized ESC mapping / physical PWM
```

PWM mapping/backend code already exists as a disabled skeleton. Physical deployment still requires verified geometry, pins, and ESC/thruster characterization. LMPC follows real-vehicle SysID, independent model validation, and controller SIL validation; it will retain the vehicle-wrench/allocator boundary.

Before DVL or another valid translational velocity source exists:

- surge/sway remain bounded manual effort/wrench commands;
- depth is pressure/depth closed-loop;
- yaw is heading closed-loop;
- roll/pitch are attitude stabilization.

AUTO mission sequencing is implemented for the reduced-state contract. Production remains blocked because geometry and the actuator backend are not ready; mock/HIL profiles can exercise AUTO with a loaded mission, valid attitude/heading/depth, healthy communication, and ready allocator/backend.


## 9. SysID data path

SysID telemetry is now available before LMPC synthesis:

```text
/tyrant/sysid/control
        ↓
SysID session (experiment_id + profile_id)
        ↓
/tyrant/sysid/sample @ 20 Hz
```

Each sample synchronizes manual command, requested wrench, reduced state, raw IMU, pressure, mode/safety, and the eight normalized thruster commands accepted by the actuator backend. The thruster fields remain zero/invalid in the production-safe profile and carry virtual commands in mock/HIL profiles. They are command records, not measured thrust; HIL data is not a vehicle-identification dataset.

Start a recording session on the laptop/Jetson with:

```bash
./companion/jetson/run_sysid_session.sh 101 6
```

See `docs/sysid.md` for the dataset contract.

## 10. TAM foundation

`control/thruster_allocation` constructs the 6x8 matrix from actual geometry using:

```text
B_i = [ d_i ; r_i × d_i ]
```

No generic 8-thruster layout is used for production. Explicit synthetic geometry is available only in mock/HIL profiles. Before the production allocator is enabled, fill `docs/thruster_geometry_template.csv` from the Tyrant CAD/assembled vehicle and freeze numbering/directions. See `docs/tam.md`.

## 11. End-to-end mock thruster stack

The main production and development actuation profiles are:

```text
teensy41
  production-safe profile
  production geometry unavailable -> allocator_ready=false
  actuator backend DISABLED -> no physical output

teensy41-mock-thrusters
  explicit synthetic geometry
  allocator active
  output goes only to MockThrusterBackend
  no physical PWM / ESC output

teensy41-hil
  synthetic geometry + MockThrusterBackend
  reduced state supplied by the ROS plant
  no physical PWM / ESC output

teensy41-pwm-skeleton
  physical Servo/PWM code is compiled
  all pins intentionally 0xFF/unconfigured
  backend init fails closed -> no channel attached
```

Build the software-only profile with:

```bash
cd ~/tyrant-simple/firmware/teensy
pio run -e teensy41-mock-thrusters -t clean
pio run -e teensy41-mock-thrusters
pio run -e teensy41-mock-thrusters -t upload
```

After rebuilding `tyrant_interfaces`, inspect:

```bash
ros2 topic echo /tyrant/control/wrench_request
ros2 topic echo /tyrant/control/thruster_command
```

`/tyrant/control/thruster_command` publishes eight normalized virtual actuator commands plus allocator status, residual, saturation, and `mock_backend: true`. The synthetic geometry is intentionally non-physical and must never be copied into the production geometry configuration.

With the normal `teensy41` build, expect:

```text
allocator_ready: false
valid: false
enabled: false
command: [0,0,0,0,0,0,0,0]
```

until verified chassis geometry is entered.

## 12. PS / joystick teleop with mock thrusters

The ROS 2 workspace now includes `tyrant_teleop`. Controller mappings are YAML-configurable because axis/button indices vary by controller and Linux driver.

Install the ROS joystick driver if it is not already present, then build the workspace and calibrate the real controller:

```bash
ros2 run joy joy_node
ros2 run tyrant_teleop tyrant_joy_probe
```

Move one control at a time and update:

```text
ros2_ws/src/tyrant_teleop/config/ps_controller.yaml
```

For an end-to-end software test, upload the mock-thruster firmware profile:

```bash
cd ~/tyrant-simple/firmware/teensy
pio run -e teensy41-mock-thrusters -t upload
```

Then launch joystick + teleop:

```bash
source /opt/ros/humble/setup.bash
source ~/tyrant-simple/ros2_ws/install/setup.bash
ros2 launch tyrant_teleop ps_teleop.launch.py
```

The PRD V0.3 button baseline is Cross = MANUAL, Square = IDLE, Circle = SAFE, Triangle = surface reference, and L1 = deadman. The teleop node requires the deadman button before streaming `ManualCommand`. Deadman release sends one neutral command and then stops the stream so the Teensy 250 ms freshness gate can force zero wrench. A longer `/joy` loss can request `SAFE`, and the development teleop process publishes the host heartbeat by default. See [`docs/teleop.md`](docs/teleop.md).


## 13. Mission + emergency recovery software stage

Mission sequencing and emergency recovery are now implemented without bypassing the normal controller/allocator path:

```text
MANUAL command ─┐
MissionManager ─┼→ StabilizedManualController → Wrench → TAM/Allocator
Emergency      ─┘
```

Mission steps currently support wait, timed surge/sway, depth targets, heading targets, and surface targets. AUTO is fail-closed: it requires a loaded mission, valid attitude/heading/depth, healthy communication, and ready allocator/backend. Therefore normal production `teensy41` still rejects AUTO while real thruster geometry and a ready backend are unavailable; mock/HIL profiles can test it end-to-end when the readiness conditions are met.

Emergency remains a separate latched mode. `ZERO_THRUST` requests no actuation. `CONTROLLED_SURFACE` uses the same stabilized controller to command ascent only while attitude/depth remain valid; loss of those signals or recovery timeout returns to zero thrust.

See [`docs/mission_emergency.md`](docs/mission_emergency.md) for ROS examples and policy details.

## 14. Actuation backend status

The control stack now has a fail-closed actuator boundary:

```text
normalized ThrusterCommand[8]
        -> DISABLED / MOCK / PWM skeleton
```

Default `teensy41` does **not** produce physical PWM. `teensy41-mock-thrusters` is the software-only end-to-end profile. `teensy41-pwm-skeleton` only compiles the Servo/PWM path; all pins remain intentionally invalid (`0xFF`), so initialization fails closed. See `docs/actuation_pwm.md`.

Monitor backend health with `/tyrant/actuation/status`.


## 15. HIL plant + automatic SysID excitation

Before chassis assembly, use the explicit HIL profile to close the loop through the real Teensy controller, TAM, allocator, mock backend, and SysID recorder while ROS supplies a synthetic reduced plant:

```bash
cd ~/tyrant-simple/firmware/teensy
pio run -e teensy41-hil -t upload
```

Then, with the micro-ROS agent active:

```bash
cd ~/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch tyrant_sim hil_plant.launch.py
```

In another terminal, run a deterministic excitation:

```bash
ros2 run tyrant_sim tyrant_sysid_excitation --ros-args \
  -p experiment_id:=1001 \
  -p profile:=step_yaw \
  -p amplitude:=0.25 \
  -p duration_s:=12.0
```

Or use the helper:

```bash
./companion/jetson/run_hil_sysid.sh 1001 step_yaw 0.25 12
```

The simulator publishes `/tyrant/sim/state_input`; the HIL firmware freshness-gates that state at 200 ms. If simulated state disappears, reduced-state validity is cleared and control fails closed.

The HIL plant is deliberately synthetic. It validates software plumbing and SysID methodology only; its datasets are marked as HIL and must not be used as the final LMPC vehicle model. See [`docs/hil_sim_sysid.md`](docs/hil_sim_sysid.md).

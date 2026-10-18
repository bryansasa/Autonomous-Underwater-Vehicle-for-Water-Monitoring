# Validation Status

This file records checks reported during baseline generation. Its environment limitations describe that historical environment, not the current laptop. Test counts describe coverage, not proof that every case has run on physical hardware. The local bring-up guide records later bench observations and pending checks; new runs should be recorded separately with their environment and result.

## Local validation evidence — 2026-10-07

The following checks were completed on the local Ubuntu laptop with a Teensy 4.1 connected as `/dev/ttyACM0`. Physical PWM/ESC output was not enabled.

- ROS 2 Humble workspace built successfully for `tyrant_interfaces`, `tyrant_teleop`, and `tyrant_sim`.
- The 8 `tyrant_teleop` mapper tests and 10 `tyrant_sim` plant/profile tests passed: **18 passed**.
- Firmware profiles compiled successfully: `teensy41`, `teensy41-mock-thrusters`, `teensy41-hil`, and `teensy41-pwm-skeleton`.
- Teensy core regression passed: **155 cases** in `teensy41-test`.
- ConnectionManager regression passed: **4 cases** in `teensy41-test-connection`.
- Production-safe firmware was uploaded successfully after the regression run.
- micro-ROS serial communication, host heartbeat, `/tyrant_teensy`, and system health were verified.
- HWT905 attitude state was valid. FullDepth was not physically installed; depth-dependent software was tested through HIL state injection.
- Bluetooth controller input was verified through `joy_node` and `tyrant_teleop`. The PRD mapping was exercised: Cross/MANUAL, Square/IDLE, Circle/SAFE, Triangle/surface reference, and L1/deadman.
- Manual command freshness and heartbeat safety behavior were verified: stale manual input zeros the wrench and heartbeat loss returns the vehicle to SAFE.
- HIL initially required `clean_microros` because the cached micro-ROS library still had the default publisher capacity. After rebuilding with `tyrant_microros.meta`, the HIL node connected successfully.
- HIL closed-loop state, controller signs, and virtual thruster output were verified. The `step_yaw` SysID session completed through START, excitation, STOP, and SAFE.
- A one-step HIL depth mission reached `0.4883 m` for a `0.5 m` target with `0.05 m` tolerance, then completed and returned to SAFE.
- HIL controlled-surface recovery reached `0.0954 m` from the deeper starting state with attitude, heading, and depth validity preserved.

These results validate the local software/HIL workflow. They do not qualify the physical FullDepth installation, production thruster geometry, ESC/PWM mapping, wet vehicle dynamics, or the final LMPC model.

## Passed in generation environment

- Clean repository contains no full-EKF source files.
- All quoted local C/C++ includes resolve inside the repository.
- Laptop ROS interface messages and firmware `extra_packages` messages are byte-identical.
- `simple_state_estimator.cpp` host-compiles with:

```text
-std=c++17 -Wall -Wextra -Werror
```

- Core production modules used by the test build pass host syntax validation with `-Wall -Wextra -Werror`.
- Existing production/test translation units retain the previous host syntax validation; the new manual-control core also host-compiles with `-Wall -Wextra -Werror`.
- Test suite now contains **155 cases**, including TAM construction, damped least-squares allocation, mock-backend fail-closed behavior, stabilized manual control, and SysID regression.
- 60 s stationary simple-estimator simulation:

```text
roll  ~= -5.00 deg
pitch ~=  0.00 deg
yaw   ~= 84.30 deg
```

- Injected residual yaw-rate bias of `+0.01 rad/s` converges to approximately `+0.00996 rad/s` while magnetic heading stays bounded.

## Not run in generation environment

The generation container does not provide PlatformIO (`pio`) or a ROS 2 Humble installation. Run the actual Teensy/Unity and ROS builds on the development laptop:

```bash
cd ~/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tyrant_interfaces tyrant_teleop tyrant_sim --symlink-install

cd ~/tyrant-simple/firmware/teensy
pio test -e teensy41-test
pio test -e teensy41-test-connection
pio run -e teensy41
```

The host syntax checks validate C++ structure, but they are not a substitute for the real PlatformIO/Teensy Unity runs.

## Hardware assumptions copied into this baseline

- HWT905 serial: `Serial1`
- baud: `9600`
- mounting: `[+X, -Y, -Z]` sensor axes into BODY-FRD
- FullDepth/MS5837 pressure source: bound to default `Wire` I2C bus at 100 kHz, sampled at 5 Hz
- depth density baseline: `1025 kg/m^3` (seawater)
- FullDepth driver host syntax check with MS5837/Wire stubs: PASS
- manual command timeout: 250 ms
- manual output: normalized wrench request -> DLS allocator -> mock 8-channel backend; production geometry remains unavailable so the normal `teensy41` profile stays fail-closed
- AUTO: readiness-gated; production stays blocked without real thruster geometry, mock profile can exercise missions

## Stabilized MANUAL controller validation

Added temporary pre-LMPC control path:

```text
surge/sway -> direct normalized effort
heave      -> depth-reference rate -> P depth hold
roll/pitch -> bounded angle reference -> PD
 yaw        -> heading-reference rate -> PD
```

Host compilation of `manual_wrench_mapper.cpp` + `stabilized_manual_controller.cpp` passed with:

```text
-std=c++17 -Wall -Wextra -Werror
```

A host behavior harness produced a finite bounded request for a mixed command/state case:

```text
x=0.4000
z=0.0200
k=-0.2000
m=0.1000
n=0.1178
```

This confirms the expected correction signs for the chosen BODY-FRD convention in that synthetic case. Actual `pio test` and hardware-loop behavior still require the user's Teensy/PlatformIO environment; `pio` is not installed in this container.


## TAM / SysID foundation validation

- TAM builder implements each enabled thruster column as `[d_i; r_i x d_i]` in BODY FRD.
- Direction vectors are normalized; zero-length and non-finite geometry are rejected.
- No production Tyrant geometry is invented or hard-coded.
- SysID recorder uses explicit START/STOP sessions with experiment/profile IDs.
- SysID samples are rate-limited to 20 Hz and contain command, requested wrench, reduced state, raw IMU, pressure, mode/safety, and fixed eight-thruster input slots.
- Damped least-squares allocator core host-compiles with `-Wall -Wextra -Werror`.
- Synthetic full-rank mock geometry produces a mixed-wrench residual of approximately `3.1e-4` in the host harness.
- Mock backend host harness verifies valid command storage and invalid-command fail-closed neutralization.
- Production firmware does not use synthetic geometry. The explicit `teensy41-mock-thrusters` and `teensy41-hil` profiles enable it for software validation.
- SysID now records the command accepted by the backend. In production-safe mode that remains invalid/zero until real geometry exists; in mock mode it is virtual software-test input only.

## PS / joystick teleop validation

- Added `ros2_ws/src/tyrant_teleop` as a configurable ROS 2 Python package.
- Mapping logic is configurable for the actual PS4/PS5/driver combination. The current YAML button baseline follows PRD V0.3; device indices and axis signs still require hardware verification.
- Deadman release sends one neutral command and then stops command publication so Teensy freshness can expire to zero wrench.
- `/joy` timeout stops command publication; a longer timeout can request `SAFE`.
- Development teleop heartbeat is configurable and can later be disabled when a Jetson supervisor owns host heartbeat.
- Eight pure-Python mapper tests pass in the generation environment.
- Python source and launch files pass `py_compile` in the generation environment.
- Actual `joy_node`, `rclpy`, `colcon`, and physical controller behavior still require the ROS 2 Humble development laptop/Jetson.


## Mission / emergency validation

- `mission_manager.cpp`, `emergency_recovery_manager.cpp`, updated safety core, and `main.cpp` pass host C++ syntax checks with `-Wall -Wextra -Werror`.
- Mission/emergency behavior harness PASS: depth mission produces positive-down heave, controlled-surface produces negative/up heave, mission completes inside tolerance, and recovery completes near surface.
- New mission and emergency Unity translation units pass host syntax validation.
- Safety regression now covers explicit AUTO readiness and separate EMERGENCY actuation authority.
- micro-ROS interface source passes host syntax validation against generated local stubs including the four new ROS messages.
- Production AUTO remains fail-closed because `allocator_ready` is false until real geometry exists.
- Controlled-surface recovery is development logic only; sea-trial tuning/authorization still requires assembled-vehicle validation.

## PWM/ESC boundary validation

- `thruster_output_mapper.cpp`: host compile with `-Wall -Wextra -Werror` PASS.
- `pwm_thruster_backend.cpp` with physical output disabled: host compile PASS.
- `thruster_backend.cpp` in mock mode: host compile PASS.
- Actuation behavior harness: PASS (neutral, forward/reverse mapping, mock apply, 100 ms watchdog neutralization/fault latch).
- `main.cpp` syntax with mock backend + synthetic geometry stubs: PASS.
- Total Teensy `RUN_TEST` cases: 155.

Actual PlatformIO/Servo and ROS 2 builds still need to run on the development laptop because `pio` and `colcon` are unavailable in this environment.


## HIL plant / automatic SysID validation

- Added `teensy41-hil`: synthetic geometry + mock backend + ROS-injected reduced state; physical PWM remains unavailable.
- HIL state source host-compiles with `-std=c++17 -Wall -Wextra -Werror`.
- `main.cpp` HIL branch passes host syntax validation with local Arduino stubs.
- `ros_interface.cpp` HIL subscriber path passes host syntax validation with generated local micro-ROS/message stubs.
- HIL state freshness is 200 ms; stale state clears attitude/heading/depth validity and therefore closes the controller/autonomy gates.
- `tyrant_sim` pure Python regression: **10/10 PASS** (synthetic TAM reconstruction, depth/yaw signs, surface clamp, restoring behavior, deterministic step/PRBS/chirp profiles, profile-ID contract).
- `tyrant_sim` Python modules and launch file pass `py_compile`.
- New `test_sim_state_source` contributes 7 Unity cases, bringing the Teensy total to **155**.
- HIL helper metadata explicitly records `hil=true` and `validated_vehicle_model=false` so synthetic bags are not confused with wet vehicle SysID.

The reduced plant coefficients are development-only. They do not validate vehicle mass/inertia, damping, buoyancy, thrust curves, cross-coupling, or the final LMPC prediction model.

# Tyrant Simple Architecture

## Scope

This baseline intentionally removes the full 15-state ESKF from runtime and source.
It does not estimate X/Y position or translational velocity from double-integrated IMU data.

## State source

- Roll/pitch: gyro propagation + accelerometer complementary correction.
- Yaw: gyro propagation + 2-state Kalman filter `[yaw, yaw_rate_bias]` corrected by tilt-compensated magnetometer heading.
- Depth: FullDepth/MS5837 absolute pressure over I2C -> `PressureSource` -> `DepthEstimator`, valid after an explicit surface-pressure reference is set.

## Current manual control stage

The temporary pre-LMPC vehicle-level controller is:

```text
/tyrant/manual/command
  -> ManualCommandManager
  -> MANUAL + safety + freshness gate
  -> StabilizedManualController
       surge/sway: direct normalized effort
       heave: depth-reference rate -> P depth hold
       roll/pitch: angle reference -> PD stabilization
       yaw: heading-reference rate -> PD heading hold
  -> normalized BODY-FRD WrenchRequest [X Y Z K M N]
       -> /tyrant/control/wrench_request (telemetry)
       -> TAM / damped least-squares allocator
       -> normalized ThrusterCommand[8]
       -> selected thruster backend
       -> /tyrant/control/thruster_command (backend-applied command telemetry)
```

The request remains dimensionless in `[-1,+1]`; it is not yet a physical N/Nm wrench. The software path already includes TAM, damped least-squares allocation, and the actuator backend. Constrained/QP allocation is still future work. Normal `teensy41` has no configured production geometry and uses the DISABLED backend, so this path cannot drive physical thrusters. Manual commands expire after 250 ms independently of the host-heartbeat timeout.

Stale/blocked control resets held depth/yaw references. When control resumes, references latch the current depth/yaw to avoid a large command jump. Invalid depth disables `Z` while preserving the other valid axes; invalid heading disables `N`; invalid attitude disables the whole request.

## Control roadmap

Manual / mission references should be expressed at vehicle level, not as per-thruster PWM.

- Surge/sway before DVL: bounded effort/wrench command, optionally time-based.
- Depth: temporary P hold from pressure-derived depth.
- Yaw: temporary PD heading hold from simple yaw estimator.
- Roll/pitch: temporary PD stabilization from simple attitude estimator.
- TAM builder and damped least-squares allocator are present, with unit/regression tests in the repository. The explicit `teensy41-mock-thrusters` profile uses synthetic geometry and a MOCK backend only for software validation. Normal production `teensy41` has no configured geometry and uses the DISABLED backend; physical output also requires verified PWM configuration and explicit build enablement.
- Constrained/QP allocation and physical thrust limits follow after thruster characterization.
- Reduced LMPC remains downstream of verified geometry and thruster characterization, SysID data collection, model identification, and independent model validation with the available reduced-state feedback.

AUTO is implemented for the reduced mission sequencer. Its readiness gate requires a mission ready for AUTO, valid attitude/heading/depth state, healthy host communication, a ready allocator, and a ready actuator backend. The production profile fails this gate because production geometry is unavailable and its backend is disabled. The mock-thruster and HIL profiles can exercise AUTO when all readiness conditions are met.


## Production sensor bindings

```text
HWT905
  -> Serial1 @ 9600
  -> SensorManager

FullDepth / MS5837-30BA
  -> Wire (Teensy 4.1 SDA18/SCL19) @ 100 kHz
  -> FullDepthPressureSource @ 5 Hz
  -> SensorManager
  -> DepthEstimator
```

The FullDepth driver intentionally does not use the library's built-in `depth()` output. The project owns surface-zero and fluid-density configuration so depth semantics remain explicit and testable.


## SysID before LMPC

The controller/plant boundary is logged through `/tyrant/sysid/sample` during explicit sessions. The recorder uses a 50 ms nominal sampling period (20 Hz), checked from the control loop; recorded timestamps determine the actual sample intervals. Samples already include the requested normalized wrench and all eight normalized commands reported as applied by the selected actuator backend, together with the command-valid flag, reduced state, and sensor snapshots.

Backend-applied commands describe software output, not measured thrust or motor feedback. In mock/HIL builds they are simulated commands; in the normal production build the disabled backend reports neutral, invalid commands. Physical SysID requires verified geometry, a configured and explicitly enabled physical backend, and thruster characterization before these normalized commands can be interpreted as physical plant inputs.

LMPC remains downstream of the workflow:

```text
actual geometry + thruster characterization
        -> TAM / constrained allocator
        -> SysID excitation + synchronized dataset
        -> grey-box model identification
        -> independent model validation
        -> reduced LMPC synthesis
```


## Operator input / teleop

The companion-side teleop boundary is device-agnostic:

```text
PS / USB controller
  -> joy_node -> /joy
  -> tyrant_teleop
  -> /tyrant/manual/command
```

Axis/button indices live in YAML and are calibrated on the actual Linux/controller combination. The operator must hold a deadman button before commands are streamed. Loss of the Joy stream stops command publication; the Teensy freshness gate then zeroes the wrench. The development teleop node can also own host heartbeat and request SAFE after an extended joystick timeout.


## Mission and emergency control ownership

The reduced control stack now has three mutually exclusive command sources selected by vehicle mode:

```text
MANUAL     -> fresh host ManualCommand
AUTO       -> MissionManager virtual ManualCommand
EMERGENCY  -> EmergencyRecoveryManager virtual ManualCommand
                  |
                  v
        StabilizedManualController
                  |
                  v
             WrenchRequest
                  |
                  v
          TAM / DLS Allocator
                  |
                  v
          Thruster backend
```

AUTO uses the mission, reduced-state, communication, allocator, and backend readiness gate described above. The production profile has no configured geometry and its actuator backend is disabled. EMERGENCY is latched and has a separate actuation authority so a controlled-surface recovery can continue after host heartbeat is lost, but only while the recovery manager still has valid attitude/depth state and has not reached its surface target or runtime limit. Emergency commands still pass through the same allocator and backend checks.

## Development HIL boundary

A dedicated `teensy41-hil` profile replaces the physical reduced-state source with `/tyrant/sim/state_input` while keeping the Teensy controller, mission/emergency logic, TAM, allocator, mock actuator backend, and SysID recorder unchanged. This is explicitly a development profile: synthetic thruster geometry and synthetic reduced plant coefficients are never production defaults.

```text
ROS reduced plant -> /tyrant/sim/state_input -> Teensy control stack
        ^                                      |
        |                                      v
        +----- /tyrant/control/thruster_command+
```

The injected state expires after 200 ms. Stale simulation state clears reduced-state validity and fails closed through the normal controller/autonomy gates.

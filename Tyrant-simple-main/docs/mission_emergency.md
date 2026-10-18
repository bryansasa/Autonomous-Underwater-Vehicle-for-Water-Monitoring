# Mission + Emergency Recovery

This stage adds software-only autonomous sequencing and emergency recovery while keeping the existing reduced controller and allocator boundary.

## Control ownership

```text
MANUAL
  /tyrant/manual/command
        -> StabilizedManualController

AUTO
  MissionManager
        -> virtual ManualCommand
        -> StabilizedManualController

EMERGENCY
  EmergencyRecoveryManager
        -> virtual ManualCommand
        -> StabilizedManualController
```

All three paths still produce the same normalized BODY-FRD `WrenchRequest`, so TAM, allocation, mock/PWM backends, and SysID do not need separate control implementations.

## Mission steps

The fixed mission queue holds up to 16 steps:

- `WAIT`
- `SURGE_TIME`
- `SWAY_TIME`
- `DIVE_TO_DEPTH`
- `TURN_TO_HEADING`
- `SURFACE_TO_DEPTH`

Time-based translation is intentionally effort + duration because no trustworthy surge/sway position or velocity feedback exists. Depth and heading steps use the reduced state as termination feedback.

Mission configuration is accepted only in `IDLE` or `SAFE`. `AUTO` readiness requires:

- mission queue loaded;
- valid attitude, heading, and depth state;
- allocator ready;
- actuator backend ready;
- healthy host communication.

Because production thruster geometry is unavailable and the production backend is DISABLED, normal `teensy41` remains unable to enter AUTO. The `teensy41-mock-thrusters` and `teensy41-hil` builds can exercise AUTO with synthetic geometry when all readiness conditions are met.

When a mission completes or fails, firmware forces `SAFE` and the normal propulsion path is disabled.

## Example mock mission

Keep `/tyrant/host_heartbeat` alive, set a valid depth surface reference, and use the mock-thruster build.

Clear the queue:

```bash
ros2 topic pub --once /tyrant/mission/command \
  tyrant_interfaces/msg/MissionCommand \
  "{request_id: 1, command: 0, step_type: 1, target: 0.0, effort: 0.0, duration_ms: 0, tolerance: 0.0}"
```

Append a dive to 1 m:

```bash
ros2 topic pub --once /tyrant/mission/command \
  tyrant_interfaces/msg/MissionCommand \
  "{request_id: 2, command: 1, step_type: 4, target: 1.0, effort: 0.5, duration_ms: 0, tolerance: 0.05}"
```

Append forward effort for 5 s:

```bash
ros2 topic pub --once /tyrant/mission/command \
  tyrant_interfaces/msg/MissionCommand \
  "{request_id: 3, command: 1, step_type: 2, target: 0.0, effort: 0.3, duration_ms: 5000, tolerance: 0.0}"
```

Append a turn to +90 degrees (`1.5708 rad`):

```bash
ros2 topic pub --once /tyrant/mission/command \
  tyrant_interfaces/msg/MissionCommand \
  "{request_id: 4, command: 1, step_type: 5, target: 1.5708, effort: 0.4, duration_ms: 0, tolerance: 0.0873}"
```

Request AUTO only after `/tyrant/system/health` reports `autonomy_ready: true`:

```bash
ros2 topic pub --once /tyrant/mode/request \
  tyrant_interfaces/msg/ModeRequest \
  "{request_id: 20, requested_mode: 3}"
```

Start the mission:

```bash
ros2 topic pub --once /tyrant/mission/command \
  tyrant_interfaces/msg/MissionCommand \
  "{request_id: 5, command: 2, step_type: 1, target: 0.0, effort: 0.0, duration_ms: 0, tolerance: 0.0}"
```

Monitor:

```bash
ros2 topic echo /tyrant/mission/status
ros2 topic echo /tyrant/control/wrench_request
ros2 topic echo /tyrant/control/thruster_command
```

## Emergency policies

`SAFE` remains zero normal propulsion. `EMERGENCY` is a separate latched vehicle mode with an explicit recovery policy.

### ZERO_THRUST

```text
EMERGENCY latched
-> no recovery command
-> zero wrench / neutral thruster command
```

Trigger:

```bash
ros2 topic pub --once /tyrant/emergency/control \
  tyrant_interfaces/msg/EmergencyControl \
  "{request_id: 100, command: 1}"
```

### CONTROLLED_SURFACE

If attitude and depth remain valid:

```text
EMERGENCY latched
-> negative heave command (up)
-> level roll/pitch stabilization remains active
-> stop active thrust near configured surface depth
```

Trigger:

```bash
ros2 topic pub --once /tyrant/emergency/control \
  tyrant_interfaces/msg/EmergencyControl \
  "{request_id: 101, command: 2}"
```

Controlled surface intentionally does not require continuing host heartbeat after EMERGENCY is latched. If depth/attitude becomes invalid or the recovery runtime expires, it fails closed to zero thrust.

`EMERGENCY` is latched by the vehicle-mode state machine. Returning to normal operation currently requires reboot/reset; this prevents a host command from silently cancelling an emergency state.

Development recovery constants are in `config/mission_config.h` and are not sea-trial tuning values.

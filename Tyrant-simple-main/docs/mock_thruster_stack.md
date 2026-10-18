# Tyrant Simple — Mock Thruster Stack

Purpose: validate the complete software path before physical assembly without inventing production geometry.

```text
Manual command
  -> stabilized controller
  -> normalized WrenchRequest [X Y Z K M N]
  -> TAM
  -> damped least-squares allocator
  -> ThrusterCommand[8]
  -> MockThrusterBackend
  -> ROS /tyrant/control/thruster_command
  -> SysID sample
```

## Build profiles

- `teensy41`: production-safe. Real geometry is not configured and the backend is DISABLED, so allocation is unavailable and actuator commands remain zero/invalid.
- `teensy41-mock-thrusters`: defines `TYRANT_USE_SYNTHETIC_THRUSTER_GEOMETRY` and `TYRANT_USE_MOCK_THRUSTER_BACKEND`. It uses an explicit non-physical full-rank geometry solely to exercise software behavior, with reduced state from the physical sensors. There is no PWM/ESC output.
- `teensy41-hil`: uses the same synthetic geometry and mock backend, with reduced state supplied through `/tyrant/sim/state_input` instead of the physical estimator. There is no PWM/ESC output.

## Safety behavior

The mock backend fails closed. Invalid/non-finite allocator output is replaced by zero command. A valid but disabled request is also stored as zero command. SAFE or a stale MANUAL command zeroes the output. Loss of host communication forces MANUAL/AUTO to SAFE. A latched EMERGENCY controlled-surface policy has separate authority and can continue without host communication while its required state remains valid; see `docs/mission_emergency.md`.

## What this does not validate

It does not validate final thruster numbering, chassis lever arms, motor direction, thrust limits, deadzone, ESC mapping, hydrodynamics, or LMPC plant dynamics. Those require verified geometry and physical characterization.

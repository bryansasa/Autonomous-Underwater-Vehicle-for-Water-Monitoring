# Tyrant Simple — PWM/ESC Actuation Boundary

## Purpose

This layer completes the software boundary from normalized 8-thruster commands to ESC-style PWM without enabling physical output by default.

Production/default `teensy41` uses the **DISABLED** backend. `teensy41-mock-thrusters` uses the **MOCK** backend. Physical Servo/PWM code is compiled only when `TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT` is explicitly set.

## Runtime pipeline

```text
WrenchRequest [X Y Z K M N]
        ↓
Allocator
        ↓
normalized ThrusterCommand[8]
        ↓
ThrusterBackend
   ├─ DISABLED (default production)
   ├─ MOCK     (software test)
   └─ PWM      (future physical hardware)
        ↓
ESC pulse_us[8]
```

## Fail-closed rules

- Physical output is not enabled in the normal production build.
- All eight PWM pins must be configured; `0xFF` is intentionally invalid.
- Every channel must satisfy `reverse_us < neutral_us < forward_us`.
- Non-finite or invalid commands immediately neutralize and latch a fault.
- An enabled command older than `100 ms` neutralizes and latches `COMMAND_TIMEOUT`.
- A latched actuator fault forces MANUAL/AUTO to SAFE in `main.cpp`.
- AUTO readiness additionally requires `thrusterBackendReady()`.

## Development mapping

The current `1100 / 1500 / 1900 us` and 5% deadband values are **placeholders only**. They are not claimed as calibrated Tyrant ESC values.

Before real motor operation, replace them using single-thruster bench characterization:

1. Verify exact Teensy pin for T1..T8.
2. Verify neutral pulse.
3. Find forward/reverse start thresholds and deadzone.
4. Verify sign/direction for every channel.
5. Determine safe min/max pulse.
6. Record command → thrust/current data for SysID.

## ROS monitoring

`/tyrant/actuation/status` reports:

- backend type
- configuration/readiness
- physical-output flag
- latched fault/fault code
- apply/reject/neutralize counters
- command age
- final PWM pulse array

`/tyrant/control/thruster_command` remains the normalized allocator/backend command.

## Compile-only physical backend check

```bash
pio run -e teensy41-pwm-skeleton
```

This build compiles the physical Servo backend but, with the current 0xFF pin configuration, initialization fails closed and no PWM channel is attached.

# PWM/ESC Actuation Stage

See `docs/actuation_pwm.md`.

Current safety state:

- `teensy41`: backend disabled, no physical PWM.
- `teensy41-mock-thrusters`: virtual 8-thruster backend.
- `teensy41-pwm-skeleton`: physical code compile check, pins deliberately invalid.

Physical motor activation is intentionally deferred until final thruster geometry, pin mapping, ESC neutral/deadzone, and thrust-direction characterization are available.

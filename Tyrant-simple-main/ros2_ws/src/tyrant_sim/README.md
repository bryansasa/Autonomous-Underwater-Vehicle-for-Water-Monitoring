# tyrant_sim

Development-only HIL reduced plant and deterministic SysID excitation tools.

This package is not a validated hydrodynamic model. Its purpose is to exercise the real Teensy command/controller/mission/TAM/allocator/SysID code before vehicle assembly.

## Nodes

- `tyrant_plant_sim`: subscribes to `/tyrant/control/thruster_command`, applies the same synthetic mock TAM convention as `teensy41-hil`, integrates a small reduced plant, and publishes `/tyrant/sim/state_input`.
- `tyrant_sysid_excitation`: publishes heartbeat, MANUAL request, SysID START/STOP, and deterministic excitation on `/tyrant/manual/command`.

Use only with `teensy41-hil` or another explicitly non-physical setup until the real actuator procedure is approved.

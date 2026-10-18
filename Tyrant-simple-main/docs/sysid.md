# Tyrant Simple — SysID Dataset Contract

SysID is collected before LMPC synthesis so the identified model is based on actual vehicle response rather than an assumed generic underwater model.

## Runtime topics

- `/tyrant/sysid/control`: START/STOP a named numeric session.
- `/tyrant/sysid/status`: session acknowledgement/status.
- `/tyrant/sysid/sample`: synchronized 20 Hz input/output sample.

Each sample contains:

- experiment ID and profile ID;
- current vehicle mode and propulsion gate;
- normalized manual command;
- normalized requested body wrench `[X Y Z K M N]`;
- eight actuator command slots;
- reduced state: roll, pitch, yaw, angular rates, yaw-rate bias, depth;
- raw accelerometer and gyro;
- raw pressure and temperature;
- validity flags.

The eight actuator slots copy the normalized command accepted by the actuator backend. In the normal production-safe build they remain invalid/zero while production geometry and a ready actuator backend are unavailable. In `teensy41-mock-thrusters` and `teensy41-hil` they contain virtual commands for software validation only. Once characterized PWM hardware is integrated, these commands provide the actuator input record for grey-box identification; they are not measured thrust or PWM pulse widths.

## Profile IDs

The host excitation generator in `ros2_ws/src/tyrant_sim/tyrant_sim/profiles.py` uses these IDs:

| Profile | Meaning |
|---:|---|
| 1 | surge step sequence |
| 2 | sway step sequence |
| 3 | heave/depth excitation |
| 4 | roll excitation |
| 5 | pitch excitation |
| 6 | yaw excitation |
| 10 | PRBS on any of the six axes, or yaw chirp |

These IDs are bookkeeping only; the firmware does not generate the excitation profile. Because all PRBS profiles and yaw chirp share ID 10, also record the exact profile name and parameters in the experiment metadata. Multisine excitation is not currently implemented.

## Recording on laptop/Jetson

After sourcing ROS 2 and the Tyrant workspace:

```bash
cd ~/tyrant-simple
./companion/jetson/run_sysid_session.sh 101 6
```

This starts experiment 101, profile 6, records the synchronized sample plus supporting raw topics to `~/tyrant_sysid/...`, and sends STOP on Ctrl+C.

## Data methodology

Do not use controller-output-only data as final thruster SysID. Final identification should use the actual per-thruster command after allocation plus the measured response. Record configuration/calibration version, tether configuration, ballast, battery condition, water condition, and experiment notes alongside the bag.


## Development-only HIL excitation

`tyrant_sim` can generate deterministic step, PRBS, and yaw-chirp profiles while `teensy41-hil` runs the real Teensy control/TAM/allocator/SysID code against a synthetic reduced plant. See `docs/hil_sim_sysid.md`.

HIL bags are only for software-pipeline validation. The helper marks them `hil=true` and `validated_vehicle_model=false`; do not mix them with wet vehicle identification data used for LMPC synthesis.

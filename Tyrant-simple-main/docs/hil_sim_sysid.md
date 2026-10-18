# Tyrant Simple — HIL Plant + Automatic SysID Excitation

This subsystem exists to validate software plumbing before vehicle assembly. It is **not** a hydrodynamic model and its bags must not be used as the final vehicle-identification dataset for LMPC.

## Closed-loop HIL architecture

```text
SysID excitation / Mission / Teleop
              ↓
        Teensy control path
              ↓
      Wrench → TAM → allocator
              ↓
         MockThrusterBackend
              ↓
/tyrant/control/thruster_command
              ↓
      tyrant_plant_sim (ROS 2)
              ↓
 /tyrant/sim/state_input
              ↓
     Teensy HIL state source
              └──────────────→ controller / mission / SysID
```

Use firmware environment:

```bash
pio run -e teensy41-hil -t upload
```

`teensy41-hil` explicitly enables:

- synthetic development thruster geometry;
- mock thruster backend;
- ROS-injected reduced state;
- no physical PWM output.

The simulated state input is freshness-gated. If `/tyrant/sim/state_input` stops for more than 200 ms, attitude/heading/depth validity is cleared and the controller fails closed.

## Build ROS 2

```bash
cd ~/tyrant-simple/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select tyrant_interfaces tyrant_teleop tyrant_sim --symlink-install
source install/setup.bash
```

## Start the plant manually

```bash
ros2 launch tyrant_sim hil_plant.launch.py
```

The node subscribes to:

```text
/tyrant/control/thruster_command
```

and publishes:

```text
/tyrant/sim/state_input
```

The plant currently models only the reduced feedback states available to `tyrant-simple`: depth/heave velocity, roll/pitch/yaw, and body angular rates. Surge/sway position or velocity are deliberately not invented.

## Automatic SysID excitation

Supported profiles:

```text
step_surge
step_sway
step_heave
step_roll
step_pitch
step_yaw
prbs_surge
prbs_sway
prbs_heave
prbs_roll
prbs_pitch
prbs_yaw
chirp_yaw
```

Step profiles reverse sign halfway through the active interval. PRBS is deterministic. The chirp uses a linearly increasing yaw excitation frequency.

Example:

```bash
ros2 run tyrant_sim tyrant_sysid_excitation --ros-args \
  -p experiment_id:=1001 \
  -p profile:=step_yaw \
  -p amplitude:=0.25 \
  -p duration_s:=12.0
```

The excitation node:

1. publishes host heartbeat;
2. repeatedly requests MANUAL until `/tyrant/mode/status` confirms it;
3. STARTs a SysID session;
4. records a neutral pre-roll;
5. applies the deterministic profile;
6. records a neutral post-roll;
7. STOPs SysID;
8. requests SAFE.

If MANUAL is not established in time or the vehicle leaves MANUAL during the session, the node aborts, publishes neutral, STOPs SysID, and requests SAFE.

## One-command helper

With the micro-ROS agent already running and the workspace sourced:

```bash
cd ~/tyrant-simple
./companion/jetson/run_hil_sysid.sh 1001 step_yaw 0.25 12
```

The helper launches the plant, records the useful ROS topics, runs the excitation, and marks metadata with:

```text
hil=true
validated_vehicle_model=false
```

This prevents HIL bags from being confused with wet vehicle SysID later.

## Local HIL evidence — 2026-10-07

The local HIL workflow was completed with a Teensy 4.1 on `/dev/ttyACM0`, the micro-ROS serial agent, and `tyrant_plant_sim`. FullDepth was not installed; the HIL `/tyrant/sim/state_input` supplied valid attitude, heading, and depth state. The firmware used synthetic geometry and `MockThrusterBackend`, so no physical PWM was produced.

The HIL profile first failed during entity creation because the cached micro-ROS library still had the default publisher capacity. Running `pio run -e teensy41-hil -t clean_microros` followed by a clean HIL build regenerated the library from `tyrant_microros.meta` and allowed the complete Teensy ROS entity set to connect.

After reconnection, the following passed:

- reduced state feedback with all three validity flags true;
- positive sign checks for surge, sway, heave/depth, and yaw;
- automatic `step_yaw` SysID session and return to SAFE;
- one-step depth mission: target `0.5 m`, final depth `0.4883 m`, tolerance `0.05 m`, state `COMPLETE`;
- controlled-surface emergency recovery: final depth `0.0954 m`, with attitude, heading, and depth remaining valid.

This is software and HIL evidence only. It does not validate the physical pressure sensor, thruster geometry, ESC characterization, hydrodynamics, or an LMPC prediction model.

## Why this exists before LMPC

This HIL loop is for validating:

- command ownership and mode transitions;
- stabilized controller signs;
- TAM/allocator path;
- mock actuator behavior;
- mission/emergency interactions;
- SysID session synchronization;
- excitation generator and bag methodology.

It does **not** validate final controller gains, hydrodynamic coupling, thrust curves, vehicle mass/inertia, damping, buoyancy, or an LMPC prediction model. Those must come from characterized hardware and wet SysID.

# Jetson Companion

Integrasi ESP + Teensy dan host sampling tersedia melalui paket
`tyrant_mission_host`: [panduan laptop dan persiapan Jetson](../../docs/payload_mission_host.md).
Dockerfile mencakup paket interface payload dan host baru. Supervisor di bawah
tetap agent/logger Teensy; belum otomatis meluncurkan koordinator atau agent ESP.

Deployment agent + logger: [panduan Jetson](../../docs/jetson_deployment.md).

Deployment host misi ARM64: [panduan deployment](../../docs/jetson_payload_mission_deployment.md).
Supervisor dual-agent dan heartbeat otomatis:
[panduan autostart](../../docs/jetson_autostart.md), melalui
`start_mission_autostart.sh` dan `run_mission_companion.py`.

`start_container.sh` dijalankan pada host Jetson. `entrypoint.sh` dan
`run_companion.py` menjalankan agent dan recorder di dalam container tanpa
heartbeat otomatis atau permintaan mode kontrol. Dockerfile tersedia untuk
build bersih; setup awal menggunakan snapshot container yang sudah berhasil.

Uji supervisor tanpa ROS/hardware:

```bash
python3 -m unittest discover -s companion/jetson -p 'test_*.py' -v
```

Bring-up order:
1. Validate the Teensy + HWT905 simple estimator on the laptop.
2. Build `ros2_ws` on the laptop and verify `/tyrant/simple_state`.
3. Clone this same repository to the Jetson.
4. Build the same `tyrant_interfaces` package on Jetson.
5. Connect the micro-ROS agent and verify telemetry before adding control/mission nodes.

Do not add LMPC here until the reduced state has passed stationary and motion hardware tests.


## SysID recorder

`run_sysid_session.sh <experiment_id> <profile_id>` starts a firmware SysID session and records the synchronized data plus supporting ROS topics into a rosbag.

## HIL SysID before assembly

`run_hil_sysid.sh <experiment_id> <profile> [amplitude] [duration_s]` launches the synthetic reduced plant, records the relevant ROS topics, and runs the deterministic SysID excitation node. Use it only with the `teensy41-hil` firmware profile. Generated metadata marks the session as HIL/non-validated so it is not confused with wet vehicle SysID.

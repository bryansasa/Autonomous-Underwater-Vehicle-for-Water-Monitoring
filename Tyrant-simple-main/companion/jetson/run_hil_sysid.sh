#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 4 ]]; then
    echo "Usage: $0 <experiment_id> <profile> [amplitude] [duration_s]" >&2
    echo "Examples:" >&2
    echo "  $0 1001 step_yaw 0.25 12" >&2
    echo "  $0 1002 prbs_heave 0.20 20" >&2
    exit 2
fi

EXPERIMENT_ID="$1"
PROFILE="$2"
AMPLITUDE="${3:-0.25}"
DURATION_S="${4:-12.0}"
OUTPUT_ROOT="${HOME}/tyrant_hil_sysid"
STAMP="$(date +%Y%m%d_%H%M%S)"
SESSION="hil_e${EXPERIMENT_ID}_${PROFILE}_${STAMP}"
SESSION_DIR="${OUTPUT_ROOT}/${SESSION}"
BAG_DIR="${SESSION_DIR}/bag"

mkdir -p "$SESSION_DIR"

cat > "${SESSION_DIR}/metadata.env" <<META
experiment_id=${EXPERIMENT_ID}
profile=${PROFILE}
amplitude=${AMPLITUDE}
duration_s=${DURATION_S}
started_at=${STAMP}
hil=true
validated_vehicle_model=false
META

cleanup()
{
    jobs -p | xargs -r kill >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

ros2 launch tyrant_sim hil_plant.launch.py &
PLANT_PID=$!

sleep 1

ros2 bag record \
    -o "$BAG_DIR" \
    /tyrant/sysid/sample \
    /tyrant/sysid/status \
    /tyrant/manual/command \
    /tyrant/control/wrench_request \
    /tyrant/control/thruster_command \
    /tyrant/simple_state \
    /tyrant/sim/state_input \
    /tyrant/mode/status \
    /tyrant/system/health \
    /tyrant/actuation/status &
BAG_PID=$!

sleep 1

ros2 run tyrant_sim tyrant_sysid_excitation --ros-args \
    -p experiment_id:="${EXPERIMENT_ID}" \
    -p profile:="${PROFILE}" \
    -p amplitude:="${AMPLITUDE}" \
    -p duration_s:="${DURATION_S}"

sleep 1
kill "$BAG_PID" >/dev/null 2>&1 || true
wait "$BAG_PID" >/dev/null 2>&1 || true
kill "$PLANT_PID" >/dev/null 2>&1 || true
wait "$PLANT_PID" >/dev/null 2>&1 || true

echo "HIL SysID bag saved to: ${BAG_DIR}"
echo "This dataset validates plumbing only; do not use it as the final LMPC vehicle-identification dataset."

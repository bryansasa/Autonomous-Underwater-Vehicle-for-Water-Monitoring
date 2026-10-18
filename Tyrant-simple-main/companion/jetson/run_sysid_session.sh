#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: $0 <experiment_id> <profile_id> [output_root]" >&2
    exit 2
fi

EXPERIMENT_ID="$1"
PROFILE_ID="$2"
OUTPUT_ROOT="${3:-$HOME/tyrant_sysid}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "$EXPERIMENT_ID" == "0" ]]; then
    echo "experiment_id must be non-zero" >&2
    exit 2
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
SESSION_NAME="sysid_e${EXPERIMENT_ID}_p${PROFILE_ID}_${STAMP}"
SESSION_DIR="${OUTPUT_ROOT}/${SESSION_NAME}"
BAG_DIR="${SESSION_DIR}/bag"

mkdir -p "$SESSION_DIR"

cat > "${SESSION_DIR}/metadata.env" <<META
experiment_id=${EXPERIMENT_ID}
profile_id=${PROFILE_ID}
started_at=${STAMP}
host=$(hostname)
META

if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$REPO_ROOT" rev-parse HEAD > "${SESSION_DIR}/git_commit.txt"
fi

stop_session()
{
    ros2 topic pub --once \
        /tyrant/sysid/control \
        tyrant_interfaces/msg/SysIdControl \
        "{request_id: 2, command: 0, experiment_id: ${EXPERIMENT_ID}, profile_id: ${PROFILE_ID}}" \
        >/dev/null 2>&1 || true
}

trap stop_session EXIT INT TERM

ros2 topic pub --once \
    /tyrant/sysid/control \
    tyrant_interfaces/msg/SysIdControl \
    "{request_id: 1, command: 1, experiment_id: ${EXPERIMENT_ID}, profile_id: ${PROFILE_ID}}"

echo "Recording SysID session: ${SESSION_NAME}"
echo "Press Ctrl+C to stop cleanly."

ros2 bag record \
    -o "$BAG_DIR" \
    /tyrant/sysid/sample \
    /tyrant/sysid/status \
    /tyrant/manual/command \
    /tyrant/control/wrench_request \
    /tyrant/simple_state \
    /tyrant/sensors/imu \
    /tyrant/sensors/pressure \
    /tyrant/mode/status \
    /tyrant/system/health

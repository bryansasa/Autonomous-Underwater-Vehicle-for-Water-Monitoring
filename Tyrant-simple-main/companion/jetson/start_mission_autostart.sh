#!/usr/bin/env bash
# Run on the Jetson host. Preserve old containers and ARM64 workspaces.
set -euo pipefail
container=tyrant-mission
image=${TYRANT_IMAGE:-tyrant-companion:bench}
agent_workspace=${TYRANT_AGENT_WORKSPACE:-/home/nvidia/ros2_docker/ws}
mission_workspace=${TYRANT_MISSION_WORKSPACE:-/home/nvidia/ros2_docker/mission_ws}
deployment_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for previous in ros2 tyrant-companion tyrant-mission-dev; do
    if [[ $(docker inspect --format '{{.State.Running}}' "$previous" 2>/dev/null || true) == true ]]; then
        echo "Stop $previous first: docker stop -t 30 $previous" >&2
        exit 1
    fi
done
if docker container inspect "$container" >/dev/null 2>&1; then
    echo "Container exists; inspect configuration before using docker start $container" >&2
    exit 1
fi
test -f "$agent_workspace/install/setup.bash"
test -f "$mission_workspace/install/setup.bash"
test -f "$deployment_dir/run_mission_companion.py"
docker image inspect "$image" >/dev/null
docker run -d --name "$container" \
    --init --network host --restart unless-stopped --stop-timeout 45 \
    --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
    --mount "type=bind,src=$agent_workspace,dst=/ws,readonly" \
    --mount "type=bind,src=$mission_workspace,dst=/mission_ws" \
    --mount "type=bind,src=$deployment_dir,dst=/deployment,readonly" \
    --mount type=bind,src=/dev,dst=/host-dev \
    --device-cgroup-rule='c 166:* rw' \
    -e "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}" -e PYTHONUNBUFFERED=1 \
    -e "TYRANT_HIL_PLANT=${TYRANT_HIL_PLANT:-false}" \
    -e "TYRANT_TEENSY_SIMULATED=${TYRANT_TEENSY_SIMULATED:-true}" \
    -e "TYRANT_PAYLOAD_NAMESPACE=${TYRANT_PAYLOAD_NAMESPACE:-/tyrant/payload_sim}" \
    -e "TYRANT_TEENSY_PORT=${TYRANT_TEENSY_PORT:-/host-dev/tyrant-teensy}" \
    -e "TYRANT_ESP_PORT=${TYRANT_ESP_PORT:-/host-dev/tyrant-esp}" \
    -e "TYRANT_OUTPUT_DIR=${TYRANT_OUTPUT_DIR:-/mission_ws/bags/missions}" \
    -e "TYRANT_PLAN=${TYRANT_PLAN:-/mission_ws/src/tyrant_mission_host/config/two_depth_hil_sampling_020m.yaml}" \
    --entrypoint /bin/bash "$image" /deployment/mission_entrypoint.sh

#!/usr/bin/env bash
# Run on the Jetson host after stopping other Tyrant containers.
set -euo pipefail
container=tyrant-mission-dev
image=${TYRANT_IMAGE:-tyrant-companion:bench}
agent_workspace=${TYRANT_AGENT_WORKSPACE:-/home/nvidia/ros2_docker/ws}
mission_workspace=${TYRANT_MISSION_WORKSPACE:-/home/nvidia/ros2_docker/mission_ws}

for previous in ros2 tyrant-companion; do
    if [[ $(docker inspect --format '{{.State.Running}}' "$previous" 2>/dev/null || true) == true ]]; then
        echo "Stop $previous first: docker stop -t 30 $previous" >&2
        exit 1
    fi
done
if docker container inspect "$container" >/dev/null 2>&1; then
    echo "Container exists. Inspect its mounts before using: docker start $container" >&2
    exit 1
fi
test -f "$agent_workspace/install/setup.bash"
test -d "$mission_workspace/src"
docker image inspect "$image" >/dev/null
docker run -d --name "$container" \
    --init --network host --restart no --stop-timeout 30 \
    --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
    --mount "type=bind,src=$agent_workspace,dst=/ws,readonly" \
    --mount "type=bind,src=$mission_workspace,dst=/mission_ws" \
    --mount type=bind,src=/dev,dst=/host-dev \
    --device-cgroup-rule='c 166:* rw' \
    -e "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}" -e PYTHONUNBUFFERED=1 \
    --entrypoint /bin/bash "$image" -c 'exec sleep infinity'

#!/usr/bin/env bash
# Run on the Jetson HOST. The original ros2 container is retained for rollback.
set -euo pipefail

container=tyrant-companion
image=${TYRANT_IMAGE:-tyrant-companion:bench}
workspace=${TYRANT_WORKSPACE:-/home/nvidia/ros2_docker/ws}
deployment_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

if [[ $(docker inspect --format '{{.State.Running}}' ros2 2>/dev/null || true) == true ]]; then
    echo 'Stop the existing ros2 container first: docker stop -t 30 ros2' >&2
    exit 1
fi
if docker container inspect "$container" >/dev/null 2>&1; then
    echo "Container already exists. Use docker start $container or inspect it before changing configuration." >&2
    exit 1
fi
test -d "$workspace"
docker image inspect "$image" >/dev/null

docker run -d --name "$container" \
    --init --network host --restart unless-stopped \
    --stop-timeout 30 \
    --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
    --mount "type=bind,src=$workspace,dst=/ws" \
    --mount "type=bind,src=$deployment_dir,dst=/deployment,readonly" \
    --mount type=bind,src=/dev,dst=/host-dev \
    --device-cgroup-rule='c 166:* rw' \
    -e "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}" \
    -e "TYRANT_SETUP=${TYRANT_SETUP:-/ws/install/setup.bash}" \
    -e "TYRANT_SERIAL_DEVICE=${TYRANT_SERIAL_DEVICE:-/host-dev/serial/by-id/usb-Teensyduino_USB_Serial_13843280-if00}" \
    -e PYTHONUNBUFFERED=1 \
    --entrypoint /bin/bash \
    "$image" /deployment/entrypoint.sh

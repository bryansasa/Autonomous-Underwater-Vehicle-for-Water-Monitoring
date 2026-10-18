# Build from the repository root on ARM64 Jetson:
# docker build --network host -f companion/jetson/Dockerfile -t tyrant-companion:humble .
FROM ros:humble-ros-base
SHELL ["/bin/bash", "-c"]
ARG DEBIAN_FRONTEND=noninteractive
# Supply commit SHAs for repeatable source versions after qualification.
ARG MICRO_ROS_AGENT_REF=humble
ARG MICRO_ROS_MSGS_REF=humble
ENV CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake python3-rosdep python3-colcon-common-extensions \
    python3-pytest ros-humble-joy ros-humble-rosbag2 \
    ros-humble-rosbag2-storage-default-plugins \
    && mkdir -p /opt/tyrant_ws/src
WORKDIR /opt/tyrant_ws
RUN git clone -b humble https://github.com/micro-ROS/micro-ROS-Agent.git src/micro-ROS-Agent \
    && git -C src/micro-ROS-Agent checkout "$MICRO_ROS_AGENT_REF" \
    && git clone -b humble https://github.com/micro-ROS/micro_ros_msgs.git src/micro_ros_msgs \
    && git -C src/micro_ros_msgs checkout "$MICRO_ROS_MSGS_REF"
COPY ros2_ws/src/tyrant_interfaces src/tyrant_interfaces
COPY ros2_ws/src/tyrant_payload_interfaces src/tyrant_payload_interfaces
COPY ros2_ws/src/tyrant_mission_host src/tyrant_mission_host
COPY ros2_ws/src/tyrant_teleop src/tyrant_teleop
COPY ros2_ws/src/tyrant_sim src/tyrant_sim
RUN source /opt/ros/humble/setup.bash \
    && (test -f /etc/ros/rosdep/sources.list.d/20-default.list || rosdep init) \
    && rosdep update --rosdistro humble \
    && rosdep install --from-paths src --ignore-src --rosdistro humble -y \
    && colcon build --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release
COPY companion/jetson /opt/tyrant-deployment
ENV TYRANT_SETUP=/opt/tyrant_ws/install/setup.bash PYTHONUNBUFFERED=1
WORKDIR /ws
ENTRYPOINT ["/bin/bash", "/opt/tyrant-deployment/entrypoint.sh"]

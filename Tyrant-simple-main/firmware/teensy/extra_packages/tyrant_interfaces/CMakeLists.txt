cmake_minimum_required(VERSION 3.8)
project(tyrant_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/SimpleState.msg"
  "msg/ImuTelemetry.msg"
  "msg/PressureTelemetry.msg"
  "msg/ModeRequest.msg"
  "msg/ModeStatus.msg"
  "msg/SystemHealth.msg"
  "msg/CommunicationDiagnostics.msg"
  "msg/DepthReferenceRequest.msg"
  "msg/DepthReferenceStatus.msg"
  "msg/ManualCommand.msg"
  "msg/WrenchRequest.msg"
  "msg/ThrusterCommand.msg"
  "msg/ActuatorStatus.msg"
  "msg/SysIdControl.msg"
  "msg/SysIdStatus.msg"
  "msg/SysIdSample.msg"
  "msg/MissionCommand.msg"
  "msg/MissionStatus.msg"
  "msg/EmergencyControl.msg"
  "msg/EmergencyStatus.msg"
)

ament_package()

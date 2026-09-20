cmake_minimum_required(VERSION 3.8)
project(tyrant_payload_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/PayloadWaterQuality.msg"
  "msg/PayloadPower.msg"
  "msg/PayloadHealth.msg"
  "msg/SensorPowerRequest.msg"
  "msg/SensorPowerStatus.msg"
  "msg/PayloadCommunicationDiagnostics.msg"
)

ament_package()

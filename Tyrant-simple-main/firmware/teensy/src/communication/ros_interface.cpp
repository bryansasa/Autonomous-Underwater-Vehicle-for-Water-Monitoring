#include "communication/ros_interface.h"

#include <micro_ros_platformio.h>

#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <rmw_microros/rmw_microros.h>

#include <std_msgs/msg/u_int32.h>

#include <tyrant_interfaces/msg/actuator_status.h>
#include <tyrant_interfaces/msg/communication_diagnostics.h>
#include <tyrant_interfaces/msg/depth_reference_request.h>
#include <tyrant_interfaces/msg/depth_reference_status.h>
#include <tyrant_interfaces/msg/imu_telemetry.h>
#include <tyrant_interfaces/msg/manual_command.h>
#include <tyrant_interfaces/msg/mission_command.h>
#include <tyrant_interfaces/msg/mission_status.h>
#include <tyrant_interfaces/msg/emergency_control.h>
#include <tyrant_interfaces/msg/emergency_status.h>
#include <tyrant_interfaces/msg/mode_request.h>
#include <tyrant_interfaces/msg/mode_status.h>
#include <tyrant_interfaces/msg/pressure_telemetry.h>
#include <tyrant_interfaces/msg/simple_state.h>
#include <tyrant_interfaces/msg/system_health.h>
#include <tyrant_interfaces/msg/sys_id_control.h>
#include <tyrant_interfaces/msg/sys_id_sample.h>
#include <tyrant_interfaces/msg/sys_id_status.h>
#include <tyrant_interfaces/msg/thruster_command.h>
#include <tyrant_interfaces/msg/wrench_request.h>

namespace
{
// ============================================================
// ROS CORE
// ============================================================

rcl_allocator_t allocator;
rclc_support_t support {};
rcl_node_t node = rcl_get_zero_initialized_node();
rclc_executor_t executor = rclc_executor_get_zero_initialized_executor();

bool support_initialized = false;
bool node_initialized = false;
bool executor_initialized = false;
bool entities_ready = false;


// ============================================================
// PUBLISHERS
// ============================================================

rcl_publisher_t heartbeat_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t mode_status_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t system_health_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t simple_state_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t imu_telemetry_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t pressure_telemetry_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t depth_reference_status_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t communication_diagnostics_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t wrench_request_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t thruster_command_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t actuator_status_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t sysid_status_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t sysid_sample_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t mission_status_pub = rcl_get_zero_initialized_publisher();
rcl_publisher_t emergency_status_pub = rcl_get_zero_initialized_publisher();

#ifdef TYRANT_ENABLE_DIAGNOSTICS
rcl_publisher_t response_pub = rcl_get_zero_initialized_publisher();
#endif

bool heartbeat_pub_initialized = false;
bool mode_status_pub_initialized = false;
bool system_health_pub_initialized = false;
bool simple_state_pub_initialized = false;
bool imu_telemetry_pub_initialized = false;
bool pressure_telemetry_pub_initialized = false;
bool depth_reference_status_pub_initialized = false;
bool communication_diagnostics_pub_initialized = false;
bool wrench_request_pub_initialized = false;
bool thruster_command_pub_initialized = false;
bool actuator_status_pub_initialized = false;
bool sysid_status_pub_initialized = false;
bool sysid_sample_pub_initialized = false;
bool mission_status_pub_initialized = false;
bool emergency_status_pub_initialized = false;
#ifdef TYRANT_ENABLE_DIAGNOSTICS
bool response_pub_initialized = false;
#endif


// ============================================================
// SUBSCRIBERS
// ============================================================

rcl_subscription_t mode_request_sub = rcl_get_zero_initialized_subscription();
rcl_subscription_t host_heartbeat_sub = rcl_get_zero_initialized_subscription();
rcl_subscription_t depth_reference_request_sub = rcl_get_zero_initialized_subscription();
rcl_subscription_t manual_command_sub = rcl_get_zero_initialized_subscription();
rcl_subscription_t sysid_control_sub = rcl_get_zero_initialized_subscription();
rcl_subscription_t mission_command_sub = rcl_get_zero_initialized_subscription();
rcl_subscription_t emergency_control_sub = rcl_get_zero_initialized_subscription();
#ifdef TYRANT_USE_SIM_STATE_INPUT
rcl_subscription_t sim_state_input_sub = rcl_get_zero_initialized_subscription();
#endif
#ifdef TYRANT_ENABLE_DIAGNOSTICS
rcl_subscription_t command_sub = rcl_get_zero_initialized_subscription();
#endif

bool mode_request_sub_initialized = false;
bool host_heartbeat_sub_initialized = false;
bool depth_reference_request_sub_initialized = false;
bool manual_command_sub_initialized = false;
bool sysid_control_sub_initialized = false;
bool mission_command_sub_initialized = false;
bool emergency_control_sub_initialized = false;
#ifdef TYRANT_USE_SIM_STATE_INPUT
bool sim_state_input_sub_initialized = false;
#endif
#ifdef TYRANT_ENABLE_DIAGNOSTICS
bool command_sub_initialized = false;
#endif


// ============================================================
// MESSAGE STORAGE
// ============================================================

std_msgs__msg__UInt32 heartbeat_msg {};
std_msgs__msg__UInt32 host_heartbeat_msg {};

tyrant_interfaces__msg__ModeRequest mode_request_msg {};
tyrant_interfaces__msg__ModeStatus mode_status_msg {};
tyrant_interfaces__msg__SystemHealth system_health_msg {};
tyrant_interfaces__msg__SimpleState simple_state_msg {};
tyrant_interfaces__msg__ImuTelemetry imu_telemetry_msg {};
tyrant_interfaces__msg__PressureTelemetry pressure_telemetry_msg {};
tyrant_interfaces__msg__DepthReferenceRequest depth_reference_request_msg {};
tyrant_interfaces__msg__DepthReferenceStatus depth_reference_status_msg {};
tyrant_interfaces__msg__CommunicationDiagnostics communication_diagnostics_msg {};
tyrant_interfaces__msg__ManualCommand manual_command_msg {};
tyrant_interfaces__msg__WrenchRequest wrench_request_msg {};
tyrant_interfaces__msg__ThrusterCommand thruster_command_msg {};
tyrant_interfaces__msg__ActuatorStatus actuator_status_msg {};
tyrant_interfaces__msg__SysIdControl sysid_control_msg {};
tyrant_interfaces__msg__SysIdStatus sysid_status_msg {};
tyrant_interfaces__msg__SysIdSample sysid_sample_msg {};
tyrant_interfaces__msg__MissionCommand mission_command_msg {};
tyrant_interfaces__msg__MissionStatus mission_status_msg {};
tyrant_interfaces__msg__EmergencyControl emergency_control_msg {};
tyrant_interfaces__msg__EmergencyStatus emergency_status_msg {};
#ifdef TYRANT_USE_SIM_STATE_INPUT
tyrant_interfaces__msg__SimpleState sim_state_input_msg {};
#endif

#ifdef TYRANT_ENABLE_DIAGNOSTICS
std_msgs__msg__UInt32 command_msg {};
std_msgs__msg__UInt32 response_msg {};
#endif


// ============================================================
// APPLICATION FLAGS
// ============================================================

bool new_mode_request = false;
uint32_t requested_mode_id = 0;
uint8_t requested_mode = 0;

bool new_host_heartbeat = false;

bool new_depth_reference_request = false;
uint32_t depth_reference_request_id = 0;
uint8_t depth_reference_command = 0;

bool new_manual_command = false;
TyrantROS::ManualCommandData received_manual_command {};

bool new_sysid_control = false;
TyrantROS::SysIdControlData received_sysid_control {};

bool new_mission_command = false;
TyrantROS::MissionCommandData received_mission_command {};

bool new_emergency_control = false;
TyrantROS::EmergencyControlData received_emergency_control {};

#ifdef TYRANT_USE_SIM_STATE_INPUT
bool new_sim_state_input = false;
TyrantSimpleEstimator::State received_sim_state {};
#endif

#ifdef TYRANT_ENABLE_DIAGNOSTICS
bool new_command = false;
uint32_t last_command = 0;
#endif


// ============================================================
// ERROR COUNTERS
// ============================================================

uint32_t publish_failures = 0;
uint32_t executor_failures = 0;
uint32_t entity_create_failures = 0;
uint32_t entity_destroy_failures = 0;

bool recordCreateResult(rcl_ret_t result)
{
    if (result == RCL_RET_OK)
    {
        return true;
    }

    ++entity_create_failures;
    return false;
}

void recordDestroyResult(rcl_ret_t result)
{
    if (result != RCL_RET_OK)
    {
        ++entity_destroy_failures;
    }
}

void recordPublishResult(rcl_ret_t result)
{
    if (result != RCL_RET_OK)
    {
        ++publish_failures;
    }
}


// ============================================================
// CALLBACKS
// ============================================================

void modeRequestCallback(const void *msgin)
{
    const auto *received =
        static_cast<const tyrant_interfaces__msg__ModeRequest *>(msgin);

    requested_mode_id = received->request_id;
    requested_mode = received->requested_mode;
    new_mode_request = true;
}

void hostHeartbeatCallback(const void *msgin)
{
    (void)msgin;
    new_host_heartbeat = true;
}

void depthReferenceRequestCallback(const void *msgin)
{
    const auto *received =
        static_cast<const tyrant_interfaces__msg__DepthReferenceRequest *>(msgin);

    depth_reference_request_id = received->request_id;
    depth_reference_command = received->command;
    new_depth_reference_request = true;
}

void manualCommandCallback(const void *msgin)
{
    const auto *received =
        static_cast<const tyrant_interfaces__msg__ManualCommand *>(msgin);

    received_manual_command.sequence = received->sequence;
    received_manual_command.surge = received->surge;
    received_manual_command.sway = received->sway;
    received_manual_command.heave = received->heave;
    received_manual_command.roll = received->roll;
    received_manual_command.pitch = received->pitch;
    received_manual_command.yaw = received->yaw;

    new_manual_command = true;
}

void sysIdControlCallback(const void *msgin)
{
    const auto *received =
        static_cast<const tyrant_interfaces__msg__SysIdControl *>(msgin);

    received_sysid_control.request_id = received->request_id;
    received_sysid_control.command = received->command;
    received_sysid_control.experiment_id = received->experiment_id;
    received_sysid_control.profile_id = received->profile_id;
    new_sysid_control = true;
}

void missionCommandCallback(const void *msgin)
{
    const auto *received =
        static_cast<const tyrant_interfaces__msg__MissionCommand *>(msgin);

    received_mission_command.request_id = received->request_id;
    received_mission_command.command = received->command;
    received_mission_command.step_type = received->step_type;
    received_mission_command.target = received->target;
    received_mission_command.effort = received->effort;
    received_mission_command.duration_ms = received->duration_ms;
    received_mission_command.tolerance = received->tolerance;
    new_mission_command = true;
}

void emergencyControlCallback(const void *msgin)
{
    const auto *received =
        static_cast<const tyrant_interfaces__msg__EmergencyControl *>(msgin);

    received_emergency_control.request_id = received->request_id;
    received_emergency_control.command = received->command;
    new_emergency_control = true;
}

#ifdef TYRANT_USE_SIM_STATE_INPUT
void simStateInputCallback(const void *msgin)
{
    const auto *received =
        static_cast<const tyrant_interfaces__msg__SimpleState *>(msgin);

    received_sim_state.roll_rad = received->roll;
    received_sim_state.pitch_rad = received->pitch;
    received_sim_state.yaw_rad = received->yaw;
    received_sim_state.angular_velocity_b_rad_s = {
        received->angular_velocity_x,
        received->angular_velocity_y,
        received->angular_velocity_z
    };
    received_sim_state.yaw_rate_bias_rad_s = received->yaw_rate_bias;
    received_sim_state.depth_m = received->depth;
    received_sim_state.attitude_valid = received->attitude_valid;
    received_sim_state.heading_valid = received->heading_valid;
    received_sim_state.depth_valid = received->depth_valid;
    received_sim_state.status =
        static_cast<TyrantSimpleEstimator::Status>(received->status);

    new_sim_state_input = true;
}
#endif

#ifdef TYRANT_ENABLE_DIAGNOSTICS
void commandCallback(const void *msgin)
{
    const auto *received = static_cast<const std_msgs__msg__UInt32 *>(msgin);
    last_command = received->data;
    new_command = true;
}
#endif


// ============================================================
// CREATION HELPERS
// ============================================================

bool createPublisher(
    rcl_publisher_t &publisher,
    const rosidl_message_type_support_t *type_support,
    const char *topic,
    bool &initialized)
{
    if (!recordCreateResult(
            rclc_publisher_init_default(
                &publisher,
                &node,
                type_support,
                topic)))
    {
        return false;
    }

    initialized = true;
    return true;
}

bool createSubscription(
    rcl_subscription_t &subscription,
    const rosidl_message_type_support_t *type_support,
    const char *topic,
    bool &initialized)
{
    if (!recordCreateResult(
            rclc_subscription_init_default(
                &subscription,
                &node,
                type_support,
                topic)))
    {
        return false;
    }

    initialized = true;
    return true;
}

void resetApplicationFlags()
{
    new_mode_request = false;
    requested_mode_id = 0;
    requested_mode = 0;
    new_host_heartbeat = false;
    new_depth_reference_request = false;
    depth_reference_request_id = 0;
    depth_reference_command = 0;
    new_manual_command = false;
    received_manual_command = TyrantROS::ManualCommandData {};
    new_sysid_control = false;
    received_sysid_control = TyrantROS::SysIdControlData {};
    new_mission_command = false;
    received_mission_command = TyrantROS::MissionCommandData {};
    new_emergency_control = false;
    received_emergency_control = TyrantROS::EmergencyControlData {};
#ifdef TYRANT_USE_SIM_STATE_INPUT
    new_sim_state_input = false;
    received_sim_state = TyrantSimpleEstimator::State {};
#endif
#ifdef TYRANT_ENABLE_DIAGNOSTICS
    new_command = false;
    last_command = 0;
#endif
}

} // namespace

namespace TyrantROS
{

void setupTransport()
{
    Serial.begin(115200);
    delay(2000);
    set_microros_serial_transports(Serial);
}

bool pingAgent(uint32_t timeout_ms, uint8_t attempts)
{
    return rmw_uros_ping_agent(timeout_ms, attempts) == RMW_RET_OK;
}

bool createEntities()
{
    if (entities_ready)
    {
        return true;
    }

    allocator = rcl_get_default_allocator();

    if (!recordCreateResult(
            rclc_support_init(&support, 0, nullptr, &allocator)))
    {
        destroyEntities();
        return false;
    }
    support_initialized = true;

    if (!recordCreateResult(
            rclc_node_init_default(
                &node,
                "tyrant_teensy",
                "",
                &support)))
    {
        destroyEntities();
        return false;
    }
    node_initialized = true;

    if (!createPublisher(
            heartbeat_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32),
            "/tyrant/heartbeat",
            heartbeat_pub_initialized) ||
        !createPublisher(
            mode_status_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, ModeStatus),
            "/tyrant/mode/status",
            mode_status_pub_initialized) ||
        !createPublisher(
            system_health_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, SystemHealth),
            "/tyrant/system/health",
            system_health_pub_initialized) ||
        !createPublisher(
            simple_state_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, SimpleState),
            "/tyrant/simple_state",
            simple_state_pub_initialized) ||
        !createPublisher(
            imu_telemetry_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, ImuTelemetry),
            "/tyrant/sensors/imu",
            imu_telemetry_pub_initialized) ||
        !createPublisher(
            pressure_telemetry_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, PressureTelemetry),
            "/tyrant/sensors/pressure",
            pressure_telemetry_pub_initialized) ||
        !createPublisher(
            depth_reference_status_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, DepthReferenceStatus),
            "/tyrant/depth/reference/status",
            depth_reference_status_pub_initialized) ||
        !createPublisher(
            communication_diagnostics_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, CommunicationDiagnostics),
            "/tyrant/communication/diagnostics",
            communication_diagnostics_pub_initialized) ||
        !createPublisher(
            wrench_request_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, WrenchRequest),
            "/tyrant/control/wrench_request",
            wrench_request_pub_initialized) ||
        !createPublisher(
            thruster_command_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, ThrusterCommand),
            "/tyrant/control/thruster_command",
            thruster_command_pub_initialized) ||
        !createPublisher(
            actuator_status_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, ActuatorStatus),
            "/tyrant/actuation/status",
            actuator_status_pub_initialized) ||
        !createPublisher(
            sysid_status_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, SysIdStatus),
            "/tyrant/sysid/status",
            sysid_status_pub_initialized) ||
        !createPublisher(
            sysid_sample_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, SysIdSample),
            "/tyrant/sysid/sample",
            sysid_sample_pub_initialized) ||
        !createPublisher(
            mission_status_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, MissionStatus),
            "/tyrant/mission/status",
            mission_status_pub_initialized) ||
        !createPublisher(
            emergency_status_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, EmergencyStatus),
            "/tyrant/emergency/status",
            emergency_status_pub_initialized))
    {
        destroyEntities();
        return false;
    }

#ifdef TYRANT_ENABLE_DIAGNOSTICS
    if (!createPublisher(
            response_pub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32),
            "/tyrant/test_response",
            response_pub_initialized))
    {
        destroyEntities();
        return false;
    }
#endif

    if (!createSubscription(
            mode_request_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, ModeRequest),
            "/tyrant/mode/request",
            mode_request_sub_initialized) ||
        !createSubscription(
            host_heartbeat_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32),
            "/tyrant/host_heartbeat",
            host_heartbeat_sub_initialized) ||
        !createSubscription(
            depth_reference_request_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, DepthReferenceRequest),
            "/tyrant/depth/reference/request",
            depth_reference_request_sub_initialized) ||
        !createSubscription(
            manual_command_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, ManualCommand),
            "/tyrant/manual/command",
            manual_command_sub_initialized) ||
        !createSubscription(
            sysid_control_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, SysIdControl),
            "/tyrant/sysid/control",
            sysid_control_sub_initialized) ||
        !createSubscription(
            mission_command_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, MissionCommand),
            "/tyrant/mission/command",
            mission_command_sub_initialized) ||
        !createSubscription(
            emergency_control_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, EmergencyControl),
            "/tyrant/emergency/control",
            emergency_control_sub_initialized))
    {
        destroyEntities();
        return false;
    }

#ifdef TYRANT_USE_SIM_STATE_INPUT
    if (!createSubscription(
            sim_state_input_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_interfaces, msg, SimpleState),
            "/tyrant/sim/state_input",
            sim_state_input_sub_initialized))
    {
        destroyEntities();
        return false;
    }
#endif

#ifdef TYRANT_ENABLE_DIAGNOSTICS
    if (!createSubscription(
            command_sub,
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32),
            "/tyrant/test_command",
            command_sub_initialized))
    {
        destroyEntities();
        return false;
    }
#endif

constexpr size_t BASE_EXECUTOR_HANDLE_COUNT = 7;
#ifdef TYRANT_ENABLE_DIAGNOSTICS
constexpr size_t DIAGNOSTIC_EXECUTOR_HANDLE_COUNT = 1;
#else
constexpr size_t DIAGNOSTIC_EXECUTOR_HANDLE_COUNT = 0;
#endif
#ifdef TYRANT_USE_SIM_STATE_INPUT
constexpr size_t SIM_EXECUTOR_HANDLE_COUNT = 1;
#else
constexpr size_t SIM_EXECUTOR_HANDLE_COUNT = 0;
#endif
    constexpr size_t EXECUTOR_HANDLE_COUNT =
        BASE_EXECUTOR_HANDLE_COUNT +
        DIAGNOSTIC_EXECUTOR_HANDLE_COUNT +
        SIM_EXECUTOR_HANDLE_COUNT;

    if (!recordCreateResult(
            rclc_executor_init(
                &executor,
                &support.context,
                EXECUTOR_HANDLE_COUNT,
                &allocator)))
    {
        destroyEntities();
        return false;
    }
    executor_initialized = true;

    if (!recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &mode_request_sub,
                &mode_request_msg,
                &modeRequestCallback,
                ON_NEW_DATA)) ||
        !recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &host_heartbeat_sub,
                &host_heartbeat_msg,
                &hostHeartbeatCallback,
                ON_NEW_DATA)) ||
        !recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &depth_reference_request_sub,
                &depth_reference_request_msg,
                &depthReferenceRequestCallback,
                ON_NEW_DATA)) ||
        !recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &manual_command_sub,
                &manual_command_msg,
                &manualCommandCallback,
                ON_NEW_DATA)) ||
        !recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &sysid_control_sub,
                &sysid_control_msg,
                &sysIdControlCallback,
                ON_NEW_DATA)) ||
        !recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &mission_command_sub,
                &mission_command_msg,
                &missionCommandCallback,
                ON_NEW_DATA)) ||
        !recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &emergency_control_sub,
                &emergency_control_msg,
                &emergencyControlCallback,
                ON_NEW_DATA)))
    {
        destroyEntities();
        return false;
    }

#ifdef TYRANT_USE_SIM_STATE_INPUT
    if (!recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &sim_state_input_sub,
                &sim_state_input_msg,
                &simStateInputCallback,
                ON_NEW_DATA)))
    {
        destroyEntities();
        return false;
    }
#endif

#ifdef TYRANT_ENABLE_DIAGNOSTICS
    if (!recordCreateResult(
            rclc_executor_add_subscription(
                &executor,
                &command_sub,
                &command_msg,
                &commandCallback,
                ON_NEW_DATA)))
    {
        destroyEntities();
        return false;
    }
#endif

    resetApplicationFlags();
    entities_ready = true;
    return true;
}

void destroyEntities()
{
    entities_ready = false;
    resetApplicationFlags();
    if (support_initialized)
    {
        rmw_context_t *rmw_context =
            rcl_context_get_rmw_context(
                &support.context
            );

        if (rmw_context != nullptr)
        {
            (void)
                rmw_uros_set_context_entity_destroy_session_timeout(
                    rmw_context,
                    0
                );
        }
    }

    if (executor_initialized)
    {
        recordDestroyResult(rclc_executor_fini(&executor));
        executor = rclc_executor_get_zero_initialized_executor();
        executor_initialized = false;
    }

#ifdef TYRANT_ENABLE_DIAGNOSTICS
    if (command_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&command_sub, &node));
        command_sub_initialized = false;
    }
#endif
#ifdef TYRANT_USE_SIM_STATE_INPUT
    if (sim_state_input_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&sim_state_input_sub, &node));
        sim_state_input_sub_initialized = false;
    }
#endif
    if (emergency_control_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&emergency_control_sub, &node));
        emergency_control_sub_initialized = false;
    }
    if (mission_command_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&mission_command_sub, &node));
        mission_command_sub_initialized = false;
    }
    if (sysid_control_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&sysid_control_sub, &node));
        sysid_control_sub_initialized = false;
    }
    if (manual_command_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&manual_command_sub, &node));
        manual_command_sub_initialized = false;
    }
    if (depth_reference_request_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&depth_reference_request_sub, &node));
        depth_reference_request_sub_initialized = false;
    }
    if (host_heartbeat_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&host_heartbeat_sub, &node));
        host_heartbeat_sub_initialized = false;
    }
    if (mode_request_sub_initialized)
    {
        recordDestroyResult(rcl_subscription_fini(&mode_request_sub, &node));
        mode_request_sub_initialized = false;
    }

#ifdef TYRANT_ENABLE_DIAGNOSTICS
    if (response_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&response_pub, &node));
        response_pub_initialized = false;
    }
#endif
    if (emergency_status_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&emergency_status_pub, &node));
        emergency_status_pub_initialized = false;
    }
    if (mission_status_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&mission_status_pub, &node));
        mission_status_pub_initialized = false;
    }
    if (sysid_sample_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&sysid_sample_pub, &node));
        sysid_sample_pub_initialized = false;
    }
    if (sysid_status_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&sysid_status_pub, &node));
        sysid_status_pub_initialized = false;
    }
    if (actuator_status_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&actuator_status_pub, &node));
        actuator_status_pub_initialized = false;
    }
    if (thruster_command_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&thruster_command_pub, &node));
        thruster_command_pub_initialized = false;
    }
    if (wrench_request_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&wrench_request_pub, &node));
        wrench_request_pub_initialized = false;
    }
    if (communication_diagnostics_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&communication_diagnostics_pub, &node));
        communication_diagnostics_pub_initialized = false;
    }
    if (depth_reference_status_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&depth_reference_status_pub, &node));
        depth_reference_status_pub_initialized = false;
    }
    if (pressure_telemetry_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&pressure_telemetry_pub, &node));
        pressure_telemetry_pub_initialized = false;
    }
    if (imu_telemetry_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&imu_telemetry_pub, &node));
        imu_telemetry_pub_initialized = false;
    }
    if (simple_state_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&simple_state_pub, &node));
        simple_state_pub_initialized = false;
    }
    if (system_health_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&system_health_pub, &node));
        system_health_pub_initialized = false;
    }
    if (mode_status_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&mode_status_pub, &node));
        mode_status_pub_initialized = false;
    }
    if (heartbeat_pub_initialized)
    {
        recordDestroyResult(rcl_publisher_fini(&heartbeat_pub, &node));
        heartbeat_pub_initialized = false;
    }

    if (node_initialized)
    {
        recordDestroyResult(rcl_node_fini(&node));
        node = rcl_get_zero_initialized_node();
        node_initialized = false;
    }

    if (support_initialized)
    {
        recordDestroyResult(rclc_support_fini(&support));
        support = {};
        support_initialized = false;
    }
}

void spin()
{
    if (!entities_ready || !executor_initialized)
    {
        return;
    }

    const rcl_ret_t result =
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));

    if (result != RCL_RET_OK && result != RCL_RET_TIMEOUT)
    {
        ++executor_failures;
    }
}

void publishHeartbeat()
{
    if (!entities_ready)
    {
        return;
    }

    ++heartbeat_msg.data;
    recordPublishResult(rcl_publish(&heartbeat_pub, &heartbeat_msg, nullptr));
}

void publishWrenchRequest(
    const TyrantControl::WrenchRequest &request)
{
    if (!entities_ready)
    {
        return;
    }

    wrench_request_msg.source_sequence = request.source_sequence;
    wrench_request_msg.x = request.x;
    wrench_request_msg.y = request.y;
    wrench_request_msg.z = request.z;
    wrench_request_msg.k = request.k;
    wrench_request_msg.m = request.m;
    wrench_request_msg.n = request.n;
    wrench_request_msg.command_fresh = request.command_fresh;
    wrench_request_msg.enabled = request.enabled;

    recordPublishResult(
        rcl_publish(
            &wrench_request_pub,
            &wrench_request_msg,
            nullptr));
}

void publishThrusterCommand(
    const TyrantControl::ThrusterCommand &command,
    bool allocator_ready,
    bool mock_backend,
    uint64_t timestamp_us)
{
    if (!entities_ready)
    {
        return;
    }

    thruster_command_msg.timestamp_us = timestamp_us;
    thruster_command_msg.source_sequence = command.source_sequence;
    thruster_command_msg.allocation_status =
        static_cast<uint8_t>(command.status);
    thruster_command_msg.allocator_ready = allocator_ready;
    thruster_command_msg.valid = command.valid;
    thruster_command_msg.enabled = command.enabled;
    thruster_command_msg.saturated = command.saturated;
    thruster_command_msg.mock_backend = mock_backend;
    thruster_command_msg.residual_norm = command.residual_norm;

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        thruster_command_msg.command[index] = command.value[index];
    }

    recordPublishResult(
        rcl_publish(
            &thruster_command_pub,
            &thruster_command_msg,
            nullptr));
}

void publishActuatorStatus(
    const TyrantActuation::ThrusterBackendStatus &status,
    uint64_t timestamp_us)
{
    if (!entities_ready)
    {
        return;
    }

    actuator_status_msg.timestamp_us = timestamp_us;
    actuator_status_msg.backend_type =
        static_cast<uint8_t>(status.type);
    actuator_status_msg.fault_code =
        static_cast<uint8_t>(status.fault);
    actuator_status_msg.configured = status.configured;
    actuator_status_msg.ready = status.ready;
    actuator_status_msg.physical_output_enabled =
        status.physical_output_enabled;
    actuator_status_msg.fault_latched = status.fault_latched;
    actuator_status_msg.apply_count = status.apply_count;
    actuator_status_msg.reject_count = status.reject_count;
    actuator_status_msg.neutralize_count = status.neutralize_count;
    actuator_status_msg.command_age_us = status.command_age_us;

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        actuator_status_msg.pulse_us[index] = status.pulse_us[index];
    }

    recordPublishResult(
        rcl_publish(
            &actuator_status_pub,
            &actuator_status_msg,
            nullptr));
}

void publishMissionStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    const TyrantMission::Status &status)
{
    if (!entities_ready)
    {
        return;
    }

    mission_status_msg.request_id = request_id;
    mission_status_msg.command = command;
    mission_status_msg.accepted = accepted;
    mission_status_msg.state = static_cast<uint8_t>(status.state);
    mission_status_msg.reason = static_cast<uint8_t>(status.reason);
    mission_status_msg.step_count = status.step_count;
    mission_status_msg.current_step = status.current_step;
    mission_status_msg.current_step_type = static_cast<uint8_t>(status.current_step_type);
    mission_status_msg.active = status.active;

    recordPublishResult(
        rcl_publish(&mission_status_pub, &mission_status_msg, nullptr));
}

void publishEmergencyStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    const TyrantEmergency::Status &status)
{
    if (!entities_ready)
    {
        return;
    }

    emergency_status_msg.request_id = request_id;
    emergency_status_msg.command = command;
    emergency_status_msg.accepted = accepted;
    emergency_status_msg.policy = static_cast<uint8_t>(status.policy);
    emergency_status_msg.state = static_cast<uint8_t>(status.state);
    emergency_status_msg.reason = static_cast<uint8_t>(status.reason);
    emergency_status_msg.elapsed_ms = status.elapsed_ms;
    emergency_status_msg.actuation_requested = status.actuation_requested;

    recordPublishResult(
        rcl_publish(&emergency_status_pub, &emergency_status_msg, nullptr));
}

void publishSysIdStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    const TyrantSysId::SessionStatus &status)
{
    if (!entities_ready)
    {
        return;
    }

    sysid_status_msg.request_id = request_id;
    sysid_status_msg.command = command;
    sysid_status_msg.accepted = accepted;
    sysid_status_msg.active = status.active;
    sysid_status_msg.experiment_id = status.experiment_id;
    sysid_status_msg.profile_id = status.profile_id;
    sysid_status_msg.sample_sequence = status.sample_sequence;

    recordPublishResult(
        rcl_publish(&sysid_status_pub, &sysid_status_msg, nullptr));
}

void publishSysIdSample(
    const TyrantSysId::Sample &sample)
{
    if (!entities_ready)
    {
        return;
    }

    sysid_sample_msg.timestamp_us = sample.timestamp_us;
    sysid_sample_msg.experiment_id = sample.experiment_id;
    sysid_sample_msg.profile_id = sample.profile_id;
    sysid_sample_msg.sample_sequence = sample.sample_sequence;
    sysid_sample_msg.mode = sample.mode;
    sysid_sample_msg.propulsion_allowed = sample.propulsion_allowed;
    sysid_sample_msg.command_fresh = sample.command_fresh;

    sysid_sample_msg.manual_sequence = sample.manual_command.sequence;
    sysid_sample_msg.manual_surge = sample.manual_command.surge;
    sysid_sample_msg.manual_sway = sample.manual_command.sway;
    sysid_sample_msg.manual_heave = sample.manual_command.heave;
    sysid_sample_msg.manual_roll = sample.manual_command.roll;
    sysid_sample_msg.manual_pitch = sample.manual_command.pitch;
    sysid_sample_msg.manual_yaw = sample.manual_command.yaw;

    sysid_sample_msg.wrench_source_sequence = sample.requested_wrench.source_sequence;
    sysid_sample_msg.wrench_x = sample.requested_wrench.x;
    sysid_sample_msg.wrench_y = sample.requested_wrench.y;
    sysid_sample_msg.wrench_z = sample.requested_wrench.z;
    sysid_sample_msg.wrench_k = sample.requested_wrench.k;
    sysid_sample_msg.wrench_m = sample.requested_wrench.m;
    sysid_sample_msg.wrench_n = sample.requested_wrench.n;
    sysid_sample_msg.wrench_enabled = sample.requested_wrench.enabled;

    sysid_sample_msg.thruster_command_valid = sample.thruster_command_valid;
    for (uint8_t index = 0; index < TyrantSysId::SYSID_THRUSTER_COUNT; ++index)
    {
        sysid_sample_msg.thruster_command[index] = sample.thruster_command[index];
    }

    sysid_sample_msg.estimator_status = static_cast<uint8_t>(sample.state.status);
    sysid_sample_msg.roll = sample.state.roll_rad;
    sysid_sample_msg.pitch = sample.state.pitch_rad;
    sysid_sample_msg.yaw = sample.state.yaw_rad;
    sysid_sample_msg.angular_velocity_x = sample.state.angular_velocity_b_rad_s.x;
    sysid_sample_msg.angular_velocity_y = sample.state.angular_velocity_b_rad_s.y;
    sysid_sample_msg.angular_velocity_z = sample.state.angular_velocity_b_rad_s.z;
    sysid_sample_msg.yaw_rate_bias = sample.state.yaw_rate_bias_rad_s;
    sysid_sample_msg.depth = sample.state.depth_m;
    sysid_sample_msg.attitude_valid = sample.state.attitude_valid;
    sysid_sample_msg.heading_valid = sample.state.heading_valid;
    sysid_sample_msg.depth_valid = sample.state.depth_valid;

    sysid_sample_msg.imu_valid = sample.imu_valid;
    sysid_sample_msg.accel_x = sample.imu.accel_x;
    sysid_sample_msg.accel_y = sample.imu.accel_y;
    sysid_sample_msg.accel_z = sample.imu.accel_z;
    sysid_sample_msg.gyro_x = sample.imu.gyro_x;
    sysid_sample_msg.gyro_y = sample.imu.gyro_y;
    sysid_sample_msg.gyro_z = sample.imu.gyro_z;

    sysid_sample_msg.pressure_valid = sample.pressure_valid;
    sysid_sample_msg.pressure_pa = sample.pressure.pressure_pa;
    sysid_sample_msg.temperature_c = sample.pressure.temperature_c;

    recordPublishResult(
        rcl_publish(&sysid_sample_pub, &sysid_sample_msg, nullptr));
}

void publishModeStatus(
    uint32_t request_id,
    uint8_t current_mode,
    uint8_t requested_mode_value,
    bool request_accepted,
    uint8_t reason,
    bool communication_healthy,
    bool propulsion_allowed)
{
    if (!entities_ready)
    {
        return;
    }

    mode_status_msg.request_id = request_id;
    mode_status_msg.current_mode = current_mode;
    mode_status_msg.requested_mode = requested_mode_value;
    mode_status_msg.request_accepted = request_accepted;
    mode_status_msg.reason = reason;
    mode_status_msg.communication_healthy = communication_healthy;
    mode_status_msg.propulsion_allowed = propulsion_allowed;

    recordPublishResult(rcl_publish(&mode_status_pub, &mode_status_msg, nullptr));
}

void publishSystemHealth(
    bool communication_healthy,
    bool estimator_ready,
    bool autonomy_ready,
    bool propulsion_allowed,
    uint8_t current_mode,
    uint32_t host_heartbeat_age_ms)
{
    if (!entities_ready)
    {
        return;
    }

    system_health_msg.communication_healthy = communication_healthy;
    system_health_msg.estimator_ready = estimator_ready;
    system_health_msg.autonomy_ready = autonomy_ready;
    system_health_msg.propulsion_allowed = propulsion_allowed;
    system_health_msg.current_mode = current_mode;
    system_health_msg.host_heartbeat_age_ms = host_heartbeat_age_ms;

    recordPublishResult(rcl_publish(&system_health_pub, &system_health_msg, nullptr));
}

void publishSimpleState(
    const TyrantSimpleEstimator::State &state,
    uint64_t timestamp_us)
{
    if (!entities_ready)
    {
        return;
    }

    simple_state_msg.timestamp_us = timestamp_us;
    simple_state_msg.status = static_cast<uint8_t>(state.status);
    simple_state_msg.roll = state.roll_rad;
    simple_state_msg.pitch = state.pitch_rad;
    simple_state_msg.yaw = state.yaw_rad;
    simple_state_msg.angular_velocity_x = state.angular_velocity_b_rad_s.x;
    simple_state_msg.angular_velocity_y = state.angular_velocity_b_rad_s.y;
    simple_state_msg.angular_velocity_z = state.angular_velocity_b_rad_s.z;
    simple_state_msg.yaw_rate_bias = state.yaw_rate_bias_rad_s;
    simple_state_msg.depth = state.depth_m;
    simple_state_msg.attitude_valid = state.attitude_valid;
    simple_state_msg.heading_valid = state.heading_valid;
    simple_state_msg.depth_valid = state.depth_valid;

    recordPublishResult(rcl_publish(&simple_state_pub, &simple_state_msg, nullptr));
}

void publishImuTelemetry(
    const TyrantSensors::ImuSample &sample,
    const TyrantSensors::SensorHealth &health,
    uint32_t bytes_received,
    uint32_t register_updates,
    uint32_t samples_produced,
    uint32_t samples_dropped,
    bool available)
{
    if (!entities_ready)
    {
        return;
    }

    imu_telemetry_msg.sensor_state = static_cast<uint8_t>(health.state);
    imu_telemetry_msg.sequence = sample.sequence;
    imu_telemetry_msg.timestamp_us = sample.timestamp_us;
    imu_telemetry_msg.accel_x = sample.accel_x;
    imu_telemetry_msg.accel_y = sample.accel_y;
    imu_telemetry_msg.accel_z = sample.accel_z;
    imu_telemetry_msg.gyro_x = sample.gyro_x;
    imu_telemetry_msg.gyro_y = sample.gyro_y;
    imu_telemetry_msg.gyro_z = sample.gyro_z;
    imu_telemetry_msg.mag_x_lsb = sample.mag_x_lsb;
    imu_telemetry_msg.mag_y_lsb = sample.mag_y_lsb;
    imu_telemetry_msg.mag_z_lsb = sample.mag_z_lsb;
    imu_telemetry_msg.mag_sequence = sample.mag_sequence;
    imu_telemetry_msg.valid = available && sample.valid;
    imu_telemetry_msg.mag_valid = available && sample.mag_valid;
    imu_telemetry_msg.mag_updated = available && sample.mag_updated;
    imu_telemetry_msg.bytes_received = bytes_received;
    imu_telemetry_msg.register_updates = register_updates;
    imu_telemetry_msg.samples_produced = samples_produced;
    imu_telemetry_msg.samples_dropped = samples_dropped;
    imu_telemetry_msg.error_count = health.error_count;

    recordPublishResult(rcl_publish(&imu_telemetry_pub, &imu_telemetry_msg, nullptr));
}

void publishPressureTelemetry(
    const TyrantSensors::PressureSample &sample,
    const TyrantSensors::SensorHealth &health,
    uint32_t read_attempts,
    uint32_t read_successes,
    uint32_t samples_produced,
    bool available)
{
    if (!entities_ready)
    {
        return;
    }

    pressure_telemetry_msg.sensor_state = static_cast<uint8_t>(health.state);
    pressure_telemetry_msg.sequence = sample.sequence;
    pressure_telemetry_msg.timestamp_us = sample.timestamp_us;
    pressure_telemetry_msg.pressure_pa = sample.pressure_pa;
    pressure_telemetry_msg.temperature_c = sample.temperature_c;
    pressure_telemetry_msg.valid = available && sample.valid;
    pressure_telemetry_msg.read_attempts = read_attempts;
    pressure_telemetry_msg.read_successes = read_successes;
    pressure_telemetry_msg.samples_produced = samples_produced;
    pressure_telemetry_msg.error_count = health.error_count;

    recordPublishResult(rcl_publish(&pressure_telemetry_pub, &pressure_telemetry_msg, nullptr));
}

void publishDepthReferenceStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    uint8_t reason,
    bool reference_valid,
    float surface_pressure_pa)
{
    if (!entities_ready)
    {
        return;
    }

    depth_reference_status_msg.request_id = request_id;
    depth_reference_status_msg.command = command;
    depth_reference_status_msg.accepted = accepted;
    depth_reference_status_msg.reason = reason;
    depth_reference_status_msg.reference_valid = reference_valid;
    depth_reference_status_msg.surface_pressure_pa = surface_pressure_pa;

    recordPublishResult(
        rcl_publish(&depth_reference_status_pub, &depth_reference_status_msg, nullptr));
}

void publishCommunicationDiagnostics(
    uint8_t connection_state,
    uint32_t connection_count,
    uint32_t disconnect_count,
    uint32_t reconnect_count,
    uint32_t publish_failure_count,
    uint32_t executor_failure_count,
    uint32_t entity_create_failure_count,
    uint32_t entity_destroy_failure_count)
{
    if (!entities_ready)
    {
        return;
    }

    communication_diagnostics_msg.connection_state = connection_state;
    communication_diagnostics_msg.connection_count = connection_count;
    communication_diagnostics_msg.disconnect_count = disconnect_count;
    communication_diagnostics_msg.reconnect_count = reconnect_count;
    communication_diagnostics_msg.publish_failures = publish_failure_count;
    communication_diagnostics_msg.executor_failures = executor_failure_count;
    communication_diagnostics_msg.entity_create_failures = entity_create_failure_count;
    communication_diagnostics_msg.entity_destroy_failures = entity_destroy_failure_count;

    recordPublishResult(
        rcl_publish(
            &communication_diagnostics_pub,
            &communication_diagnostics_msg,
            nullptr));
}

bool takeModeRequest(ModeRequestData &request)
{
    if (!new_mode_request)
    {
        return false;
    }

    request.request_id = requested_mode_id;
    request.requested_mode = requested_mode;
    new_mode_request = false;
    return true;
}

bool takeDepthReferenceRequest(DepthReferenceRequestData &request)
{
    if (!new_depth_reference_request)
    {
        return false;
    }

    request.request_id = depth_reference_request_id;
    request.command = depth_reference_command;
    new_depth_reference_request = false;
    return true;
}

bool takeManualCommand(ManualCommandData &command)
{
    if (!new_manual_command)
    {
        return false;
    }

    command = received_manual_command;
    new_manual_command = false;
    return true;
}

bool takeMissionCommand(MissionCommandData &command)
{
    if (!new_mission_command)
    {
        return false;
    }

    command = received_mission_command;
    new_mission_command = false;
    return true;
}

bool takeEmergencyControl(EmergencyControlData &control)
{
    if (!new_emergency_control)
    {
        return false;
    }

    control = received_emergency_control;
    new_emergency_control = false;
    return true;
}

bool takeSysIdControl(SysIdControlData &control)
{
    if (!new_sysid_control)
    {
        return false;
    }

    control = received_sysid_control;
    new_sysid_control = false;
    return true;
}

bool takeSimStateInput(TyrantSimpleEstimator::State &state)
{
#ifdef TYRANT_USE_SIM_STATE_INPUT
    if (!new_sim_state_input)
    {
        return false;
    }

    state = received_sim_state;
    new_sim_state_input = false;
    return true;
#else
    (void)state;
    return false;
#endif
}

bool takeHostHeartbeat()
{
    if (!new_host_heartbeat)
    {
        return false;
    }

    new_host_heartbeat = false;
    return true;
}

ErrorStats getErrorStats()
{
    return {
        publish_failures,
        executor_failures,
        entity_create_failures,
        entity_destroy_failures
    };
}

#ifdef TYRANT_ENABLE_DIAGNOSTICS
void publishResponse(uint32_t value)
{
    if (!entities_ready)
    {
        return;
    }

    response_msg.data = value;
    recordPublishResult(rcl_publish(&response_pub, &response_msg, nullptr));
}

bool hasNewCommand()
{
    if (!new_command)
    {
        return false;
    }

    new_command = false;
    return true;
}

uint32_t getLastCommand()
{
    return last_command;
}
#endif

} // namespace TyrantROS

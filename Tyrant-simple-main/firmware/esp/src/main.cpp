#include <Arduino.h>
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <rmw_microros/rmw_microros.h>
#include <std_msgs/msg/u_int32.h>
#include "payload_config.h"
#include "payload_clock.h"
#include "water_quality_lib.h"
#include "connection_health.h"
#include "payload_monitor.h"
#include "ea_dsra.h"
#include "transport_health.h"
#include "payload_simulation.h"

TwoWire payload_wire(0), power_wire(1);
PayloadI2c payload_bus(payload_wire), power_bus(power_wire);
#ifdef PAYLOAD_SIMULATION
PayloadSimulationModel simulation;
SimulatedWaterQualityManager sensors(simulation);
SimulatedPayloadMonitor payload_mon(simulation);
#else
WaterQualityManager sensors;
PayloadMonitor payload_mon;
#endif
ConnectionHealthManager comm_health;
PowerController power_ctrl;
EaDsraController ea_dsra;
TransportHealth transport_health;

rcl_node_t node;
rclc_support_t support;
rcl_allocator_t allocator;
rclc_executor_t executor;
rcl_init_options_t init_options;
rcl_publisher_t publishers[7];
rcl_subscription_t host_hb_sub, pwr_req_sub;
rcl_timer_t timer_1hz, timer_10hz;
enum Publisher { WATER, HEARTBEAT, DIAGNOSTICS, POWER_STATUS, SENSOR_POWER, THRUSTER_POWER, HEALTH };
bool support_ready=false, node_ready=false, executor_ready=false, options_ready=false;
bool timer_ready[2]={}, sub_ready[2]={};
unsigned pub_count=0;
bool micro_ros_connected=false, transport_fault=false;
uint32_t tick_10hz_counter=0, sample_sequence=0, hb_counter=0, last_agent_check=0;

tyrant_payload_interfaces__msg__PayloadWaterQuality wq_msg;
tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics diag_msg;
tyrant_payload_interfaces__msg__SensorPowerRequest pwr_req_msg;
tyrant_payload_interfaces__msg__SensorPowerStatus pwr_status_msg;
tyrant_payload_interfaces__msg__PayloadPower pwr_sensor_msg, pwr_thruster_msg;
tyrant_payload_interfaces__msg__PayloadHealth health_msg;
std_msgs__msg__UInt32 hb_msg, host_hb_msg;

void publish(Publisher id, const void *message) {
    if (transport_fault) return;
    const bool success=rcl_publish(&publishers[id], message, nullptr)==RCL_RET_OK;
    transport_health.publishResult(success, millis());
    if (!success) ++comm_health.publish_failures;
}
void host_heartbeat_callback(const void *) { comm_health.onHostHeartbeatRx(); }
void power_request_callback(const void *message) {
    const auto *req=static_cast<const tyrant_payload_interfaces__msg__SensorPowerRequest*>(message);
    power_ctrl.handleRequest(req, &pwr_status_msg, !transport_fault && comm_health.isHostHealthy());
    // Apply OFF invalidation immediately, even if OFF/ON requests arrive in one spin.
    sensors.readAll();
    publish(POWER_STATUS, &pwr_status_msg);
}
void timer_1hz_callback(rcl_timer_t *timer, int64_t) {
    if (!timer) return;
    hb_msg.data=hb_counter++;
    publish(HEARTBEAT, &hb_msg);
    comm_health.populateDiagnostics(diag_msg);
    publish(DIAGNOSTICS, &diag_msg);
}
void timer_10hz_callback(rcl_timer_t *timer, int64_t) {
    if (!timer) return;
    ++tick_10hz_counter;
    payload_mon.populateThrusterPower(pwr_thruster_msg);
    publish(THRUSTER_POWER, &pwr_thruster_msg);
    if (tick_10hz_counter%2==0) {
        payload_mon.populateSensorPower(pwr_sensor_msg); publish(SENSOR_POWER, &pwr_sensor_msg);
    }
    if (tick_10hz_counter%5==0) {
        payload_mon.populateHealth(health_msg, sensors.readAll(), power_ctrl, sensors.errors());
        publish(HEALTH, &health_msg);
    }
}
void noteDestroy(rcl_ret_t rc) { if (rc!=RCL_RET_OK) ++comm_health.entity_destroy_failures; }
void destroy_entities() {
    if (support_ready) {
        auto *context=rcl_context_get_rmw_context(&support.context);
        if (context) (void)rmw_uros_set_context_entity_destroy_session_timeout(context, 0);
    }
    // Only finalize resources that were successfully initialized, in reverse ownership order.
    if (executor_ready) noteDestroy(rclc_executor_fini(&executor));
    if (timer_ready[1]) noteDestroy(rcl_timer_fini(&timer_10hz));
    if (timer_ready[0]) noteDestroy(rcl_timer_fini(&timer_1hz));
    if (sub_ready[1]) noteDestroy(rcl_subscription_fini(&pwr_req_sub, &node));
    if (sub_ready[0]) noteDestroy(rcl_subscription_fini(&host_hb_sub, &node));
    while (pub_count) noteDestroy(rcl_publisher_fini(&publishers[--pub_count], &node));
    if (node_ready) noteDestroy(rcl_node_fini(&node));
    if (support_ready) noteDestroy(rclc_support_fini(&support));
    if (options_ready) noteDestroy(rcl_init_options_fini(&init_options));
    support_ready=node_ready=executor_ready=options_ready=false;
    timer_ready[0]=timer_ready[1]=sub_ready[0]=sub_ready[1]=false;
}
#define CHECK(call) do { if ((call)!=RCL_RET_OK) { ++comm_health.entity_create_failures; return false; } } while (0)
bool create_entities() {
    allocator=rcl_get_default_allocator();
    support={}; node=rcl_get_zero_initialized_node();
    executor=rclc_executor_get_zero_initialized_executor();
    host_hb_sub=rcl_get_zero_initialized_subscription(); pwr_req_sub=rcl_get_zero_initialized_subscription();
    timer_1hz=rcl_get_zero_initialized_timer(); timer_10hz=rcl_get_zero_initialized_timer();
    for (auto &p : publishers) p=rcl_get_zero_initialized_publisher();
    init_options=rcl_get_zero_initialized_init_options();
    CHECK(rcl_init_options_init(&init_options, allocator)); options_ready=true;
    CHECK(rcl_init_options_set_domain_id(&init_options, PayloadConfig::ROS_DOMAIN_ID));
    const rcl_ret_t support_rc=rclc_support_init_with_options(&support, 0, nullptr, &init_options, &allocator);
    if (support_rc!=RCL_RET_OK) {
        ++comm_health.entity_create_failures;
        // rclc can initialize the context successfully before clock initialization fails.
        if (rcl_context_is_valid(&support.context)) {
            if (rcl_clock_valid(&support.clock)) noteDestroy(rcl_clock_fini(&support.clock));
            noteDestroy(rcl_shutdown(&support.context));
            noteDestroy(rcl_context_fini(&support.context));
        }
        return false;
    }
    support_ready=true;
    CHECK(rclc_node_init_default(&node, PayloadConfig::ROS_NODE_NAME, PayloadConfig::ROS_NAMESPACE, &support)); node_ready=true;
#define PUB(type, topic) do { \
    CHECK(rclc_publisher_init_default(&publishers[pub_count], &node, type, topic)); \
    ++pub_count; \
    if (rmw_uros_set_publisher_session_timeout(rcl_publisher_get_rmw_handle(&publishers[pub_count-1]), PayloadConfig::RELIABLE_PUBLISH_TIMEOUT_MS)!=RMW_RET_OK) { \
        ++comm_health.entity_create_failures; return false; } \
} while (0)
#define PAYLOAD_TYPE(name) ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, name)
    PUB(PAYLOAD_TYPE(PayloadWaterQuality), "water_quality");
    PUB(ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32), "heartbeat");
    PUB(PAYLOAD_TYPE(PayloadCommunicationDiagnostics), "communication/diagnostics");
    PUB(PAYLOAD_TYPE(SensorPowerStatus), "sensor_power/status");
    PUB(PAYLOAD_TYPE(PayloadPower), "power/sensors");
    PUB(PAYLOAD_TYPE(PayloadPower), "power/thruster");
    PUB(PAYLOAD_TYPE(PayloadHealth), "health");
    CHECK(rclc_subscription_init_default(&host_hb_sub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32), PayloadConfig::HOST_HEARTBEAT_TOPIC)); sub_ready[0]=true;
    CHECK(rclc_subscription_init_default(&pwr_req_sub, &node, PAYLOAD_TYPE(SensorPowerRequest), "sensor_power/request")); sub_ready[1]=true;
    CHECK(rclc_timer_init_default(&timer_1hz, &support, RCL_MS_TO_NS(1000), timer_1hz_callback)); timer_ready[0]=true;
    CHECK(rclc_timer_init_default(&timer_10hz, &support, RCL_MS_TO_NS(100), timer_10hz_callback)); timer_ready[1]=true;
    CHECK(rclc_executor_init(&executor, &support.context, 4, &allocator)); executor_ready=true;
    // Commands/heartbeat are serviced before periodic telemetry.
    CHECK(rclc_executor_add_subscription(&executor, &host_hb_sub, &host_hb_msg, host_heartbeat_callback, ON_NEW_DATA));
    CHECK(rclc_executor_add_subscription(&executor, &pwr_req_sub, &pwr_req_msg, power_request_callback, ON_NEW_DATA));
    CHECK(rclc_executor_add_timer(&executor, &timer_1hz));
    CHECK(rclc_executor_add_timer(&executor, &timer_10hz));
    return true;
}
#undef CHECK
#undef PUB
#undef PAYLOAD_TYPE
void setup() {
    power_ctrl.begin();
#ifndef PAYLOAD_SIMULATION
    payload_bus.begin(PayloadConfig::I2C_PAYLOAD_SDA, PayloadConfig::I2C_PAYLOAD_SCL);
    power_bus.begin(PayloadConfig::I2C_POWER_SDA, PayloadConfig::I2C_POWER_SCL);
#endif
    sensors.begin(payload_bus, power_ctrl);
    payload_mon.begin(payload_bus, power_bus);
    ea_dsra.begin(PayloadConfig::BATTERY_FULL_V, PayloadConfig::BATTERY_EMPTY_V, 30, 5, 2,
        PayloadConfig::MIN_SAMPLE_INTERVAL_MS, PayloadConfig::MAX_SAMPLE_INTERVAL_MS);
    Serial.begin(115200);
    set_microros_serial_transports(Serial);
    // Do not print debug text to the micro-ROS serial stream.
}
void loop() {
    payload_mon.update(); sensors.update(); comm_health.isHostHealthy();
    const uint32_t now=millis();
    if (now-last_agent_check>=PayloadConfig::AGENT_PING_INTERVAL_MS) {
        last_agent_check=now;
        const bool agent_ok=rmw_uros_ping_agent(PayloadConfig::AGENT_PING_TIMEOUT_MS, 1)==RMW_RET_OK;
        if (!agent_ok) {
            ++comm_health.ping_failures;
            if (micro_ros_connected && transport_health.probeFailed()) transport_fault=true;
        } else {
            transport_health.probeSucceeded();
            if (!micro_ros_connected) {
                transport_fault=false;
                if (create_entities()) {
                    micro_ros_connected=true; comm_health.onConnected(); transport_health.reset();
                } else { destroy_entities(); }
            }
        }
    }
    if (micro_ros_connected && !transport_fault) {
        const rcl_ret_t rc=rclc_executor_spin_some(&executor, RCL_MS_TO_NS(2));
        if (rc!=RCL_RET_OK && rc!=RCL_RET_TIMEOUT) { ++comm_health.executor_failures; transport_fault=true; }
    }
    if (sensors.takeSnapshotReady()) {
        const auto decision=ea_dsra.evaluate(sensors.readAll(), payload_mon.batteryVoltage());
        sensors.setSamplingInterval(decision.t_ea_final_ms);
        sensors.populateRosMessage(wq_msg); wq_msg.sequence=sample_sequence++;
        if (micro_ros_connected && !transport_fault) publish(WATER, &wq_msg);
    }
    if (micro_ros_connected && transport_health.publishingStalled(millis())) transport_fault=true;
    if (transport_fault && micro_ros_connected) {
        comm_health.onDisconnected(); micro_ros_connected=false; destroy_entities();
        last_agent_check=millis();
    }
    delay(1);
}

#include <Arduino.h>
#include <micro_ros_platformio.h>

#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/u_int32.h>

#include <tyrant_payload_interfaces/msg/payload_water_quality.h>
#include <tyrant_payload_interfaces/msg/payload_communication_diagnostics.h>
#include <tyrant_payload_interfaces/msg/sensor_power_request.h>
#include <tyrant_payload_interfaces/msg/sensor_power_status.h>
#include <tyrant_payload_interfaces/msg/payload_power.h>
#include <tyrant_payload_interfaces/msg/payload_health.h>

#include "water_quality_lib.h"
#include "connection_health.h"
#include "power_controller.h"
#include "payload_monitor.h"

#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){ return false; }}
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){}}

// Modul
WaterQualityManager sensors;
ConnectionHealthManager comm_health;
PowerController power_ctrl;
PayloadMonitor payload_mon;

// ROS Entities
rcl_node_t node;
rclc_support_t support;
rcl_allocator_t allocator;
rclc_executor_t executor;

// Publishers & Subscribers
rcl_publisher_t wq_pub, hb_pub, diag_pub, pwr_status_pub;
rcl_publisher_t pwr_sensor_pub, pwr_thruster_pub, health_pub;
rcl_subscription_t host_hb_sub, pwr_req_sub;

// Timers (Hanya 2 Timer Utama)
rcl_timer_t timer_1hz, timer_10hz;

// Messages
tyrant_payload_interfaces__msg__PayloadWaterQuality wq_msg;
tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics diag_msg;
tyrant_payload_interfaces__msg__SensorPowerRequest pwr_req_msg;
tyrant_payload_interfaces__msg__SensorPowerStatus pwr_status_msg;
tyrant_payload_interfaces__msg__PayloadPower pwr_sensor_msg;
tyrant_payload_interfaces__msg__PayloadPower pwr_thruster_msg;
tyrant_payload_interfaces__msg__PayloadHealth health_msg;
std_msgs__msg__UInt32 hb_msg;
std_msgs__msg__UInt32 host_hb_msg;

uint32_t wq_sequence = 0;
uint32_t hb_counter = 0;
uint32_t tick_10hz_counter = 0;
bool micro_ros_connected = false;

// Subscription Callbacks
void host_heartbeat_callback(const void * msgin) {
    (void)msgin;
    comm_health.onHostHeartbeatRx();
}

void power_request_callback(const void * msgin) {
    const tyrant_payload_interfaces__msg__SensorPowerRequest * req = 
        (const tyrant_payload_interfaces__msg__SensorPowerRequest *)msgin;
    power_ctrl.handleRequest(req, &pwr_status_msg, comm_health.isHostHealthy());
    RCSOFTCHECK(rcl_publish(&pwr_status_pub, &pwr_status_msg, NULL));
}

// Timer 1 Hz: Telemetri Kualitas Air, Detak Jantung, dan Diagnostik
void timer_1hz_callback(rcl_timer_t * timer, int64_t last_call_time) {
    RCLC_UNUSED(last_call_time);
    if (timer == NULL) return;

    // 1. Water Quality
    WaterQualitySnapshot data = sensors.readAll();
    wq_msg.sequence = wq_sequence++;
    wq_msg.timestamp_us = (uint64_t)micros();
    wq_msg.temperature_c = data.temperature.value;
    wq_msg.temperature_valid = data.temperature.valid;
    wq_msg.temperature_state = (uint8_t)data.temperature.state;
    wq_msg.conductivity_us_cm = data.conductivity.value;
    wq_msg.conductivity_valid = data.conductivity.valid;
    wq_msg.conductivity_state = (uint8_t)data.conductivity.state;
    wq_msg.ph = data.ph.value;
    wq_msg.ph_valid = data.ph.valid;
    wq_msg.ph_state = (uint8_t)data.ph.state;
    wq_msg.dissolved_oxygen_mg_l = data.dissolved_oxygen.value;
    wq_msg.dissolved_oxygen_valid = data.dissolved_oxygen.valid;
    wq_msg.dissolved_oxygen_state = (uint8_t)data.dissolved_oxygen.state;
    RCSOFTCHECK(rcl_publish(&wq_pub, &wq_msg, NULL));

    // 2. Heartbeat
    hb_msg.data = hb_counter++;
    RCSOFTCHECK(rcl_publish(&hb_pub, &hb_msg, NULL));

    // 3. Diagnostics
    comm_health.populateDiagnostics(diag_msg);
    RCSOFTCHECK(rcl_publish(&diag_pub, &diag_msg, NULL));
}

// Timer 10 Hz (Master Tick): Menjadwalkan Daya Sensor (5 Hz), Thruster (10 Hz), Health (2 Hz)
void timer_10hz_callback(rcl_timer_t * timer, int64_t last_call_time) {
    RCLC_UNUSED(last_call_time);
    if (timer == NULL) return;

    tick_10hz_counter++;

    // 10 Hz: Thruster Power Bus (Setiap tick)
    payload_mon.populateThrusterPower(pwr_thruster_msg);
    RCSOFTCHECK(rcl_publish(&pwr_thruster_pub, &pwr_thruster_msg, NULL));

    // 5 Hz: Sensor Rail Power (Setiap 2 tick = 200 ms)
    if (tick_10hz_counter % 2 == 0) {
        payload_mon.populateSensorPower(pwr_sensor_msg);
        RCSOFTCHECK(rcl_publish(&pwr_sensor_pub, &pwr_sensor_msg, NULL));
    }

    // 2 Hz: Subsystem Health (Setiap 5 tick = 500 ms)
    if (tick_10hz_counter % 5 == 0) {
        payload_mon.populateHealth(health_msg, sensors.readAll(), power_ctrl);
        RCSOFTCHECK(rcl_publish(&health_pub, &health_msg, NULL));
    }
}

bool create_entities() {
    allocator = rcl_get_default_allocator();
    RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));
    RCCHECK(rclc_node_init_default(&node, "tyrant_payload_esp32", "/tyrant/payload", &support));

    // 7 Publishers
    RCCHECK(rclc_publisher_init_default(&wq_pub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, PayloadWaterQuality), "water_quality"));
    RCCHECK(rclc_publisher_init_default(&hb_pub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32), "heartbeat"));
    RCCHECK(rclc_publisher_init_default(&diag_pub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, PayloadCommunicationDiagnostics), "communication/diagnostics"));
    RCCHECK(rclc_publisher_init_default(&pwr_status_pub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, SensorPowerStatus), "sensor_power/status"));
    RCCHECK(rclc_publisher_init_default(&pwr_sensor_pub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, PayloadPower), "power/sensors"));
    RCCHECK(rclc_publisher_init_default(&pwr_thruster_pub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, PayloadPower), "power/thruster"));
    RCCHECK(rclc_publisher_init_default(&health_pub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, PayloadHealth), "health"));

    // 2 Subscribers
    RCCHECK(rclc_subscription_init_default(&host_hb_sub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, UInt32), "host_heartbeat"));
    RCCHECK(rclc_subscription_init_default(&pwr_req_sub, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(tyrant_payload_interfaces, msg, SensorPowerRequest), "sensor_power/request"));

    // 2 Timers (1 Hz dan 10 Hz)
    RCCHECK(rclc_timer_init_default(&timer_1hz, &support, RCL_MS_TO_NS(1000), timer_1hz_callback));
    RCCHECK(rclc_timer_init_default(&timer_10hz, &support, RCL_MS_TO_NS(100), timer_10hz_callback));

    // Executor: Tepat 4 Handles (2 Timers + 2 Subscribers)
    RCCHECK(rclc_executor_init(&executor, &support.context, 4, &allocator));
    RCCHECK(rclc_executor_add_timer(&executor, &timer_1hz));
    RCCHECK(rclc_executor_add_timer(&executor, &timer_10hz));
    RCCHECK(rclc_executor_add_subscription(&executor, &host_hb_sub, &host_hb_msg, &host_heartbeat_callback, ON_NEW_DATA));
    RCCHECK(rclc_executor_add_subscription(&executor, &pwr_req_sub, &pwr_req_msg, &power_request_callback, ON_NEW_DATA));

    return true;
}

void destroy_entities() {
    rmw_context_t * rmw_context = rcl_context_get_rmw_context(&support.context);
    (void) rmw_uros_set_context_entity_destroy_session_timeout(rmw_context, 0);

    rcl_ret_t rc;
    rc = rcl_publisher_fini(&wq_pub, &node);
    rc = rcl_publisher_fini(&hb_pub, &node);
    rc = rcl_publisher_fini(&diag_pub, &node);
    rc = rcl_publisher_fini(&pwr_status_pub, &node);
    rc = rcl_publisher_fini(&pwr_sensor_pub, &node);
    rc = rcl_publisher_fini(&pwr_thruster_pub, &node);
    rc = rcl_publisher_fini(&health_pub, &node);

    rc = rcl_subscription_fini(&host_hb_sub, &node);
    rc = rcl_subscription_fini(&pwr_req_sub, &node);

    rc = rcl_timer_fini(&timer_1hz);
    rc = rcl_timer_fini(&timer_10hz);

    rc = rclc_executor_fini(&executor);
    rc = rcl_node_fini(&node);
    rc = rclc_support_fini(&support);
    (void)rc;
}

void setup() {
    Serial.begin(115200);
    delay(2500);

    set_microros_serial_transports(Serial);
    delay(500);

    power_ctrl.begin();
    sensors.begin();
    payload_mon.begin();

    tyrant_payload_interfaces__msg__PayloadWaterQuality__init(&wq_msg);
    tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics__init(&diag_msg);
    tyrant_payload_interfaces__msg__SensorPowerRequest__init(&pwr_req_msg);
    tyrant_payload_interfaces__msg__SensorPowerStatus__init(&pwr_status_msg);
    tyrant_payload_interfaces__msg__PayloadPower__init(&pwr_sensor_msg);
    tyrant_payload_interfaces__msg__PayloadPower__init(&pwr_thruster_msg);
    tyrant_payload_interfaces__msg__PayloadHealth__init(&health_msg);
}

void loop() {
    if (!micro_ros_connected) {
        if (rmw_uros_ping_agent(100, 1) == RMW_RET_OK) {
            if (create_entities()) {
                micro_ros_connected = true;
                comm_health.onConnected();
            } else {
                destroy_entities();
            }
        }
        delay(500);
    } else {
        // Eksekusi callback subscriber & timer tanpa polling ping serial yang memblokir
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
        delay(5);
    }
}
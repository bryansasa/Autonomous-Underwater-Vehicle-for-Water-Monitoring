#ifndef PAYLOAD_MONITOR_H
#define PAYLOAD_MONITOR_H

#include <Arduino.h>
#include <tyrant_payload_interfaces/msg/payload_power.h>
#include <tyrant_payload_interfaces/msg/payload_health.h>
#include "sensor_types.h"
#include "power_controller.h"

class PayloadMonitor {
public:
    PayloadMonitor();

    void begin();

    // Telemetri Daya Rel Sensor (5 Hz)
    void populateSensorPower(tyrant_payload_interfaces__msg__PayloadPower &msg);

    // Telemetri Daya Bus Thruster (10 Hz)
    void populateThrusterPower(tyrant_payload_interfaces__msg__PayloadPower &msg);

    // Telemetri Kesehatan Subsistem (2 Hz)
    void populateHealth(
        tyrant_payload_interfaces__msg__PayloadHealth &msg,
        const WaterQualitySnapshot &wq_data,
        const PowerController &pwr_ctrl
    );

private:
    uint32_t sensor_pwr_seq;
    uint32_t thruster_pwr_seq;
    uint32_t boot_time_ms;
};

#endif
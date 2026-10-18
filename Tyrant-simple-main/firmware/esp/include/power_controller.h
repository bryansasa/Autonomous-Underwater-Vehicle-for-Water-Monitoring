#pragma once
#include <Arduino.h>
#include <tyrant_payload_interfaces/msg/sensor_power_request.h>
#include <tyrant_payload_interfaces/msg/sensor_power_status.h>

class PowerController {
public:
    void begin();
    void handleRequest(const tyrant_payload_interfaces__msg__SensorPowerRequest*,
                       tyrant_payload_interfaces__msg__SensorPowerStatus*, bool host_healthy);
    bool isEnabled(uint8_t sensor_id) const;
    uint32_t enabledSinceMs(uint8_t sensor_id) const;
    bool isConductivityOn() const { return isEnabled(1); }
    bool isPhOn() const { return isEnabled(2); }
    bool isTemperatureOn() const { return isEnabled(3); }
    bool isDoOn() const { return isEnabled(4); }
private:
    bool states_[4] = {};
    uint32_t enabled_since_[4] = {};
};

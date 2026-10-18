#pragma once
#include <tyrant_payload_interfaces/msg/payload_power.h>
#include <tyrant_payload_interfaces/msg/payload_health.h>
#include "payload_i2c.h"
#include "sensor_types.h"
#include "power_controller.h"

class Ina226Monitor {
public:
    void begin(PayloadI2c &bus, uint8_t address, float shunt_ohm, uint8_t id);
    void sample();
    void populate(tyrant_payload_interfaces__msg__PayloadPower &msg);
    float voltageForSampling() const;
    SensorState state() const;
private:
    bool initialize();
    void fail();
    PayloadI2c *bus_ = nullptr;
    uint8_t address_ = 0, id_ = 0;
    float shunt_ = 0, voltage_ = NAN, current_ = NAN;
    bool initialized_ = false, attempted_ = false, voltage_valid_ = false, valid_ = false;
    SensorState state_ = STATE_NOT_INITIALIZED;
    uint32_t last_init_ms_ = 0, sequence_ = 0, errors_ = 0;
    uint64_t sampled_us_ = 0;
};
class PayloadMonitor {
public:
    void begin(PayloadI2c &sensor_bus, PayloadI2c &power_bus);
    void update();
    void populateSensorPower(tyrant_payload_interfaces__msg__PayloadPower &m) { sensors_.populate(m); }
    void populateThrusterPower(tyrant_payload_interfaces__msg__PayloadPower &m) { thruster_.populate(m); }
    float batteryVoltage() const { return thruster_.voltageForSampling(); }
    void populateHealth(tyrant_payload_interfaces__msg__PayloadHealth &m,
        const WaterQualitySnapshot &wq, const PowerController &power, uint32_t sensor_errors);
private:
    PayloadI2c *sensor_bus_ = nullptr, *power_bus_ = nullptr;
    Ina226Monitor sensors_, thruster_;
    uint32_t sensor_tick_ = 0, thruster_tick_ = 0;
};

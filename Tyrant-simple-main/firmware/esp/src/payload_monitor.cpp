#include "payload_monitor.h"
#include "payload_config.h"
#include "payload_clock.h"

void Ina226Monitor::begin(PayloadI2c &bus, uint8_t address, float shunt_ohm, uint8_t id) {
    bus_ = &bus; address_ = address; shunt_ = shunt_ohm; id_ = id;
    state_ = STATE_INITIALIZING;
}
void Ina226Monitor::fail() {
    ++errors_; initialized_ = false; voltage_valid_ = false; valid_ = false;
    voltage_ = NAN; current_ = NAN; state_ = STATE_ERROR;
}
bool Ina226Monitor::initialize() {
    attempted_ = true; last_init_ms_ = millis();
    uint16_t manufacturer=0, die=0;
    if (!bus_->readRegister(address_, 0xFE, manufacturer) ||
        !bus_->readRegister(address_, 0xFF, die) || manufacturer != 0x5449 || (die & 0xFFF0) != 0x2260 ||
        !bus_->writeRegister(address_, 0x00, 0x4127)) {
        fail(); return false;
    }
    initialized_ = true; state_ = STATE_INITIALIZING; return true;
}
void Ina226Monitor::sample() {
    if (!bus_) return;
    if (!initialized_) {
        if (!attempted_ || static_cast<uint32_t>(millis()-last_init_ms_) >= 1000) initialize();
        return; // Allow at least one complete ADC conversion after configuration.
    }
    uint16_t config=0, status=0, raw_bus=0, raw_shunt=0;
    if (!bus_->readRegister(address_, 0, config) || config != 0x4127 ||
        !bus_->readRegister(address_, 6, status)) { fail(); return; }
    if (!(status & 0x0008)) { // Conversion-ready flag. Never refresh old sample time.
        if (sampled_us_ && payloadTimeUs()-sampled_us_ > 500000) {
            valid_ = false; voltage_valid_ = false; state_ = STATE_STALE;
        }
        return;
    }
    if (!bus_->readRegister(address_, 2, raw_bus) ||
        !bus_->readRegister(address_, 1, raw_shunt)) { fail(); return; }
    voltage_ = raw_bus * 0.00125f;
    if (voltage_ > 36.0f || raw_shunt == 0x7FFF || raw_shunt == 0x8000) { fail(); return; }
    sampled_us_ = payloadTimeUs(); voltage_valid_ = true;
    // Signed shunt voltage / actual resistor. No guessed calibration register.
    // INA226 LSBs: bus 1.25 mV; shunt 2.5 uV (TI datasheet).
    valid_ = isfinite(shunt_) && shunt_ > 0;
    current_ = valid_ ? static_cast<int16_t>(raw_shunt) * 0.0000025f / shunt_ : NAN;
    state_ = valid_ ? STATE_READY : STATE_INITIALIZING;
}
SensorState Ina226Monitor::state() const {
    return voltage_valid_ && payloadTimeUs()-sampled_us_ > 500000 ? STATE_STALE : state_;
}
void Ina226Monitor::populate(tyrant_payload_interfaces__msg__PayloadPower &m) {
    const bool fresh = voltage_valid_ && payloadTimeUs()-sampled_us_ <= 500000;
    m.sequence = sequence_++; m.timestamp_us = sampled_us_; m.monitor_id = id_;
    m.bus_voltage_v = fresh ? voltage_ : NAN;
    m.current_a = fresh && valid_ ? current_ : NAN;
    m.power_w = fresh && valid_ ? voltage_*current_ : NAN;
    m.valid = fresh && valid_;
    m.sensor_state = state();
    m.error_count = errors_;
}
float Ina226Monitor::voltageForSampling() const {
    return voltage_valid_ && payloadTimeUs()-sampled_us_ <= 500000 ? voltage_ : NAN;
}
void PayloadMonitor::begin(PayloadI2c &sensor_bus, PayloadI2c &power_bus) {
    sensor_bus_ = &sensor_bus; power_bus_ = &power_bus;
    sensors_.begin(sensor_bus, PayloadConfig::SENSOR_INA_ADDRESS, PayloadConfig::SENSOR_SHUNT_OHM, 1);
    thruster_.begin(power_bus, PayloadConfig::THRUSTER_INA_ADDRESS, PayloadConfig::THRUSTER_SHUNT_OHM, 2);
}
void PayloadMonitor::update() {
    const uint32_t now = millis();
    if (now-thruster_tick_ >= 100) { thruster_tick_ = now; thruster_.sample(); }
    if (now-sensor_tick_ >= 200) { sensor_tick_ = now; sensors_.sample(); }
}
void PayloadMonitor::populateHealth(tyrant_payload_interfaces__msg__PayloadHealth &m,
    const WaterQualitySnapshot &wq, const PowerController &p, uint32_t sensor_errors) {
    m.timestamp_us = payloadTimeUs(); m.uptime_ms = millis();
    m.conductivity_state = wq.conductivity.state; m.ph_state = wq.ph.state;
    m.temperature_state = wq.temperature.state; m.dissolved_oxygen_state = wq.dissolved_oxygen.state;
    m.sensor_power_monitor_state = sensors_.state(); m.thruster_power_monitor_state = thruster_.state();
    m.i2c_bus1_healthy = sensor_bus_->healthy(); m.i2c_bus2_healthy = power_bus_->healthy();
    m.mosfet_conductivity_on = p.isConductivityOn(); m.mosfet_ph_on = p.isPhOn();
    m.mosfet_temperature_on = p.isTemperatureOn(); m.mosfet_do_on = p.isDoOn();
    m.i2c_bus1_error_count = sensor_bus_->errors(); m.i2c_bus2_error_count = power_bus_->errors();
    m.sensor_read_error_count = sensor_errors;
    // No hardware feedback for MOSFET transitions; zero is not proof of a working switch.
    m.power_transition_error_count = 0;
}

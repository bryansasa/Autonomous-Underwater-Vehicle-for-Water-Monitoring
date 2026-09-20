#include "payload_monitor.h"

PayloadMonitor::PayloadMonitor()
    : sensor_pwr_seq(0),
      thruster_pwr_seq(0),
      boot_time_ms(0) {}

void PayloadMonitor::begin() {
    boot_time_ms = millis();
}

void PayloadMonitor::populateSensorPower(tyrant_payload_interfaces__msg__PayloadPower &msg) {
    msg.sequence = sensor_pwr_seq++;
    msg.timestamp_us = (uint64_t)micros();
    msg.monitor_id = 1; // PAYLOAD_SENSOR_RAIL

    // Simulasi INA226 Rel Sensor: ~12.0 V, ~0.35 A
    float v = 12.05f + ((float)(rand() % 8) / 100.0f);
    float i = 0.35f + ((float)(rand() % 4) / 100.0f);

    msg.bus_voltage_v = v;
    msg.current_a = i;
    msg.power_w = v * i;
    msg.valid = true;
    msg.sensor_state = 2; // READY
    msg.error_count = 0;
}

void PayloadMonitor::populateThrusterPower(tyrant_payload_interfaces__msg__PayloadPower &msg) {
    msg.sequence = thruster_pwr_seq++;
    msg.timestamp_us = (uint64_t)micros();
    msg.monitor_id = 2; // THRUSTER_BUS

    // Simulasi INA226 Bus Thruster: ~16.2 V, ~2.5 A
    float v = 16.20f + ((float)(rand() % 15) / 100.0f);
    float i = 2.50f + ((float)(rand() % 20) / 100.0f);

    msg.bus_voltage_v = v;
    msg.current_a = i;
    msg.power_w = v * i;
    msg.valid = true;
    msg.sensor_state = 2; // READY
    msg.error_count = 0;
}

void PayloadMonitor::populateHealth(
    tyrant_payload_interfaces__msg__PayloadHealth &msg,
    const WaterQualitySnapshot &wq_data,
    const PowerController &pwr_ctrl
) {
    msg.timestamp_us = (uint64_t)micros();
    msg.uptime_ms = millis() - boot_time_ms;

    // Status 4 Sensor Kualitas Air
    msg.conductivity_state = (uint8_t)wq_data.conductivity.state;
    msg.ph_state = (uint8_t)wq_data.ph.state;
    msg.temperature_state = (uint8_t)wq_data.temperature.state;
    msg.dissolved_oxygen_state = (uint8_t)wq_data.dissolved_oxygen.state;

    // Status Monitor Daya
    msg.sensor_power_monitor_state = 2;   // READY
    msg.thruster_power_monitor_state = 2; // READY

    // Jalur Bus I2C Terisolasi
    msg.i2c_bus1_healthy = true;
    msg.i2c_bus2_healthy = true;

    // Kondisi Saklar MOSFET Aktual
    msg.mosfet_conductivity_on = pwr_ctrl.isConductivityOn();
    msg.mosfet_ph_on = pwr_ctrl.isPhOn();
    msg.mosfet_temperature_on = pwr_ctrl.isTemperatureOn();
    msg.mosfet_do_on = pwr_ctrl.isDoOn();

    // Penghitung Galat
    msg.i2c_bus1_error_count = 0;
    msg.i2c_bus2_error_count = 0;
    msg.sensor_read_error_count = 0;
    msg.power_transition_error_count = 0;
}
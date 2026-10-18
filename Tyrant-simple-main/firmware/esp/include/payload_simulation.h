#pragma once
#ifdef PAYLOAD_SIMULATION
#include "water_quality_lib.h"
#include "payload_monitor.h"
#include "payload_config.h"
#include "payload_clock.h"

// Synthetic data only; this backend never touches GPIO, ADC or I2C.
class PayloadSimulationModel {
public:
    void start() { if (!started_) { epoch_us_=payloadTimeUs(); started_=true; } }
    float seconds() const { return started_ ? ((payloadTimeUs()-epoch_us_)/1000 % 180000)/1000.0f : 0; }
    float batteryVoltage() const;
    float value(uint8_t id) const;
    bool channelFailed(uint8_t id) const { const float t=seconds(); return id==1 && t>=150 && t<165; }
private:
    uint64_t epoch_us_=0;
    bool started_=false;
};
class SimulatedWaterQualityManager {
public:
    explicit SimulatedWaterQualityManager(PayloadSimulationModel &model) : model_(model) {}
    void begin(PayloadI2c&, const PowerController &power) { power_=&power; }
    void update();
    void setSamplingInterval(uint32_t ms);
    bool takeSnapshotReady() { const bool ready=ready_; ready_=false; return ready; }
    WaterQualitySnapshot readAll();
    void populateRosMessage(tyrant_payload_interfaces__msg__PayloadWaterQuality &msg);
    uint32_t errors() const { return errors_; }
private:
    void refresh();
    PayloadSimulationModel &model_;
    const PowerController *power_=nullptr;
    WaterQualitySnapshot data_;
    bool previous_power_[4]={}, ready_=false, first_=true;
    uint32_t last_cycle_ms_=0, interval_ms_=1000, errors_=0;
};
class SimulatedPayloadMonitor {
public:
    explicit SimulatedPayloadMonitor(PayloadSimulationModel &model) : model_(model) {}
    void begin(PayloadI2c&, PayloadI2c&) {}
    void update();
    float batteryVoltage() const;
    void populateSensorPower(tyrant_payload_interfaces__msg__PayloadPower &msg);
    void populateThrusterPower(tyrant_payload_interfaces__msg__PayloadPower &msg);
    void populateHealth(tyrant_payload_interfaces__msg__PayloadHealth &msg,
        const WaterQualitySnapshot &wq, const PowerController &power, uint32_t sensor_errors);
private:
    PayloadSimulationModel &model_;
    float voltage_=NAN;
    uint64_t sampled_us_=0;
    uint32_t sensor_seq_=0, thruster_seq_=0, last_tick_=0, errors_=0;
    bool failed_=false;
};
#endif

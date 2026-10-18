#include "payload_simulation.h"
#ifdef PAYLOAD_SIMULATION
float PayloadSimulationModel::batteryVoltage() const {
    const float t=seconds();
    if ((t>=120 && t<123) || t>=165) return NAN;
    return t>=123 && t<150 ? 20.3f : 25.2f;
}
float PayloadSimulationModel::value(uint8_t id) const {
    const float t=seconds();
    // Transition layer: deterministic wave creates a measurable gradient.
    const float wave=t>=45 && t<90 ? sinf((t-45)*0.4f) : 0;
    switch(id) {
        case 1: return 1200+300*wave;
        case 2: return 7.2f+0.8f*wave;
        case 3: return 26+1.5f*wave;
        case 4: return t>=90 && t<120 ? 1.5f : 7.5f+wave;
        default: return NAN;
    }
}
void SimulatedWaterQualityManager::refresh() {
    SensorData *all[]={&data_.conductivity,&data_.ph,&data_.temperature,&data_.dissolved_oxygen};
    for (uint8_t i=0; i<4; ++i) {
        const bool on=power_->isEnabled(i+1);
        if (!on) *all[i]=SensorData{};
        else if (!previous_power_[i]) { *all[i]=SensorData{}; all[i]->state=STATE_INITIALIZING; }
        else if (all[i]->valid && sampleAgeMs(*all[i],payloadTimeUs())>PayloadConfig::SENSOR_STALE_MS) {
            all[i]->valid=false; all[i]->state=STATE_STALE;
        }
        previous_power_[i]=on;
        if (on) model_.start();
    }
}
void SimulatedWaterQualityManager::setSamplingInterval(uint32_t ms) {
    interval_ms_=ms<1000 ? 1000 : (ms>5000 ? 5000 : ms);
}
void SimulatedWaterQualityManager::update() {
    if (!power_) return;
    refresh(); const uint32_t now=millis();
    if (!first_ && now-last_cycle_ms_<interval_ms_) return;
    first_=false; last_cycle_ms_=now; ready_=true;
    SensorData *all[]={&data_.conductivity,&data_.ph,&data_.temperature,&data_.dissolved_oxygen};
    for (uint8_t i=0; i<4; ++i) {
        auto &s=*all[i];
        if (!power_->isEnabled(i+1) || now-power_->enabledSinceMs(i+1)<PayloadConfig::SENSOR_WARMUP_MS) continue;
        if (model_.channelFailed(i+1)) { s.valid=false; s.state=STATE_ERROR; ++errors_; continue; }
        s.value=model_.value(i+1); s.valid=true; s.state=STATE_READY;
        s.seen=true; s.last_sample_us=payloadTimeUs();
    }
}
WaterQualitySnapshot SimulatedWaterQualityManager::readAll() { refresh(); return data_; }
void SimulatedWaterQualityManager::populateRosMessage(tyrant_payload_interfaces__msg__PayloadWaterQuality &m) {
    const auto s=readAll(); const uint64_t now=payloadTimeUs(); m.timestamp_us=now;
#define SIM_COPY(field, source) \
    m.field=s.source.value; m.source##_valid=s.source.valid; \
    m.source##_state=s.source.state; m.source##_age_ms=sampleAgeMs(s.source,now)
    SIM_COPY(conductivity_us_cm,conductivity); SIM_COPY(ph,ph);
    SIM_COPY(temperature_c,temperature); SIM_COPY(dissolved_oxygen_mg_l,dissolved_oxygen);
#undef SIM_COPY
}
void SimulatedPayloadMonitor::update() {
    const uint32_t now=millis(); if (now-last_tick_<100) return;
    last_tick_=now; voltage_=model_.batteryVoltage(); sampled_us_=payloadTimeUs();
    const bool failed=!isfinite(voltage_);
    if (failed && !failed_) ++errors_;
    failed_=failed;
}
float SimulatedPayloadMonitor::batteryVoltage() const {
    return payloadTimeUs()-sampled_us_<=500000 ? voltage_ : NAN;
}
void SimulatedPayloadMonitor::populateSensorPower(tyrant_payload_interfaces__msg__PayloadPower &m) {
    m.sequence=sensor_seq_++; m.timestamp_us=payloadTimeUs(); m.monitor_id=1;
    m.bus_voltage_v=12; m.current_a=0.35f; m.power_w=4.2f; m.valid=true;
    m.sensor_state=STATE_READY; m.error_count=0;
}
void SimulatedPayloadMonitor::populateThrusterPower(tyrant_payload_interfaces__msg__PayloadPower &m) {
    const float v=batteryVoltage(); const bool valid=isfinite(v);
    m.sequence=thruster_seq_++; m.timestamp_us=sampled_us_; m.monitor_id=2;
    m.bus_voltage_v=v; m.current_a=valid ? 2.5f : NAN; m.power_w=valid ? v*2.5f : NAN;
    m.valid=valid; m.sensor_state=valid ? STATE_READY : STATE_ERROR; m.error_count=errors_;
}
void SimulatedPayloadMonitor::populateHealth(tyrant_payload_interfaces__msg__PayloadHealth &m,
    const WaterQualitySnapshot &wq, const PowerController &p, uint32_t sensor_errors) {
    m.timestamp_us=payloadTimeUs(); m.uptime_ms=millis();
    m.conductivity_state=wq.conductivity.state; m.ph_state=wq.ph.state;
    m.temperature_state=wq.temperature.state; m.dissolved_oxygen_state=wq.dissolved_oxygen.state;
    m.sensor_power_monitor_state=STATE_READY;
    m.thruster_power_monitor_state=isfinite(batteryVoltage()) ? STATE_READY : STATE_ERROR;
    m.i2c_bus1_healthy=!model_.channelFailed(1); m.i2c_bus2_healthy=isfinite(batteryVoltage());
    m.mosfet_conductivity_on=p.isConductivityOn(); m.mosfet_ph_on=p.isPhOn();
    m.mosfet_temperature_on=p.isTemperatureOn(); m.mosfet_do_on=p.isDoOn();
    m.i2c_bus1_error_count=sensor_errors; m.i2c_bus2_error_count=errors_;
    m.sensor_read_error_count=sensor_errors; m.power_transition_error_count=0;
}
#endif

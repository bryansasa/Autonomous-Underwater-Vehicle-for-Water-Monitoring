#include "water_quality_lib.h"
#include "payload_config.h"
#include "payload_clock.h"
#include <stdlib.h>
#include <ctype.h>

void WaterQualityManager::begin(PayloadI2c &bus, const PowerController &power) {
    bus_ = &bus; power_ = &power;
    channels_[0] = {PayloadConfig::EC_ADDRESS, 1, &data_.conductivity, false, 0, 0};
    channels_[1] = {PayloadConfig::PH_ADDRESS, 2, &data_.ph, false, 0, 0};
    channels_[2] = {PayloadConfig::DO_ADDRESS, 4, &data_.dissolved_oxygen, false, 0, 0};
    pinMode(PayloadConfig::TEMPERATURE_ADC, INPUT);
    analogReadResolution(12);
    analogSetPinAttenuation(PayloadConfig::TEMPERATURE_ADC, ADC_11db);
}
void WaterQualityManager::setSamplingInterval(uint32_t ms) {
    interval_ms_ = ms < PayloadConfig::MIN_SAMPLE_INTERVAL_MS ? PayloadConfig::MIN_SAMPLE_INTERVAL_MS :
        (ms > PayloadConfig::MAX_SAMPLE_INTERVAL_MS ? PayloadConfig::MAX_SAMPLE_INTERVAL_MS : ms);
}
void WaterQualityManager::fail(SensorData &s) {
    s.valid = false; s.state = STATE_ERROR; ++errors_;
}
void WaterQualityManager::refreshPowerAndAge() {
    SensorData *all[] = {&data_.conductivity, &data_.ph, &data_.temperature, &data_.dissolved_oxygen};
    for (uint8_t i=0; i<4; ++i) {
        const bool enabled = power_->isEnabled(i+1);
        auto &s = *all[i];
        if (!enabled) { s = SensorData{}; }
        else if (!previous_power_[i]) { s = SensorData{}; s.state = STATE_INITIALIZING; }
        else if (s.valid && sampleAgeMs(s, payloadTimeUs()) > PayloadConfig::SENSOR_STALE_MS) {
            s.valid = false; s.state = STATE_STALE;
        }
        previous_power_[i] = enabled;
    }
    for (auto &ch : channels_) if (!power_->isEnabled(ch.sensor_id)) ch.pending = false;
}
void WaterQualityManager::start(EzoChannel &ch, uint32_t now) {
    if (!power_->isEnabled(ch.sensor_id) ||
        static_cast<uint32_t>(now-power_->enabledSinceMs(ch.sensor_id)) < PayloadConfig::SENSOR_WARMUP_MS) return;
    const uint8_t command = 'R';
    if (!bus_->write(ch.address, &command, 1)) { fail(*ch.data); return; }
    ch.pending = true; ch.started_ms = now; ch.last_poll_ms = now;
}
void WaterQualityManager::poll(EzoChannel &ch, uint32_t now) {
    if (!ch.pending) return;
    const uint32_t elapsed = now-ch.started_ms;
    if (elapsed > PayloadConfig::EZO_TIMEOUT_MS) {
        fail(*ch.data); ch.pending = false; return;
    }
    if (elapsed < PayloadConfig::EZO_CONVERSION_MS || now-ch.last_poll_ms < 100) return;
    ch.last_poll_ms = now;
    uint8_t bytes[32] = {};
    if (!bus_->read(ch.address, bytes, sizeof(bytes))) {
        fail(*ch.data); ch.pending = false; return;
    }
    if (bytes[0] == 254 && elapsed < PayloadConfig::EZO_TIMEOUT_MS) return;
    ch.pending = false;
    if (bytes[0] != 1) { fail(*ch.data); return; }
    // First ASCII numeric field; EZO-EC and DO may have comma-separated outputs.
    char text[32] = {};
    unsigned n=0;
    while (n<31 && bytes[n+1] != 0 && bytes[n+1] != ',') { text[n] = bytes[n+1]; ++n; }
    if (n==31) { fail(*ch.data); return; } // Truncated/non-terminated response.
    char *end = nullptr;
    const float value = strtof(text, &end);
    const bool parsed = end != text;
    while (end && isspace(static_cast<unsigned char>(*end))) ++end;
    const bool range_ok = ch.sensor_id == 2 ? value >= 0 && value <= 14 : value >= 0;
    if (!parsed || !end || *end || !isfinite(value) || !range_ok) { fail(*ch.data); return; }
    ch.data->value = value; ch.data->valid = true; ch.data->state = STATE_READY;
    ch.data->last_sample_us = payloadTimeUs(); ch.data->seen = true;
}
void WaterQualityManager::temperature() {
    auto &s = data_.temperature;
    if (!power_->isTemperatureOn() ||
        static_cast<uint32_t>(millis()-power_->enabledSinceMs(3)) < PayloadConfig::SENSOR_WARMUP_MS) return;
    if (!PayloadConfig::TEMPERATURE_CALIBRATION_CONFIRMED) {
        s.valid = false; s.state = STATE_NOT_INITIALIZED; return;
    }
    uint32_t sum=0;
    for (unsigned i=0; i<10; ++i) sum += analogReadMilliVolts(PayloadConfig::TEMPERATURE_ADC);
    const float volts = sum / 10000.0f;
    if (volts < PayloadConfig::TEMPERATURE_MIN_V || volts > PayloadConfig::TEMPERATURE_MAX_V ||
        PayloadConfig::TEMPERATURE_V_PER_C <= 0) { fail(s); return; }
    const float value = (volts-PayloadConfig::TEMPERATURE_OFFSET_V)/PayloadConfig::TEMPERATURE_V_PER_C;
    if (!isfinite(value)) { fail(s); return; }
    s.value = value; s.valid = true; s.state = STATE_READY;
    s.last_sample_us = payloadTimeUs(); s.seen = true;
}
void WaterQualityManager::update() {
    if (!power_ || !bus_) return;
    refreshPowerAndAge();
    const uint32_t now = millis();
    if (!cycle_active_ && (first_cycle_ || now-last_cycle_ms_ >= interval_ms_)) {
        first_cycle_ = false; last_cycle_ms_ = now; cycle_active_ = true;
        for (auto &ch : channels_) start(ch, now);
        temperature();
    }
    if (cycle_active_) {
        bool pending = false;
        for (auto &ch : channels_) { poll(ch, now); pending |= ch.pending; }
        if (!pending) { cycle_active_ = false; snapshot_ready_ = true; }
    }
}
bool WaterQualityManager::takeSnapshotReady() {
    const bool ready = snapshot_ready_; snapshot_ready_ = false; return ready;
}
WaterQualitySnapshot WaterQualityManager::readAll() { refreshPowerAndAge(); return data_; }
void WaterQualityManager::populateRosMessage(tyrant_payload_interfaces__msg__PayloadWaterQuality &m) {
    const auto snapshot = readAll();
    const uint64_t now = payloadTimeUs();
    m.timestamp_us = now;
#define COPY_SENSOR(field, source) \
    m.field = snapshot.source.value; \
    m.source##_valid = snapshot.source.valid; \
    m.source##_state = snapshot.source.state; \
    m.source##_age_ms = sampleAgeMs(snapshot.source, now)
    COPY_SENSOR(conductivity_us_cm, conductivity);
    COPY_SENSOR(ph, ph);
    COPY_SENSOR(temperature_c, temperature);
    COPY_SENSOR(dissolved_oxygen_mg_l, dissolved_oxygen);
#undef COPY_SENSOR
}

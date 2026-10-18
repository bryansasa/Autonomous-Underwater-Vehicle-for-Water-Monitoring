#pragma once
#include <Arduino.h>
#include <math.h>
#include <stdint.h>

enum SensorState : uint8_t {
    STATE_NOT_INITIALIZED = 0, STATE_INITIALIZING = 1, STATE_READY = 2,
    STATE_STALE = 3, STATE_ERROR = 4
};
struct SensorData {
    float value = NAN;
    bool valid = false;
    SensorState state = STATE_NOT_INITIALIZED;
    uint64_t last_sample_us = 0;
    bool seen = false;
};
struct WaterQualitySnapshot {
    SensorData temperature, conductivity, ph, dissolved_oxygen;
};
inline uint32_t sampleAgeMs(const SensorData &s, uint64_t now_us) {
    if (!s.seen) return UINT32_MAX;
    const uint64_t age = (now_us - s.last_sample_us) / 1000;
    return age >= UINT32_MAX ? UINT32_MAX - 1 : static_cast<uint32_t>(age);
}
